//! Session recovery — ingest corrupted Claude Code .jsonl sessions.
//!
//! Parses Claude Code session files, extracts all context (decisions,
//! files, corrections, interactions), and writes to .crux/ for
//! restore_context to pick up.

use chrono::Utc;
use regex::Regex;
use serde_json::Value;
use std::collections::HashSet;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

use crate::hooks::CORRECTION_PATTERNS;
use crate::session::{self, SessionState};

/// Recovered data from a Claude Code session.
#[derive(Debug, Default)]
pub struct RecoveredSession {
    pub session_id: String,
    pub project_dir: String,
    pub working_on: String,
    pub key_decisions: Vec<String>,
    pub files_touched: Vec<String>,
    pub corrections: Vec<String>,
    pub pending: Vec<String>,
    pub messages: Vec<ConversationEntry>,
    pub interactions: Vec<InteractionEntry>,
    pub total_lines: usize,
    pub parsed_lines: usize,
}

#[derive(Debug)]
pub struct ConversationEntry {
    pub role: String,
    pub content: String,
    pub timestamp: String,
}

#[derive(Debug)]
pub struct InteractionEntry {
    pub tool_name: String,
    pub input_summary: String,
    pub output_summary: String,
    pub timestamp: String,
}

static COMMIT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[[\w/.-]+\s+\w+\]\s+(.+)").unwrap()
});

static DECISION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(decided to|chose|using .+ because|switched to|going with)").unwrap()
});

/// Parse a Claude Code session .jsonl file and extract all useful data.
pub fn parse_session(path: &Path) -> RecoveredSession {
    let mut recovered = RecoveredSession::default();

    let file = match fs::File::open(path) {
        Ok(f) => f,
        Err(_) => return recovered,
    };

    let reader = BufReader::new(file);
    let mut last_working_on = String::new();
    let mut files_set: HashSet<String> = HashSet::new();

    for line in reader.lines() {
        recovered.total_lines += 1;
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let msg: Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(_) => continue,
        };
        recovered.parsed_lines += 1;

        let msg_type = msg["type"].as_str().unwrap_or("");
        let role = msg["message"]["role"].as_str().unwrap_or("");
        let timestamp = msg["timestamp"].as_str().unwrap_or("").to_string();

        // Extract session metadata
        if recovered.session_id.is_empty() {
            if let Some(sid) = msg["sessionId"].as_str() {
                recovered.session_id = sid.to_string();
            }
        }
        if recovered.project_dir.is_empty() {
            if let Some(cwd) = msg["cwd"].as_str() {
                recovered.project_dir = cwd.to_string();
            }
        }

        match msg_type {
            "user" if role == "user" => {
                let raw_content = &msg["message"]["content"];

                // Handle tool_result blocks (also type=user, role=user)
                if let Some(blocks) = raw_content.as_array() {
                    for block in blocks {
                        if block["type"].as_str() == Some("tool_result") {
                            let output = extract_text_content(&block["content"]);
                            // Extract git commit messages
                            if let Some(cap) = COMMIT_RE.captures(&output) {
                                let commit_msg = cap[1].trim();
                                if !commit_msg.is_empty() && !commit_msg.starts_with("$(") {
                                    recovered.key_decisions.push(truncate(commit_msg, 200));
                                }
                            }
                            // Update last interaction with output
                            if let Some(last) = recovered.interactions.last_mut() {
                                if last.output_summary.is_empty() {
                                    last.output_summary = truncate(&output, 200);
                                }
                            }
                        }
                    }
                }

                // Handle plain text user messages
                let content = extract_text_content(raw_content);
                if !content.is_empty() {
                    // Check for corrections
                    if crate::hooks::is_correction(&content) {
                        recovered.corrections.push(truncate(&content, 200));
                    }

                    // Log conversation
                    if content.len() > 20 && content.len() < 500 {
                        recovered.messages.push(ConversationEntry {
                            role: "user".into(),
                            content: truncate(&content, 500),
                            timestamp: timestamp.clone(),
                        });
                    }
                }
            }

            "assistant" if role == "assistant" => {
                let content = extract_text_content(&msg["message"]["content"]);
                if !content.is_empty() {
                    // Extract decisions
                    if DECISION_RE.is_match(&content) {
                        let first_line = content.lines().next().unwrap_or("");
                        if first_line.len() > 10 && first_line.len() < 300 {
                            recovered.key_decisions.push(first_line.to_string());
                        }
                    }

                    // Track what assistant was working on
                    if content.len() > 50 {
                        last_working_on = truncate(&content.lines().next().unwrap_or(""), 200);
                    }

                    // Log conversation
                    recovered.messages.push(ConversationEntry {
                        role: "assistant".into(),
                        content: truncate(&content, 500),
                        timestamp: timestamp.clone(),
                    });
                }

                // Extract tool_use from assistant content blocks
                if let Some(blocks) = msg["message"]["content"].as_array() {
                    for block in blocks {
                        if block["type"].as_str() == Some("tool_use") {
                            let tool_name = block["name"].as_str().unwrap_or("").to_string();
                            let input = &block["input"];

                            // Track files from Edit/Write
                            if (tool_name == "Edit" || tool_name == "Write") {
                                if let Some(fp) = input["file_path"].as_str() {
                                    files_set.insert(fp.to_string());
                                }
                            }

                            // Extract git commit decisions from Bash
                            if tool_name == "Bash" {
                                if let Some(cmd) = input["command"].as_str() {
                                    if cmd.contains("git commit") {
                                        // Will match output in tool_result
                                    }
                                }
                            }

                            let input_str = if let Some(fp) = input["file_path"].as_str() {
                                fp.to_string()
                            } else if let Some(cmd) = input["command"].as_str() {
                                truncate(cmd, 100)
                            } else {
                                truncate(&input.to_string(), 100)
                            };

                            recovered.interactions.push(InteractionEntry {
                                tool_name,
                                input_summary: input_str,
                                output_summary: String::new(), // filled from tool_result
                                timestamp: timestamp.clone(),
                            });
                        }
                    }
                }
            }

            _ => {}
        }
    }

    recovered.working_on = last_working_on;
    recovered.files_touched = files_set.into_iter().collect();
    recovered.files_touched.sort();

    // Deduplicate decisions
    let mut seen = HashSet::new();
    recovered.key_decisions.retain(|d| seen.insert(d.clone()));

    recovered
}

