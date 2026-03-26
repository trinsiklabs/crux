//! Hook handlers — infrastructure enforcement without LLM cooperation.
//!
//! Auto-captures session state from tool call patterns:
//! - PostToolUse: files from Edit/Write, decisions from git commits
//! - Stop: auto-writes handoff
//! - UserPromptSubmit: correction detection (10 regex patterns)

use regex::Regex;
use std::path::Path;
use std::sync::LazyLock;

use crate::session;

static CORRECTION_PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    [
        r"(?i)\bno,?\s+(actually|not|that's wrong|incorrect)",
        r"(?i)\binstead,?\s+(use|do|try|make)",
        r"(?i)\bthat's not (right|correct|what I)",
        r"(?i)\bdon't\s+(do|use|add|make|create)",
        r"(?i)\bwrong\b.{0,20}\b(should|use|be|do)",
        r"(?i)\bactually,?\s+(it|the|we|I|this|that)",
        r"(?i)\bI (said|meant|want|need)\s+",
        r"(?i)\bplease\s+(don't|stop|remove|undo|revert)",
        r"(?i)\bnot\s+what\s+I\s+(asked|wanted|meant)",
        r"(?i)\b(revert|undo|roll\s*back)\s+(that|this|the|it)",
    ]
    .iter()
    .filter_map(|p| Regex::new(p).ok())
    .collect()
});

static COMMIT_OUTPUT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[[\w/.-]+\s+\w+\]\s+(.+)").unwrap()
});

/// Check if a user message contains a correction.
pub fn is_correction(prompt: &str) -> bool {
    CORRECTION_PATTERNS.iter().any(|re| re.is_match(prompt))
}

/// Extract commit message from tool output.
pub fn extract_commit_message(command: &str, output: &str) -> Option<String> {
    if !command.contains("git commit") {
        return None;
    }

    // Prefer output (always clean)
    if let Some(cap) = COMMIT_OUTPUT_RE.captures(output) {
        let msg = cap[1].trim();
        if !msg.is_empty() && !msg.starts_with("$(") {
            return Some(msg[..msg.len().min(256)].to_string());
        }
    }

    None
}

/// Handle PostToolUse — auto-capture files and decisions.
pub fn on_tool_result(
    tool_name: &str,
    tool_input: &serde_json::Value,
    tool_output: &str,
    crux_dir: &Path,
) {
    // Track files from Edit/Write
    if tool_name == "Edit" || tool_name == "Write" {
        if let Some(path) = tool_input.get("file_path").and_then(|v| v.as_str()) {
            session::update_session(crux_dir, None, None, Some(path), None, None);
        }
    }

    // Capture decisions from git commits
    if tool_name == "Bash" {
        let command = tool_input.get("command").and_then(|v| v.as_str()).unwrap_or("");
        if let Some(msg) = extract_commit_message(command, tool_output) {
            session::update_session(crux_dir, None, Some(&msg), None, None, None);
        }
    }
}

/// Handle Stop — auto-write handoff.
pub fn on_stop(crux_dir: &Path) {
    session::auto_handoff(crux_dir);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_corrections() {
        assert!(is_correction("no, that's wrong, use snake_case"));
        assert!(is_correction("actually, it should be async"));
        assert!(is_correction("don't do that"));
        assert!(is_correction("revert that change"));
        assert!(is_correction("please stop adding comments"));
    }

    #[test]
    fn no_false_positives() {
        assert!(!is_correction("looks good, ship it"));
        assert!(!is_correction("can you add a test?"));
        assert!(!is_correction("what does this function do?"));
    }

    #[test]
    fn extracts_commit_from_output() {
        let msg = extract_commit_message(
            "git commit -m \"test\"",
            "[main abc123] Fix authentication bug",
        );
        assert_eq!(msg, Some("Fix authentication bug".into()));
    }

    #[test]
    fn skips_heredoc_commits() {
        let msg = extract_commit_message(
            "git commit -m \"$(cat <<'EOF'\nstuff\nEOF\n)\"",
            "[main abc123] $(cat stuff",
        );
        assert!(msg.is_none());
    }

    #[test]
    fn skips_non_commits() {
        assert!(extract_commit_message("ls -la", "total 0").is_none());
    }

    #[test]
    fn on_tool_result_tracks_files() {
        let tmp = tempfile::TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        std::fs::create_dir_all(crux.join("sessions")).unwrap();
        session::save_session(&session::SessionState::new(), &crux).unwrap();

        let input = serde_json::json!({"file_path": "auth.py"});
        on_tool_result("Edit", &input, "", &crux);

        let state = session::load_session(&crux);
        assert!(state.files_touched.contains(&"auth.py".to_string()));
    }

    #[test]
    fn on_tool_result_captures_decisions() {
        let tmp = tempfile::TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        std::fs::create_dir_all(crux.join("sessions")).unwrap();
        session::save_session(&session::SessionState::new(), &crux).unwrap();

        let input = serde_json::json!({"command": "git commit -m \"test\""});
        on_tool_result("Bash", &input, "[main abc] Add OAuth flow", &crux);

        let state = session::load_session(&crux);
        assert!(state.key_decisions.iter().any(|d| d.contains("OAuth")));
    }

    #[test]
    fn on_stop_writes_handoff() {
        let tmp = tempfile::TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        std::fs::create_dir_all(crux.join("sessions")).unwrap();
        let mut state = session::SessionState::new();
        state.working_on = "test task".into();
        session::save_session(&state, &crux).unwrap();

        on_stop(&crux);

        let handoff = session::read_handoff(&crux);
        assert!(handoff.is_some());
        assert!(handoff.unwrap().contains("test task"));
    }
}
