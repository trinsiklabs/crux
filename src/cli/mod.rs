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
    /// Show or regenerate handoff context
    Handoff,
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