/// Write recovered session data to .crux/ directory.
pub fn write_recovery(recovered: &RecoveredSession, crux_dir: &Path) -> anyhow::Result<String> {
    fs::create_dir_all(crux_dir.join("sessions"))?;
    fs::create_dir_all(crux_dir.join("corrections"))?;
    fs::create_dir_all(crux_dir.join("analytics/conversations"))?;
    fs::create_dir_all(crux_dir.join("analytics/interactions"))?;

    // Write session state
    let state = SessionState {
        active_mode: "build-py".into(),
        active_tool: "claude-code".into(),
        working_on: recovered.working_on.clone(),
        key_decisions: recovered.key_decisions.clone(),
        files_touched: recovered.files_touched.clone(),
        pending: recovered.pending.clone(),
        ..SessionState::new()
    };
    session::save_session(&state, crux_dir)?;

    // Write handoff
    let handoff = format!(
        "# Session Recovery\n\n\
        Recovered from Claude Code session: {}\n\n\
        **Working on:** {}\n\n\
        ## Key Decisions ({})\n{}\n\n\
        ## Files Touched ({})\n{}\n\n\
        ## Corrections Detected ({})\n{}\n",
        recovered.session_id,
        recovered.working_on,
        recovered.key_decisions.len(),
        recovered.key_decisions.iter().map(|d| format!("- {d}")).collect::<Vec<_>>().join("\n"),
        recovered.files_touched.len(),
        recovered.files_touched.iter().take(30).map(|f| format!("- {f}")).collect::<Vec<_>>().join("\n"),
        recovered.corrections.len(),
        recovered.corrections.iter().take(10).map(|c| format!("- {c}")).collect::<Vec<_>>().join("\n"),
    );
    session::write_handoff(crux_dir, &handoff)?;

    // Write corrections
    if !recovered.corrections.is_empty() {
        let path = crux_dir.join("corrections/corrections.jsonl");
        let mut f = OpenOptions::new().create(true).append(true).open(&path)?;
        for correction in &recovered.corrections {
            let entry = serde_json::json!({
                "content": correction,
                "source": "session-recovery",
                "timestamp": Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
            });
            writeln!(f, "{}", serde_json::to_string(&entry)?)?;
        }
    }

    // Write full conversation log
    if !recovered.messages.is_empty() {
        let date = recovered.messages.first()
            .map(|m| m.timestamp.get(..10).unwrap_or("unknown"))
            .unwrap_or("unknown");
        let path = crux_dir.join(format!("analytics/conversations/{date}.jsonl"));
        let mut f = OpenOptions::new().create(true).append(true).open(&path)?;
        for msg in &recovered.messages {
            let entry = serde_json::json!({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "source": "session-recovery",
            });
            writeln!(f, "{}", serde_json::to_string(&entry)?)?;
        }
    }

    // Write full interaction log
    if !recovered.interactions.is_empty() {
        let date = recovered.interactions.first()
            .map(|i| i.timestamp.get(..10).unwrap_or("unknown"))
            .unwrap_or("unknown");
        let path = crux_dir.join(format!("analytics/interactions/{date}.jsonl"));
        let mut f = OpenOptions::new().create(true).append(true).open(&path)?;
        for interaction in &recovered.interactions {
            let entry = serde_json::json!({
                "tool": interaction.tool_name,
                "input": interaction.input_summary,
                "output": interaction.output_summary,
                "timestamp": interaction.timestamp,
                "source": "session-recovery",
            });
            writeln!(f, "{}", serde_json::to_string(&entry)?)?;
        }
    }

    let summary = format!(
        "Recovered: {} decisions, {} files, {} corrections, {} messages, {} interactions from session {}",
        recovered.key_decisions.len(),
        recovered.files_touched.len(),
        recovered.corrections.len(),
        recovered.messages.len(),
        recovered.interactions.len(),
        recovered.session_id,
    );
    Ok(summary)
}

