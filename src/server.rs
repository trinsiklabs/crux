//! Crux MCP Server — tools via rmcp.

use rmcp::handler::server::router::tool::ToolRouter;
use rmcp::handler::server::wrapper::Parameters;
use rmcp::model::ServerInfo;
use rmcp::{tool, tool_handler, tool_router, ServerHandler, ServiceExt};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

use crate::handlers::{git_context, knowledge};
use crate::impact::scorer;
use crate::memory;
use crate::safety::{preflight, pipeline, RiskLevel};
use crate::session;

// --- Parameter types ---

#[derive(Deserialize, JsonSchema)]
pub struct QueryParam {
    /// Search term
    pub query: String,
}

#[derive(Deserialize, JsonSchema)]
pub struct UpdateSessionParam {
    /// What you're currently working on
    pub working_on: Option<String>,
    /// A key decision to record
    pub add_decision: Option<String>,
    /// A file that was touched
    pub add_file: Option<String>,
}

#[derive(Deserialize, JsonSchema)]
pub struct HandoffParam {
    /// Handoff content text
    pub content: String,
}

#[derive(Deserialize, JsonSchema)]
pub struct FactParam {
    /// The fact to remember
    pub fact: String,
    /// 'project' or 'user' scope
    pub scope: Option<String>,
}

#[derive(Deserialize, JsonSchema)]
pub struct ImpactParam {
    /// Natural language task description
    pub prompt: String,
    /// Max results (default 20)
    pub top_n: Option<usize>,
}

#[derive(Deserialize, JsonSchema)]
pub struct ScriptParam {
    /// Script content to validate
    pub content: String,
}

#[derive(Deserialize, JsonSchema)]
pub struct RiskParam {
    /// Risk level: low, medium, high
    pub risk_level: String,
}

#[derive(Deserialize, JsonSchema)]
pub struct FileParam {
    /// File path relative to project root
    pub filepath: String,
}

#[derive(Deserialize, JsonSchema)]
pub struct TopNParam {
    /// Number of results
    pub top_n: Option<usize>,
}

// --- Server ---

#[derive(Debug, Clone)]
pub struct CruxServer {
    tool_router: ToolRouter<Self>,
    project_dir: PathBuf,
    home_dir: PathBuf,
}

impl CruxServer {
    pub fn new() -> Self {
        let project_dir = std::env::var("CRUX_PROJECT")
            .map(PathBuf::from)
            .unwrap_or_else(|_| std::env::current_dir().unwrap_or_default());
        let home_dir = std::env::var("CRUX_HOME")
            .or_else(|_| std::env::var("HOME"))
            .map(PathBuf::from)
            .unwrap_or_default();
        Self {
            tool_router: Self::tool_router(),
            project_dir,
            home_dir,
        }
    }

    fn crux_dir(&self) -> PathBuf {
        self.project_dir.join(".crux")
    }
}

#[tool_handler(router = self.tool_router)]
impl ServerHandler for CruxServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            instructions: Some(
                "Crux AI operating system. Call restore_context() on session start. \
                 Call update_session() after every significant action."
                    .into(),
            ),
            ..Default::default()
        }
    }
}

#[tool_router(router = tool_router)]
impl CruxServer {
    /// Get the current Crux session state.
    #[tool(description = "Get the current session state (active mode, tool, working context).")]
    async fn get_session_state(&self, _params: Parameters<()>) -> String {
        let state = session::load_session(&self.crux_dir());
        serde_json::to_string_pretty(&state).unwrap_or_default()
    }

    /// Update the current session state.
    #[tool(description = "Update session state — working_on, add_decision, add_file.")]
    async fn update_session(&self, params: Parameters<UpdateSessionParam>) -> String {
        let p = &params.0;
        let state = session::update_session(
            &self.crux_dir(),
            p.working_on.as_deref(),
            p.add_decision.as_deref(),
            p.add_file.as_deref(),
            None,
            None,
        );
        serde_json::to_string_pretty(&state).unwrap_or_default()
    }

