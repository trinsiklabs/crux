//! CLI interface via clap — all subcommands call handler functions directly.

use clap::Parser;
use std::path::PathBuf;

use crate::handlers::{git_context, knowledge};
use crate::impact::scorer;
use crate::memory;
use crate::paths;
use crate::session;

#[derive(Parser)]
#[command(name = "crux", about = "Self-improving AI operating system — single binary, zero dependencies")]
pub struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(clap::Subcommand)]
enum Commands {
    /// Show runtime status and health checks
    Status,
    /// Switch to a different AI tool
    Switch { tool: String },
    /// Run health checks
    Health,
    /// Search knowledge entries
    Knowledge { query: String },
    /// Find files relevant to a task
    Impact {
        prompt: String,
        #[arg(default_value = "10")]
        top_n: usize,
    },
    /// Show daily digest
    Digest,
    /// MCP server management
    Mcp {
        #[command(subcommand)]
        cmd: McpCommands,
    },
    /// Interactive setup
    Setup,
    /// Show version
    Version,
    /// Initialize .crux/ in current project
    Init,
    /// Adopt project into Crux — init + git scan + MCP config + session ingest
    Adopt {
        /// Target tool (claude-code, cruxcli, opencode, cursor)
        #[arg(default_value = "claude-code")]
        tool: String,
    },
    /// Show or regenerate handoff context
    Handoff,
    /// Handle Claude Code hook events (called by .claude/settings.local.json)
    Hook {
        /// Event name: SessionStart, PostToolUse, UserPromptSubmit, Stop
        event: String,
    },
    /// Recover a corrupted Claude Code session
    Recover {
        /// Path to .jsonl file, or session ID
        path: Option<String>,
    },
    /// Remember a fact
    Remember { fact: String },
    /// Recall memories matching a query
    Recall { query: String },
}

#[derive(clap::Subcommand)]
enum McpCommands {
    /// Start MCP server on stdio
    Start,
    /// Show server status and tools
    Status,
}