/// Find Claude Code session files for a project directory.
pub fn find_sessions(project_dir: &Path, home: &Path) -> Vec<PathBuf> {
    let claude_projects = home.join(".claude/projects");
    if !claude_projects.exists() {
        return Vec::new();
    }

    // Claude Code uses project path with / replaced by -
    let project_hash = format!("-{}", project_dir.to_string_lossy().replace('/', "-"));
    let session_dir = claude_projects.join(&project_hash);

    if !session_dir.exists() {
        return Vec::new();
    }

    let mut sessions: Vec<PathBuf> = Vec::new();
    if let Ok(entries) = fs::read_dir(&session_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().map_or(false, |e| e == "jsonl") {
                sessions.push(path);
            }
        }
    }

    // Sort by modification time, most recent first
    sessions.sort_by(|a, b| {
        let a_time = fs::metadata(a).and_then(|m| m.modified()).ok();
        let b_time = fs::metadata(b).and_then(|m| m.modified()).ok();
        b_time.cmp(&a_time)
    });

    sessions
}

fn extract_text_content(content: &Value) -> String {
    match content {
        Value::String(s) => s.clone(),
        Value::Array(arr) => {
            arr.iter()
                .filter_map(|block| {
                    if block["type"].as_str() == Some("text") {
                        block["text"].as_str().map(String::from)
                    } else if block.is_string() {
                        Some(block.as_str().unwrap_or("").to_string())
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>()
                .join("\n")
        }
        _ => String::new(),
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        return s.to_string();
    }
    // Find the last char boundary at or before max
    let mut end = max;
    while end > 0 && !s.is_char_boundary(end) {
        end -= 1;
    }
    format!("{}...", &s[..end])
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn write_fixture(dir: &Path, lines: &[Value]) -> PathBuf {
        let path = dir.join("test-session.jsonl");
        let mut f = fs::File::create(&path).unwrap();
        for line in lines {
            writeln!(f, "{}", serde_json::to_string(line).unwrap()).unwrap();
        }
        path
    }

    #[test]
    fn parse_empty_file() {
        let tmp = TempDir::new().unwrap();
        let path = tmp.path().join("empty.jsonl");
        fs::write(&path, "").unwrap();
        let r = parse_session(&path);
        assert_eq!(r.total_lines, 0);
    }

    #[test]
    fn parse_user_and_assistant_messages() {
        let tmp = TempDir::new().unwrap();
        let path = write_fixture(tmp.path(), &[
            serde_json::json!({
                "type": "user",
                "sessionId": "test-123",
                "cwd": "/test/project",
                "timestamp": "2026-03-27T10:00:00Z",
                "message": {"role": "user", "content": "build the auth module"}
            }),
            serde_json::json!({
                "type": "assistant",
                "timestamp": "2026-03-27T10:00:05Z",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "I'll create the auth module with JWT tokens."}]}
            }),
        ]);
        let r = parse_session(&path);
        assert_eq!(r.session_id, "test-123");
        assert_eq!(r.project_dir, "/test/project");
        assert_eq!(r.messages.len(), 2);
    }

    #[test]
    fn parse_tool_use_extracts_files() {
        let tmp = TempDir::new().unwrap();
        let path = write_fixture(tmp.path(), &[
            serde_json::json!({
                "type": "assistant",
                "timestamp": "2026-03-27T10:00:00Z",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "t1", "name": "Edit", "input": {"file_path": "/test/auth.py"}}
                ]}
            }),
        ]);
        let r = parse_session(&path);
        assert!(r.files_touched.contains(&"/test/auth.py".to_string()));
        assert_eq!(r.interactions.len(), 1);
        assert_eq!(r.interactions[0].tool_name, "Edit");
    }

    #[test]
    fn parse_detects_corrections() {
        let tmp = TempDir::new().unwrap();
        let path = write_fixture(tmp.path(), &[
            serde_json::json!({
                "type": "user",
                "timestamp": "2026-03-27T10:00:00Z",
                "message": {"role": "user", "content": "no, that's wrong, use snake_case not camelCase"}
            }),
        ]);
        let r = parse_session(&path);
        assert_eq!(r.corrections.len(), 1);
    }

    #[test]
    fn parse_extracts_commit_messages() {
        let tmp = TempDir::new().unwrap();
        let path = write_fixture(tmp.path(), &[
            serde_json::json!({
                "type": "user",
                "timestamp": "2026-03-27T10:00:00Z",
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "[main abc123] Add OAuth2 authentication flow"}
                ]}
            }),
        ]);
        let r = parse_session(&path);
        assert!(r.key_decisions.iter().any(|d| d.contains("OAuth2")));
    }

    #[test]
    fn parse_handles_malformed_lines() {
        let tmp = TempDir::new().unwrap();
        let path = tmp.path().join("bad.jsonl");
        fs::write(&path, "not json\n{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello\"},\"timestamp\":\"2026-03-27\"}\n{broken\n").unwrap();
        let r = parse_session(&path);
        assert_eq!(r.parsed_lines, 1); // only the valid line
    }

    #[test]
    fn parse_nonexistent_file() {
        let r = parse_session(Path::new("/nonexistent/file.jsonl"));
        assert_eq!(r.total_lines, 0);
    }

    #[test]
    fn write_recovery_creates_files() {
        let tmp = TempDir::new().unwrap();
        let crux_dir = tmp.path().join(".crux");

        let recovered = RecoveredSession {
            session_id: "test-123".into(),
            working_on: "building auth".into(),
            key_decisions: vec!["use JWT".into()],
            files_touched: vec!["auth.py".into()],
            corrections: vec!["no, use snake_case".into()],
            messages: vec![ConversationEntry {
                role: "user".into(),
                content: "build auth".into(),
                timestamp: "2026-03-27T10:00:00Z".into(),
            }],
            interactions: vec![InteractionEntry {
                tool_name: "Edit".into(),
                input_summary: "auth.py".into(),
                output_summary: "ok".into(),
                timestamp: "2026-03-27T10:00:00Z".into(),
            }],
            ..Default::default()
        };

        let summary = write_recovery(&recovered, &crux_dir).unwrap();
        assert!(summary.contains("1 decisions"));
        assert!(crux_dir.join("sessions/state.json").exists());
        assert!(crux_dir.join("sessions/handoff.md").exists());
        assert!(crux_dir.join("corrections/corrections.jsonl").exists());
        assert!(crux_dir.join("analytics/conversations/2026-03-27.jsonl").exists());
        assert!(crux_dir.join("analytics/interactions/2026-03-27.jsonl").exists());
    }

    #[test]
    fn find_sessions_returns_empty_for_nonexistent() {
        let tmp = TempDir::new().unwrap();
        let sessions = find_sessions(Path::new("/test/project"), tmp.path());
        assert!(sessions.is_empty());
    }
}