    /// Restore full session context after a restart or tool switch.
    #[tool(description = "Restore session context. Call at the start of every new session.")]
    async fn restore_context(&self, _params: Parameters<()>) -> String {
        session::update_session(&self.crux_dir(), None, None, None, None, None);
        let state = session::load_session(&self.crux_dir());
        let handoff = session::read_handoff(&self.crux_dir());
        let mut parts = vec![
            format!("Mode: {}", state.active_mode),
            format!("Tool: {}", state.active_tool),
        ];
        if !state.working_on.is_empty() {
            parts.push(format!("Working on: {}", state.working_on));
        }
        if let Some(h) = handoff {
            parts.push(format!("Handoff:\n{h}"));
        }
        serde_json::to_string(&serde_json::json!({"context": parts.join("\n")}))
            .unwrap_or_default()
    }

    /// Write handoff context for the next session.
    #[tool(description = "Write handoff context for the next mode or tool switch.")]
    async fn write_handoff(&self, params: Parameters<HandoffParam>) -> String {
        let _ = session::write_handoff(&self.crux_dir(), &&params.0.content);
        r#"{"written": true}"#.into()
    }

    /// Read handoff context from previous session.
    #[tool(description = "Read handoff context left by a previous session.")]
    async fn read_handoff(&self, _params: Parameters<()>) -> String {
        match session::read_handoff(&self.crux_dir()) {
            Some(c) => serde_json::to_string(&serde_json::json!({"exists": true, "content": c}))
                .unwrap_or_default(),
            None => r#"{"exists": false}"#.into(),
        }
    }

    /// Search knowledge entries.
    #[tool(description = "Search knowledge entries across project and user scopes.")]
    async fn lookup_knowledge(&self, params: Parameters<QueryParam>) -> String {
        let results = knowledge::lookup_knowledge(
            &&params.0.query, None, &self.project_dir, &self.home_dir,
        );
        serde_json::to_string(&serde_json::json!({
            "entries": results, "total_found": results.len(),
        })).unwrap_or_default()
    }

    /// Remember a fact.
    #[tool(description = "Remember a fact for future sessions.")]
    async fn remember_fact(&self, params: Parameters<FactParam>) -> String {
        let p = &params.0;
        let scope = p.scope.as_deref().unwrap_or("project");
        let crux = if scope == "user" { self.home_dir.join(".crux") } else { self.crux_dir() };
        let entry = memory::MemoryEntry::new(&p.fact, "manual");
        let _ = memory::save_memory(&entry, scope, &crux);
        serde_json::to_string(&serde_json::json!({"saved": true, "fact": p.fact}))
            .unwrap_or_default()
    }

    /// Search memories.
    #[tool(description = "Search memories by keyword.")]
    async fn recall_memories(&self, params: Parameters<FactParam>) -> String {
        let p = &params.0;
        let scope = p.scope.as_deref().unwrap_or("project");
        let crux = if scope == "user" { self.home_dir.join(".crux") } else { self.crux_dir() };
        let results = memory::search_memories(&p.fact, scope, &crux);
        serde_json::to_string(&serde_json::json!({
            "memories": results.iter().map(|e| serde_json::json!({
                "id": e.id, "fact": e.fact, "confidence": e.confidence,
            })).collect::<Vec<_>>(),
            "total": results.len(),
        })).unwrap_or_default()
    }

    /// Rank files by relevance.
    #[tool(description = "Rank files by relevance to a prompt using git history and keywords.")]
    async fn analyze_impact(&self, params: Parameters<ImpactParam>) -> String {
        let p = &params.0;
        let results = scorer::rank_files(&self.project_dir, &p.prompt, p.top_n.unwrap_or(20), true);
        serde_json::to_string(&serde_json::json!({
            "files": results, "total": results.len(), "prompt": p.prompt,
        })).unwrap_or_default()
    }

    /// Validate a script.
    #[tool(description = "Validate a script against Crux safety conventions.")]
    async fn validate_script(&self, params: Parameters<ScriptParam>) -> String {
        let result = preflight::validate(&&params.0.content);
        serde_json::to_string(&result).unwrap_or_default()
    }