impl Cli {
    pub async fn run(self) {
        let project = paths::project_dir();
        let crux = paths::project_crux_dir();
        let home = paths::user_crux_dir();
        let home_root = home.parent().unwrap_or(&home).to_path_buf();

        match self.command {
            Some(Commands::Version) | None => {
                println!("crux {}", env!("CARGO_PKG_VERSION"));
            }

            Some(Commands::Status) => {
                let state = session::load_session(&crux);
                println!("Crux Status\n");
                println!("  Mode:       {}", state.active_mode);
                println!("  Tool:       {}", if state.active_tool.is_empty() { "not set" } else { &state.active_tool });
                println!("  Working on: {}", if state.working_on.is_empty() { "(none)" } else { &state.working_on });
                println!("  Decisions:  {}", state.key_decisions.len());
                println!("  Files:      {}", state.files_touched.len());
                println!("  Pending:    {}", state.pending.len());
                println!("  Updated:    {}", state.updated_at);
            }

            Some(Commands::Health) => {
                // Basic health checks
                let checks = vec![
                    (".crux/ exists", crux.exists()),
                    ("sessions/ exists", crux.join("sessions").exists()),
                    ("state.json exists", crux.join("sessions/state.json").exists()),
                    ("knowledge/ exists", crux.join("knowledge").exists()),
                    ("memory/ exists", crux.join("memory").exists()),
                ];
                println!("Health Checks\n");
                let mut passed = 0;
                for (name, ok) in &checks {
                    let mark = if *ok { "\x1b[32m✓\x1b[0m" } else { "\x1b[31m✗\x1b[0m" };
                    println!("  {mark} {name}");
                    if *ok { passed += 1; }
                }
                println!("\n{passed}/{} checks passed", checks.len());
            }

            Some(Commands::Switch { tool }) => {
                println!("Switching to {tool}...");
                let recipe = crate::recipes::get_recipe(&tool);
                match recipe {
                    Some(r) => {
                        session::auto_handoff(&crux);
                        session::update_session(&crux, None, None, None, None, Some(&tool));
                        println!("  Config: {}", r.config_file);
                        println!("  Launch: {}", r.launch_command);
                        println!("  Run restore_context() on first message.");
                    }
                    None => eprintln!("Unknown tool: {tool}. Supported: claude-code, cruxcli, opencode, cursor, windsurf, zed"),
                }
            }

            Some(Commands::Knowledge { query }) => {
                let results = knowledge::lookup_knowledge(&query, None, &project, &home_root);
                if results.is_empty() {
                    println!("No knowledge entries found for '{query}'.");
                } else {
                    println!("Found {} entries:\n", results.len());
                    for entry in &results {
                        println!("  [{}] {}", entry.scope, entry.name);
                        if !entry.preview.is_empty() {
                            println!("       {}", &entry.preview[..entry.preview.len().min(100)]);
                        }
                    }
                }
            }

            Some(Commands::Impact { prompt, top_n }) => {
                let results = scorer::rank_files(&project, &prompt, top_n, true);
                if results.is_empty() {
                    println!("No relevant files found.");
                } else {
                    println!("Top {} files for: {prompt}\n", results.len());
                    for r in &results {
                        let reasons: String = r.reasons.iter()
                            .filter(|(_, v)| **v > 0.0)
                            .map(|(k, v)| format!("{k}={v:.2}"))
                            .collect::<Vec<_>>()
                            .join(", ");
                        println!("  {:.3}  {}", r.score, r.path);
                        if !reasons.is_empty() {
                            println!("       {reasons}");
                        }
                    }
                }
            }

            Some(Commands::Digest) => {
                println!("Digest: not yet implemented in Rust binary.");
            }

            Some(Commands::Init) => {
                match crate::init::init_project(&project) {
                    Ok(created) => {
                        if created.is_empty() {
                            println!(".crux/ already initialized.");
                        } else {
                            println!("Created .crux/ with {} directories.", created.len());
                        }
                    }
                    Err(e) => eprintln!("Init failed: {e}"),
                }
            }

            Some(Commands::Handoff) => {
                let content = session::auto_handoff(&crux);
                println!("{content}");
            }

            Some(Commands::Hook { event }) => {
                // Read JSON from stdin (Claude Code passes hook data via stdin)
                let input: serde_json::Value = {
                    let mut buf = String::new();
                    if std::io::Read::read_to_string(&mut std::io::stdin(), &mut buf).is_ok() && !buf.is_empty() {
                        serde_json::from_str(&buf).unwrap_or(serde_json::json!({}))
                    } else {
                        serde_json::json!({})
                    }
                };

                match event.as_str() {
                    "SessionStart" => {
                        let mut state = session::load_session(&crux);

                        // Check staleness — archive old state, start fresh
                        if state.is_stale() {
                            let history_dir = crux.join("sessions/history");
                            let _ = std::fs::create_dir_all(&history_dir);
                            let _ = std::fs::rename(
                                crux.join("sessions/state.json"),
                                history_dir.join(format!("{}.json", chrono::Utc::now().format("%Y-%m-%d-%H%M%S"))),
                            );
                            state = session::SessionState::new();
                        }

                        // Detect project type and check mode match
                        if let Some(pt) = crate::context::detect_project_type(&project) {
                            if state.active_mode == "build-py" && pt.mode != "build-py" && pt.confidence > 0.8 {
                                state.active_mode = pt.mode;
                            }
                        }

                        // Clear session-scoped fields on new session start
                        state.working_on.clear();
                        state.pending.clear();

                        session::update_session(&crux, None, None, None, None, Some("claude-code"));

                        let mut parts = vec![];

                        // Mode prompt
                        let mode_file = home.join("modes").join(format!("{}.md", state.active_mode));
                        if let Ok(prompt) = std::fs::read_to_string(&mode_file) {
                            parts.push(format!("## Active Mode: {}\n{}", state.active_mode, prompt));
                        }

                        // Session state
                        parts.push(format!("## Session State"));
                        parts.push(format!("- Mode: {}", state.active_mode));
                        parts.push(format!("- Tool: claude-code"));
                        if !state.working_on.is_empty() {
                            parts.push(format!("- Working on: {}", state.working_on));
                        }

                        // Recent decisions
                        let clean: Vec<&str> = state.key_decisions.iter()
                            .filter(|d| !d.starts_with("$(") && d.len() < 300)
                            .map(|s| s.as_str()).collect();
                        if !clean.is_empty() {
                            parts.push(format!("\n## Key Decisions (last {})", clean.len().min(5)));
                            for d in clean.iter().rev().take(5).rev() {
                                parts.push(format!("- {d}"));
                            }
                        }

                        let output = serde_json::json!({"status": "ok", "context": parts.join("\n")});
                        println!("{}", serde_json::to_string(&output).unwrap_or_default());
                    }

                    "PostToolUse" => {
                        let tool_name = input["tool_name"].as_str().unwrap_or("");
                        let tool_input = &input["tool_input"];
                        let tool_output = input["tool_output"].as_str().unwrap_or("");

                        crate::hooks::on_tool_result(tool_name, tool_input, tool_output, &crux);

                        let output = serde_json::json!({"status": "ok"});
                        println!("{}", serde_json::to_string(&output).unwrap_or_default());
                    }

                    "UserPromptSubmit" => {
                        let prompt = input["prompt"].as_str().unwrap_or("");
                        let is_correction = crate::hooks::is_correction(prompt);

                        if is_correction {
                            // Log correction
                            let corrections_dir = crux.join("corrections");
                            let _ = std::fs::create_dir_all(&corrections_dir);
                            let path = corrections_dir.join("corrections.jsonl");
                            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&path) {
                                let entry = serde_json::json!({
                                    "content": &prompt[..prompt.len().min(500)],
                                    "timestamp": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
                                });
                                let _ = std::io::Write::write_all(&mut f, format!("{}\n", serde_json::to_string(&entry).unwrap_or_default()).as_bytes());
                            }
                        }

                        // Log conversation
                        let log_dir = crux.join("analytics/conversations");
                        let _ = std::fs::create_dir_all(&log_dir);
                        let date = chrono::Utc::now().format("%Y-%m-%d").to_string();
                        let path = log_dir.join(format!("{date}.jsonl"));
                        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&path) {
                            let state = session::load_session(&crux);
                            let entry = serde_json::json!({
                                "role": "user",
                                "content": &prompt[..prompt.len().min(2000)],
                                "timestamp": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
                                "mode": state.active_mode,
                                "tool": "claude-code",
                            });
                            let _ = std::io::Write::write_all(&mut f, format!("{}\n", serde_json::to_string(&entry).unwrap_or_default()).as_bytes());
                        }

                        let output = serde_json::json!({"status": "ok", "correction_detected": is_correction});
                        println!("{}", serde_json::to_string(&output).unwrap_or_default());
                    }

                    "Stop" => {
                        crate::hooks::on_stop(&crux);
                        let output = serde_json::json!({"status": "ok"});
                        println!("{}", serde_json::to_string(&output).unwrap_or_default());
                    }

                    other => {
                        let output = serde_json::json!({"status": "error", "message": format!("Unknown event: {other}")});
                        println!("{}", serde_json::to_string(&output).unwrap_or_default());
                    }
                }
            }