    /// Get active safety gates.
    #[tool(description = "Get active safety gates for a risk level.")]
    async fn get_active_gates(&self, params: Parameters<RiskParam>) -> String {
        let risk = RiskLevel::from_str(&&params.0.risk_level).unwrap_or(RiskLevel::Low);
        serde_json::to_string(&pipeline::get_config(risk)).unwrap_or_default()
    }

    /// Get git context for a file.
    #[tool(description = "Get git context for a file — recent history, risk.")]
    async fn git_context(&self, params: Parameters<FileParam>) -> String {
        let fp = &&params.0.filepath;
        let history = git_context::file_history(&self.project_dir, fp, 5);
        serde_json::to_string(&serde_json::json!({
            "file": fp, "recent_commits": history,
        })).unwrap_or_default()
    }

    /// Get current uncommitted changes.
    #[tool(description = "Get current uncommitted changes.")]
    async fn git_diff(&self, _params: Parameters<()>) -> String {
        let diff = git_context::current_diff(&self.project_dir);
        let branch = git_context::branch_context(&self.project_dir);
        serde_json::to_string(&serde_json::json!({
            "diff": diff,
            "branch": branch.map(|(b, c)| serde_json::json!({"name": b, "commits": c})),
        })).unwrap_or_default()
    }

    /// Find risky files.
    #[tool(description = "Find files with highest churn.")]
    async fn git_risky_files(&self, params: Parameters<TopNParam>) -> String {
        let risky = git_context::risky_files(&self.project_dir, params.0.top_n.unwrap_or(10));
        serde_json::to_string(&serde_json::json!({
            "files": risky.iter().map(|(f, c)| serde_json::json!({"file": f, "commits": c})).collect::<Vec<_>>(),
        })).unwrap_or_default()
    }

    /// Suggest commit message.
    #[tool(description = "Suggest a commit message from staged changes.")]
    async fn git_suggest_commit(&self, _params: Parameters<()>) -> String {
        let msg = git_context::suggest_commit(&self.project_dir);
        serde_json::to_string(&serde_json::json!({
            "message": msg, "has_staged": !msg.is_empty(),
        })).unwrap_or_default()
    }

    // --- Modes ---

    /// Get mode prompt text.
    #[tool(description = "Get the full prompt text for a specific mode.")]
    async fn get_mode_prompt(&self, params: Parameters<QueryParam>) -> String {
        let mode = &params.0.query;
        let mode_file = self.home_dir.join(".crux/modes").join(format!("{mode}.md"));
        match std::fs::read_to_string(&mode_file) {
            Ok(content) => serde_json::to_string(&serde_json::json!({"found": true, "mode": mode, "prompt": content})).unwrap_or_default(),
            Err(_) => serde_json::to_string(&serde_json::json!({"found": false, "mode": mode})).unwrap_or_default(),
        }
    }

    /// List all available modes.
    #[tool(description = "List all available Crux modes with descriptions.")]
    async fn list_modes(&self, _params: Parameters<()>) -> String {
        let modes_dir = self.home_dir.join(".crux/modes");
        let mut modes = Vec::new();
        if let Ok(entries) = std::fs::read_dir(&modes_dir) {
            for entry in entries.flatten() {
                if entry.path().extension().map_or(false, |e| e == "md") {
                    let name = entry.path().file_stem().unwrap_or_default().to_string_lossy().to_string();
                    modes.push(name);
                }
            }
        }
        modes.sort();
        serde_json::to_string(&serde_json::json!({"modes": modes, "total": modes.len()})).unwrap_or_default()
    }

    // --- Forget memory ---

    /// Forget a memory.
    #[tool(description = "Forget a memory by its ID.")]
    async fn forget_fact(&self, params: Parameters<QueryParam>) -> String {
        let forgotten = memory::forget_memory(&params.0.query, "project", &self.crux_dir());
        serde_json::to_string(&serde_json::json!({"forgotten": forgotten})).unwrap_or_default()
    }

    /// List all memories.
    #[tool(description = "List all stored memories.")]
    async fn list_all_memories(&self, _params: Parameters<()>) -> String {
        let entries = memory::load_memories("project", &self.crux_dir());
        serde_json::to_string(&serde_json::json!({
            "memories": entries.iter().map(|e| serde_json::json!({
                "id": e.id, "fact": e.fact, "confidence": e.confidence, "use_count": e.use_count,
            })).collect::<Vec<_>>(),
            "total": entries.len(),
        })).unwrap_or_default()
    }

    // --- Codebase indexing ---

    /// Search the codebase for files and symbols.
    #[tool(description = "Search the codebase for files and symbols matching a query.")]
    async fn search_code(&self, params: Parameters<QueryParam>) -> String {
        // Build catalog inline (lightweight for now)
        let catalog = crate::impact::keywords::grep_matches(&self.project_dir, &[params.0.query.clone()]);
        serde_json::to_string(&serde_json::json!({
            "results": catalog.keys().take(20).collect::<Vec<_>>(),
            "total": catalog.len(),
        })).unwrap_or_default()
    }

    // --- Correction logging ---

    /// Log a correction for continuous learning.
    #[tool(description = "Log a correction for continuous learning.")]
    async fn log_correction(&self, params: Parameters<HandoffParam>) -> String {
        // Append to corrections JSONL
        let corrections_dir = self.crux_dir().join("corrections");
        let _ = std::fs::create_dir_all(&corrections_dir);
        let path = corrections_dir.join("corrections.jsonl");
        let entry = serde_json::json!({
            "content": params.0.content,
            "timestamp": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        });
        let _ = std::fs::OpenOptions::new()
            .create(true).append(true).open(&path)
            .and_then(|mut f| {
                use std::io::Write;
                writeln!(f, "{}", serde_json::to_string(&entry).unwrap_or_default())
            });
        r#"{"logged": true}"#.into()
    }

    /// Log an interaction.
    #[tool(description = "Log a conversation message for continuous learning analysis.")]
    async fn log_interaction(&self, params: Parameters<HandoffParam>) -> String {
        let log_dir = self.crux_dir().join("analytics/interactions");
        let _ = std::fs::create_dir_all(&log_dir);
        let date = chrono::Utc::now().format("%Y-%m-%d").to_string();
        let path = log_dir.join(format!("{date}.jsonl"));
        let entry = serde_json::json!({
            "content": params.0.content,
            "timestamp": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        });
        let _ = std::fs::OpenOptions::new()
            .create(true).append(true).open(&path)
            .and_then(|mut f| {
                use std::io::Write;
                writeln!(f, "{}", serde_json::to_string(&entry).unwrap_or_default())
            });
        r#"{"logged": true}"#.into()
    }

    // --- Tool switching ---

    /// Switch to a different AI coding tool.
    #[tool(description = "Switch to a different AI coding tool, syncing configs.")]
    async fn switch_tool_to(&self, params: Parameters<QueryParam>) -> String {
        let tool_id = &params.0.query;
        session::auto_handoff(&self.crux_dir());
        let crux_binary = std::env::current_exe().unwrap_or_default().to_string_lossy().to_string();
        match crate::sync::generate_mcp_config(tool_id, &self.project_dir, &crux_binary) {
            Ok(true) => {
                let recipe = crate::recipes::get_recipe(tool_id);
                session::update_session(&self.crux_dir(), None, None, None, None, Some(tool_id));
                serde_json::to_string(&serde_json::json!({
                    "success": true,
                    "to_tool": tool_id,
                    "launch_command": recipe.map(|r| r.launch_command).unwrap_or_default(),
                    "restore_instruction": "Call restore_context() on first message.",
                })).unwrap_or_default()
            }
            Ok(false) => serde_json::to_string(&serde_json::json!({"success": false, "error": format!("Unknown tool: {tool_id}")})).unwrap_or_default(),
            Err(e) => serde_json::to_string(&serde_json::json!({"success": false, "error": e.to_string()})).unwrap_or_default(),
        }
    }

    // --- MCP server registry ---