            Some(Commands::Adopt { tool }) => {
                println!("Adopting project into Crux...\n");

                // Step 1: Init .crux/
                match crate::init::init_project(&project) {
                    Ok(created) => {
                        if created.is_empty() {
                            println!("  .crux/ already initialized");
                        } else {
                            println!("  Created .crux/ ({} dirs)", created.len());
                        }
                    }
                    Err(e) => {
                        eprintln!("  Init failed: {e}");
                        return;
                    }
                }
                let _ = crate::init::init_user(&home_root);

                // Step 2: Scan git history
                let churn = crate::impact::git::churn(&project, 90);
                let recent_files: Vec<&str> = {
                    let mut pairs: Vec<(&str, u32)> = churn.iter().map(|(k, v)| (k.as_str(), *v)).collect();
                    pairs.sort_by(|a, b| b.1.cmp(&a.1));
                    pairs.into_iter().take(20).map(|(f, _)| f).collect()
                };
                println!("  Git history: {} files with recent activity", churn.len());

                // Step 3: Write MCP config for target tool
                let crux_binary = std::env::current_exe().unwrap_or_default().to_string_lossy().to_string();
                match crate::sync::generate_mcp_config(&tool, &project, &crux_binary) {
                    Ok(true) => println!("  MCP config: written for {tool}"),
                    Ok(false) => eprintln!("  MCP config: unknown tool '{tool}'"),
                    Err(e) => eprintln!("  MCP config: {e}"),
                }

                // Step 4: Check for Claude Code sessions to ingest
                let sessions = crate::recover::find_sessions(&project, &home_root);
                if !sessions.is_empty() {
                    println!("  Found {} Claude Code session(s)", sessions.len());
                    let most_recent = &sessions[0];
                    let recovered = crate::recover::parse_session(most_recent);
                    if recovered.parsed_lines > 0 {
                        match crate::recover::write_recovery(&recovered, &crux) {
                            Ok(summary) => println!("  Ingested: {summary}"),
                            Err(e) => eprintln!("  Ingest failed: {e}"),
                        }
                    }
                } else {
                    // No Claude Code sessions — create initial state from git
                    let state = session::SessionState {
                        active_mode: "build-py".into(),
                        active_tool: tool.clone(),
                        working_on: String::new(),
                        files_touched: recent_files.iter().map(|f| f.to_string()).collect(),
                        ..session::SessionState::new()
                    };
                    let _ = session::save_session(&state, &crux);
                    println!("  Session state: initialized from git history");
                }

                // Step 5: Import CLAUDE.md if present
                let claude_md = project.join("CLAUDE.md");
                if claude_md.exists() {
                    if let Ok(content) = std::fs::read_to_string(&claude_md) {
                        let knowledge_dir = crux.join("knowledge");
                        let _ = std::fs::write(knowledge_dir.join("claude-md-import.md"), &content);
                        println!("  CLAUDE.md: imported as knowledge entry");
                    }
                }

                // Step 6: Generate Claude Code hooks if tool is claude-code
                if tool == "claude-code" {
                    let crux_binary = std::env::current_exe().unwrap_or_default().to_string_lossy().to_string();
                    let claude_dir = project.join(".claude");
                    let _ = std::fs::create_dir_all(&claude_dir);
                    let settings = serde_json::json!({
                        "permissions": {
                            "allow": ["Bash(cargo:*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push:*)", "Bash(gh pr:*)"]
                        },
                        "hooks": {
                            "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": format!("{crux_binary} hook SessionStart")}]}],
                            "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": format!("{crux_binary} hook PostToolUse")}]}],
                            "UserPromptSubmit": [{"matcher": "", "hooks": [{"type": "command", "command": format!("{crux_binary} hook UserPromptSubmit")}]}],
                            "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": format!("{crux_binary} hook Stop")}]}],
                        }
                    });
                    let settings_path = claude_dir.join("settings.local.json");
                    let _ = std::fs::write(&settings_path, serde_json::to_string_pretty(&settings).unwrap_or_default());
                    println!("  Claude Code hooks: written to .claude/settings.local.json");
                }

                println!("\nAdoption complete. Start {tool} and call restore_context().");
            }

            Some(Commands::Recover { path }) => {
                let session_path = if let Some(p) = path {
                    std::path::PathBuf::from(p)
                } else {
                    // Auto-find most recent session for this project
                    let sessions = crate::recover::find_sessions(&project, &home_root);
                    if sessions.is_empty() {
                        eprintln!("No Claude Code sessions found for this project.");
                        eprintln!("Usage: crux recover <path-to-session.jsonl>");
                        return;
                    }
                    println!("Found {} session(s). Recovering most recent...", sessions.len());
                    sessions[0].clone()
                };

                println!("Parsing: {}", session_path.display());
                let recovered = crate::recover::parse_session(&session_path);
                println!("  Parsed {}/{} lines", recovered.parsed_lines, recovered.total_lines);
                println!("  Messages: {}", recovered.messages.len());
                println!("  Interactions: {}", recovered.interactions.len());
                println!("  Decisions: {}", recovered.key_decisions.len());
                println!("  Files: {}", recovered.files_touched.len());
                println!("  Corrections: {}", recovered.corrections.len());

                match crate::recover::write_recovery(&recovered, &crux) {
                    Ok(summary) => println!("\n{summary}"),
                    Err(e) => eprintln!("Write failed: {e}"),
                }
            }

            Some(Commands::Remember { fact }) => {
                let entry = memory::MemoryEntry::new(&fact, "manual");
                match memory::save_memory(&entry, "project", &crux) {
                    Ok(_) => println!("Remembered: {fact}"),
                    Err(e) => eprintln!("Failed: {e}"),
                }
            }

            Some(Commands::Recall { query }) => {
                let results = memory::search_memories(&query, "project", &crux);
                if results.is_empty() {
                    println!("No memories match '{query}'.");
                } else {
                    for m in &results {
                        println!("  [{}] {} (confidence: {:.1})", m.id, m.fact, m.confidence);
                    }
                }
            }

            Some(Commands::Mcp { cmd }) => match cmd {
                McpCommands::Start => {
                    if let Err(e) = crate::server::run_server().await {
                        eprintln!("MCP server error: {e}");
                        std::process::exit(1);
                    }
                }
                McpCommands::Status => {
                    println!("Crux MCP Server: 15 tools registered");
                    println!("Binary: {}", std::env::current_exe().unwrap_or_default().display());
                    println!("Project: {}", project.display());
                }
            },

            Some(Commands::Setup) => {
                // Initialize project and user
                let _ = crate::init::init_project(&project);
                let _ = crate::init::init_user(&home_root);
                println!("Crux initialized.");
                println!("  Project: {}", crux.display());
                println!("  User:    {}", home.display());
                println!("\nTo connect your AI tool, add this to your MCP config:");
                println!("  command: {:?}", std::env::current_exe().unwrap_or_default());
                println!("  args: [\"mcp\", \"start\"]");
            }
        }
    }
}