    /// Register an external MCP server.
    #[tool(description = "Register an external MCP server for aggregation.")]
    async fn register_mcp_server(&self, params: Parameters<HandoffParam>) -> String {
        // Parse JSON from content field
        match serde_json::from_str::<serde_json::Value>(&params.0.content) {
            Ok(v) => {
                let name = v["name"].as_str().unwrap_or("unnamed");
                let cmd: Vec<String> = v["command"].as_array()
                    .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                    .unwrap_or_default();
                let _ = crate::registry::register_server(
                    &self.crux_dir(), name, cmd, std::collections::HashMap::new(), None, 30,
                );
                serde_json::to_string(&serde_json::json!({"registered": true, "name": name})).unwrap_or_default()
            }
            Err(_) => r#"{"registered": false, "error": "Invalid JSON"}"#.into(),
        }
    }

    /// List registered MCP servers.
    #[tool(description = "List all registered external MCP servers.")]
    async fn list_mcp_servers(&self, _params: Parameters<()>) -> String {
        let servers = crate::registry::list_servers(&self.crux_dir());
        serde_json::to_string(&serde_json::json!({
            "servers": servers.iter().map(|s| serde_json::json!({"name": s.name, "enabled": s.enabled})).collect::<Vec<_>>(),
            "total": servers.len(),
        })).unwrap_or_default()
    }

    // --- Health ---

    /// Run all health checks.
    #[tool(description = "Run all health checks and return a combined report.")]
    async fn verify_health(&self, _params: Parameters<()>) -> String {
        let crux = self.crux_dir();
        let checks = vec![
            ("crux_dir_exists", crux.exists()),
            ("sessions_exists", crux.join("sessions").exists()),
            ("state_json_exists", crux.join("sessions/state.json").exists()),
            ("knowledge_exists", crux.join("knowledge").exists()),
        ];
        let passed = checks.iter().filter(|(_, ok)| *ok).count();
        serde_json::to_string(&serde_json::json!({
            "checks": checks.iter().map(|(n, ok)| serde_json::json!({"name": n, "passed": ok})).collect::<Vec<_>>(),
            "summary": {"total": checks.len(), "passed": passed, "all_passed": passed == checks.len()},
        })).unwrap_or_default()
    }

    /// Get project context.
    #[tool(description = "Read the PROJECT.md context file.")]
    async fn get_project_context(&self, _params: Parameters<()>) -> String {
        let path = self.crux_dir().join("context/PROJECT.md");
        match std::fs::read_to_string(&path) {
            Ok(content) => serde_json::to_string(&serde_json::json!({"found": true, "content": content})).unwrap_or_default(),
            Err(_) => r#"{"found": false}"#.into(),
        }
    }

    /// Get daily digest.
    #[tool(description = "Retrieve a daily digest.")]
    async fn get_digest(&self, _params: Parameters<()>) -> String {
        let date = chrono::Utc::now().format("%Y-%m-%d").to_string();
        let path = self.crux_dir().join(format!("analytics/digests/{date}.md"));
        match std::fs::read_to_string(&path) {
            Ok(content) => serde_json::to_string(&serde_json::json!({"found": true, "date": date, "content": content})).unwrap_or_default(),
            Err(_) => serde_json::to_string(&serde_json::json!({"found": false, "date": date})).unwrap_or_default(),
        }
    }

    /// Promote knowledge entry.
    #[tool(description = "Promote a knowledge entry from project to user scope.")]
    async fn promote_knowledge(&self, params: Parameters<QueryParam>) -> String {
        match knowledge::promote_knowledge(&params.0.query, &self.project_dir, &self.home_dir) {
            Ok(true) => serde_json::to_string(&serde_json::json!({"promoted": true})).unwrap_or_default(),
            Ok(false) => serde_json::to_string(&serde_json::json!({"promoted": false, "error": "Entry not found"})).unwrap_or_default(),
            Err(e) => serde_json::to_string(&serde_json::json!({"promoted": false, "error": e.to_string()})).unwrap_or_default(),
        }
    }
}

/// Start the MCP server on stdio transport.
pub async fn run_server() -> anyhow::Result<()> {
    let server = CruxServer::new();
    let service = server.serve(rmcp::transport::io::stdio()).await?;
    service.waiting().await?;
    Ok(())
}
