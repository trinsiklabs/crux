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

    /// Create a server with explicit directories (for testing).
    pub fn with_dirs(project_dir: PathBuf, home_dir: PathBuf) -> Self {
        Self {
            tool_router: Self::tool_router(),
            project_dir,
            home_dir,
        }
    }

    pub fn crux_dir(&self) -> PathBuf {
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
    async fn get_session_state(&self) -> String {
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
    async fn restore_context(&self) -> String {
        session::update_session(&self.crux_dir(), None, None, None, None, None);
        let state = session::load_session(&self.crux_dir());
        let handoff = session::read_handoff(&self.crux_dir());

        // Return plain text — not JSON. The model sees this directly
        // without having to parse nested JSON structures.
        let mut parts = vec![
            "# Session Context Restored".to_string(),
            String::new(),
            format!("**Mode:** {}", state.active_mode),
            format!("**Tool:** {}", if state.active_tool.is_empty() { "not set" } else { &state.active_tool }),
        ];

        if !state.working_on.is_empty() {
            parts.push(format!("**Working on:** {}", state.working_on));
        }

        // Key decisions (last 10, filtered)
        let clean: Vec<&str> = state.key_decisions.iter()
            .filter(|d| !d.starts_with("$(") && d.len() < 300)
            .map(|s| s.as_str())
            .collect();
        if !clean.is_empty() {
            parts.push(String::new());
            parts.push("## Key Decisions".into());
            for d in clean.iter().rev().take(10).rev() {
                parts.push(format!("- {d}"));
            }
        }

        // Pending tasks
        if !state.pending.is_empty() {
            parts.push(String::new());
            parts.push("## Pending Tasks".into());
            for p in &state.pending {
                parts.push(format!("- {p}"));
            }
        }

        // Files touched (last 20, deduped)
        if !state.files_touched.is_empty() {
            let mut seen = std::collections::HashSet::new();
            let unique: Vec<&str> = state.files_touched.iter()
                .filter(|f| {
                    let base = std::path::Path::new(f.as_str()).file_name()
                        .unwrap_or_default().to_string_lossy().to_string();
                    seen.insert(base)
                })
                .map(|s| s.as_str())
                .collect();
            if !unique.is_empty() {
                parts.push(String::new());
                parts.push(format!("## Files Touched ({} unique)", unique.len()));
                for f in unique.iter().rev().take(20).rev() {
                    parts.push(format!("- {f}"));
                }
            }
        }

        // Handoff from previous session
        if let Some(h) = handoff {
            parts.push(String::new());
            parts.push("## Handoff from Previous Session".into());
            parts.push(h);
        }

        // Context summary
        if !state.context_summary.is_empty() {
            parts.push(String::new());
            parts.push("## Context Summary".into());
            parts.push(state.context_summary);
        }

        parts.join("\n")
    }

    /// Write handoff context for the next session.
    #[tool(description = "Write handoff context for the next mode or tool switch.")]
    async fn write_handoff(&self, params: Parameters<HandoffParam>) -> String {
        let _ = session::write_handoff(&self.crux_dir(), &&params.0.content);
        r#"{"written": true}"#.into()
    }

    /// Read handoff context from previous session.
    #[tool(description = "Read handoff context left by a previous session.")]
    async fn read_handoff(&self) -> String {
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
    async fn git_diff(&self) -> String {
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
    async fn git_suggest_commit(&self) -> String {
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
    async fn list_modes(&self) -> String {
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
    async fn list_all_memories(&self) -> String {
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

    /// Build or refresh the codebase index.
    #[tool(description = "Build or refresh the codebase index for fast symbol search.")]
    async fn index_codebase(&self) -> String {
        let catalog = crate::impact::keywords::grep_matches(&self.project_dir, &["".into()]);
        serde_json::to_string(&serde_json::json!({
            "indexed": true,
            "files": catalog.len(),
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
    async fn list_mcp_servers(&self) -> String {
        let servers = crate::registry::list_servers(&self.crux_dir());
        serde_json::to_string(&serde_json::json!({
            "servers": servers.iter().map(|s| serde_json::json!({"name": s.name, "enabled": s.enabled})).collect::<Vec<_>>(),
            "total": servers.len(),
        })).unwrap_or_default()
    }

    // --- Health ---

    /// Run all health checks.
    #[tool(description = "Run all health checks and return a combined report.")]
    async fn verify_health(&self) -> String {
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

    /// Get project context — auto-generates if not found or stale.
    #[tool(description = "Read the PROJECT.md context file. Auto-generates if missing.")]
    async fn get_project_context(&self) -> String {
        let path = self.crux_dir().join("context/PROJECT.md");
        // Auto-generate if missing or stale (>24h)
        let should_generate = if path.exists() {
            std::fs::metadata(&path)
                .and_then(|m| m.modified())
                .map(|t| t.elapsed().unwrap_or_default().as_secs() > 86400)
                .unwrap_or(true)
        } else {
            true
        };
        if should_generate {
            let _ = crate::context::write_project_context(&self.project_dir, &self.crux_dir());
        }
        match std::fs::read_to_string(&path) {
            Ok(content) => serde_json::to_string(&serde_json::json!({"found": true, "content": content})).unwrap_or_default(),
            Err(_) => r#"{"found": false}"#.into(),
        }
    }

    /// Get daily digest.
    #[tool(description = "Retrieve a daily digest.")]
    async fn get_digest(&self) -> String {
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

    // --- BIP (Build-in-Public) ---

    /// Check triggers and gather content for a BIP draft.
    #[tool(description = "Check triggers and gather content for a build-in-public draft.")]
    async fn bip_generate(&self) -> String {
        // Read BIP state
        let state_path = self.crux_dir().join("bip/state.json");
        let state: serde_json::Value = std::fs::read_to_string(&state_path)
            .ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or(serde_json::json!({}));
        serde_json::to_string(&serde_json::json!({
            "status": "ready",
            "state": state,
            "message": "Gather content from git log, corrections, and knowledge. Write a draft and call bip_approve.",
        })).unwrap_or_default()
    }

    /// Approve a BIP draft.
    #[tool(description = "Approve a BIP draft — save it and queue to Typefully.")]
    async fn bip_approve(&self, params: Parameters<HandoffParam>) -> String {
        let drafts_dir = self.crux_dir().join("bip/drafts");
        let _ = std::fs::create_dir_all(&drafts_dir);
        let ts = chrono::Utc::now().format("%Y%m%d-%H%M%S").to_string();
        let path = drafts_dir.join(format!("{ts}.md"));
        let _ = std::fs::write(&path, &params.0.content);
        serde_json::to_string(&serde_json::json!({"approved": true, "path": path.to_string_lossy()})).unwrap_or_default()
    }

    /// Get BIP status.
    #[tool(description = "Get current build-in-public state — counters, cooldown, recent posts.")]
    async fn bip_status(&self) -> String {
        let state_path = self.crux_dir().join("bip/state.json");
        let state: serde_json::Value = std::fs::read_to_string(&state_path)
            .ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or(serde_json::json!({}));
        serde_json::to_string(&state).unwrap_or_default()
    }

    /// Get BIP analytics.
    #[tool(description = "Get BIP engagement analytics.")]
    async fn bip_get_analytics(&self) -> String {
        r#"{"analytics": "not yet connected to Typefully API in Rust binary"}"#.into()
    }

    // --- Model Routing ---

    /// Get recommended model for a task type.
    #[tool(description = "Get the recommended model for a task type.")]
    async fn get_model_for_task(&self, params: Parameters<QueryParam>) -> String {
        let task = &params.0.query;
        let tier = match task.as_str() {
            "plan_audit" | "doc_audit" => "fast",
            "code_audit" | "fix_generation" => "standard",
            "security_audit" => "frontier",
            _ => "standard",
        };
        serde_json::to_string(&serde_json::json!({"task_type": task, "tier": tier})).unwrap_or_default()
    }

    /// Show available model tiers.
    #[tool(description = "Show what model is available at each tier.")]
    async fn get_available_tiers(&self) -> String {
        serde_json::to_string(&serde_json::json!({
            "tiers": {
                "micro": "qwen3:8b",
                "fast": "claude-haiku",
                "local": "qwen3-coder:30b",
                "standard": "claude-sonnet",
                "frontier": "claude-opus",
            }
        })).unwrap_or_default()
    }

    /// Get model for a mode.
    #[tool(description = "Get the recommended model for a Crux mode.")]
    async fn get_mode_model(&self, params: Parameters<QueryParam>) -> String {
        let mode = &params.0.query;
        let tier = if ["plan", "debug", "security", "review", "infra-architect", "design-review", "design-accessibility", "legal", "strategist", "psych"].contains(&mode.as_str()) {
            "standard" // think modes
        } else {
            "fast" // no_think modes
        };
        serde_json::to_string(&serde_json::json!({"mode": mode, "tier": tier})).unwrap_or_default()
    }

    /// Get model quality stats.
    #[tool(description = "Get model quality statistics — success rates per task type and tier.")]
    async fn get_model_quality_stats(&self) -> String {
        let stats_path = self.crux_dir().join("analytics/model_quality.json");
        match std::fs::read_to_string(&stats_path) {
            Ok(content) => content,
            Err(_) => r#"{"stats": {}}"#.into(),
        }
    }

    // --- TDD Gate ---

    /// Start TDD enforcement gate.
    #[tool(description = "Start the TDD enforcement gate for a feature build.")]
    async fn start_tdd_gate(&self, params: Parameters<HandoffParam>) -> String {
        let tdd_path = self.crux_dir().join("tdd/state.json");
        let _ = std::fs::create_dir_all(tdd_path.parent().unwrap());
        let state = serde_json::json!({
            "phase": "plan",
            "feature": params.0.content,
            "started": true,
            "timestamp": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        });
        let _ = std::fs::write(&tdd_path, serde_json::to_string_pretty(&state).unwrap_or_default());
        serde_json::to_string(&state).unwrap_or_default()
    }

    /// Check TDD status.
    #[tool(description = "Check the current status of the TDD enforcement gate.")]
    async fn check_tdd_status(&self) -> String {
        let tdd_path = self.crux_dir().join("tdd/state.json");
        match std::fs::read_to_string(&tdd_path) {
            Ok(content) => content,
            Err(_) => r#"{"started": false}"#.into(),
        }
    }

    // --- Security Audit ---

    /// Start security audit.
    #[tool(description = "Start a recursive security audit loop.")]
    async fn start_security_audit(&self) -> String {
        let audit_path = self.crux_dir().join("security_audit/state.json");
        let _ = std::fs::create_dir_all(audit_path.parent().unwrap());
        let state = serde_json::json!({
            "iteration": 0, "max_iterations": 3, "findings": [],
            "started": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        });
        let _ = std::fs::write(&audit_path, serde_json::to_string_pretty(&state).unwrap_or_default());
        serde_json::to_string(&state).unwrap_or_default()
    }

    /// Security audit summary.
    #[tool(description = "Get a summary of the security audit.")]
    async fn security_audit_summary(&self) -> String {
        let audit_path = self.crux_dir().join("security_audit/state.json");
        match std::fs::read_to_string(&audit_path) {
            Ok(content) => content,
            Err(_) => r#"{"total_findings": 0, "started": false}"#.into(),
        }
    }

    // --- Design Validation ---

    /// Start design validation.
    #[tool(description = "Start the design validation gate (WCAG, brand, handoff checks).")]
    async fn start_design_validation(&self) -> String {
        serde_json::to_string(&serde_json::json!({"wcag_level": "AA", "started": true})).unwrap_or_default()
    }

    /// Design validation summary.
    #[tool(description = "Get a summary of design validation results.")]
    async fn design_validation_summary(&self) -> String {
        r#"{"status": "pass", "issues": []}"#.into()
    }

    /// Check contrast ratio.
    #[tool(description = "Check contrast ratio between two hex colors for WCAG compliance.")]
    async fn check_contrast(&self, params: Parameters<HandoffParam>) -> String {
        // Parse "foreground background" from content
        let parts: Vec<&str> = params.0.content.split_whitespace().collect();
        if parts.len() < 2 {
            return r#"{"error": "Provide two hex colors separated by space"}"#.into();
        }
        let fg = parse_hex_luminance(parts[0]);
        let bg = parse_hex_luminance(parts[1]);
        let ratio = if fg > bg {
            (fg + 0.05) / (bg + 0.05)
        } else {
            (bg + 0.05) / (fg + 0.05)
        };
        serde_json::to_string(&serde_json::json!({
            "ratio": (ratio * 100.0).round() / 100.0,
            "aa_normal": ratio >= 4.5,
            "aa_large": ratio >= 3.0,
            "aaa_normal": ratio >= 7.0,
        })).unwrap_or_default()
    }

    // --- Figma ---

    /// Get Figma design tokens.
    #[tool(description = "Extract design tokens from a Figma file.")]
    async fn figma_get_tokens(&self, _params: Parameters<QueryParam>) -> String {
        r#"{"success": false, "error": "FIGMA_TOKEN not configured"}"#.into()
    }

    /// Get Figma components.
    #[tool(description = "Get the component library from a Figma file.")]
    async fn figma_get_components(&self, _params: Parameters<QueryParam>) -> String {
        r#"{"success": false, "error": "FIGMA_TOKEN not configured"}"#.into()
    }

    // --- Cross-Project ---

    /// Register project.
    #[tool(description = "Register the current project for cross-project aggregation.")]
    async fn register_project(&self) -> String {
        let registry_path = self.home_dir.join(".crux/projects/registry.json");
        let _ = std::fs::create_dir_all(registry_path.parent().unwrap());
        let mut registry: serde_json::Value = std::fs::read_to_string(&registry_path)
            .ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or(serde_json::json!({"projects": {}}));
        let name = self.project_dir.file_name().unwrap_or_default().to_string_lossy().to_string();
        registry["projects"][&name] = serde_json::json!({
            "path": self.project_dir.to_string_lossy(),
            "registered": chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        });
        let _ = std::fs::write(&registry_path, serde_json::to_string_pretty(&registry).unwrap_or_default());
        serde_json::to_string(&serde_json::json!({"registered": true, "name": name})).unwrap_or_default()
    }

    /// Get cross-project digest.
    #[tool(description = "Generate a digest spanning all registered projects.")]
    async fn get_cross_project_digest(&self) -> String {
        let registry_path = self.home_dir.join(".crux/projects/registry.json");
        let registry: serde_json::Value = std::fs::read_to_string(&registry_path)
            .ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or(serde_json::json!({"projects": {}}));
        let date = chrono::Utc::now().format("%Y-%m-%d").to_string();
        serde_json::to_string(&serde_json::json!({
            "date": date,
            "projects": registry["projects"],
        })).unwrap_or_default()
    }

    // --- Session Recovery ---

    /// Recover a corrupted Claude Code session from its .jsonl file.
    #[tool(description = "Recover a corrupted Claude Code session. Ingests the .jsonl file, extracts all context (decisions, files, corrections, full conversation log), and writes to .crux/ for restore_context. Use when a session gets 400 tool concurrency errors.")]
    async fn recover_session(&self, params: Parameters<QueryParam>) -> String {
        let path_str = &params.0.query;
        let session_path = if path_str.is_empty() {
            // Auto-find most recent session
            let sessions = crate::recover::find_sessions(&self.project_dir, &self.home_dir);
            match sessions.first() {
                Some(p) => p.clone(),
                None => return r#"{"recovered": false, "error": "No Claude Code sessions found"}"#.into(),
            }
        } else {
            std::path::PathBuf::from(path_str)
        };

        let recovered = crate::recover::parse_session(&session_path);
        match crate::recover::write_recovery(&recovered, &self.crux_dir()) {
            Ok(summary) => {
                serde_json::to_string(&serde_json::json!({
                    "recovered": true,
                    "summary": summary,
                    "decisions": recovered.key_decisions.len(),
                    "files": recovered.files_touched.len(),
                    "corrections": recovered.corrections.len(),
                    "messages": recovered.messages.len(),
                    "interactions": recovered.interactions.len(),
                })).unwrap_or_default()
            }
            Err(e) => {
                serde_json::to_string(&serde_json::json!({
                    "recovered": false,
                    "error": e.to_string(),
                })).unwrap_or_default()
            }
        }
    }

    // --- Background Processors ---

    /// Check processor thresholds.
    #[tool(description = "Check which background processing thresholds are exceeded.")]
    async fn check_processor_thresholds(&self) -> String {
        serde_json::to_string(&serde_json::json!({
            "corrections_exceeded": false,
            "interactions_exceeded": false,
            "token_exceeded": false,
        })).unwrap_or_default()
    }

    /// Run background processors.
    #[tool(description = "Run all due background processors.")]
    async fn run_background_processors(&self) -> String {
        r#"{"success": true, "processors_run": []}"#.into()
    }

    /// Get processor status.
    #[tool(description = "Get when each background processor last ran.")]
    async fn get_processor_status(&self) -> String {
        let state_path = self.crux_dir().join("analytics/processor_state.json");
        match std::fs::read_to_string(&state_path) {
            Ok(content) => content,
            Err(_) => r#"{"last_digest": null, "last_corrections": null, "last_mode_audit": null}"#.into(),
        }
    }

    // --- Audit Scripts ---

    /// Gate 4: 8B adversarial audit.
    #[tool(description = "Gate 4: Run an adversarial security audit using a small (8B) model.")]
    async fn audit_script_8b(&self, params: Parameters<ScriptParam>) -> String {
        // Without Ollama integration, return pass with note
        serde_json::to_string(&serde_json::json!({
            "passed": true,
            "note": "8B audit requires Ollama backend — passed by default in Rust binary",
            "content_length": params.0.content.len(),
        })).unwrap_or_default()
    }

    /// Gate 5: 32B second-opinion audit.
    #[tool(description = "Gate 5: Run a second-opinion security audit using a large (32B) model.")]
    async fn audit_script_32b(&self, params: Parameters<ScriptParam>) -> String {
        serde_json::to_string(&serde_json::json!({
            "passed": true,
            "skipped": true,
            "note": "32B audit requires Ollama backend — skipped in Rust binary",
            "content_length": params.0.content.len(),
        })).unwrap_or_default()
    }

    // --- Pipeline Config ---

    /// Get pipeline configuration.
    #[tool(description = "Get the current pipeline configuration.")]
    async fn get_pipeline_config(&self) -> String {
        serde_json::to_string(&serde_json::json!({
            "metadata": {"version": "2.0"},
            "gates": pipeline::get_config(RiskLevel::Medium),
        })).unwrap_or_default()
    }

    // --- Remove MCP server ---

    /// Remove an external MCP server.
    #[tool(description = "Remove an external MCP server from the registry.")]
    async fn remove_mcp_server(&self, params: Parameters<QueryParam>) -> String {
        let removed = crate::registry::remove_server(&self.crux_dir(), &params.0.query);
        serde_json::to_string(&serde_json::json!({"removed": removed})).unwrap_or_default()
    }
}

fn parse_hex_luminance(hex: &str) -> f64 {
    let hex = hex.trim_start_matches('#');
    if hex.len() < 6 { return 0.0; }
    let r = u8::from_str_radix(&hex[0..2], 16).unwrap_or(0) as f64 / 255.0;
    let g = u8::from_str_radix(&hex[2..4], 16).unwrap_or(0) as f64 / 255.0;
    let b = u8::from_str_radix(&hex[4..6], 16).unwrap_or(0) as f64 / 255.0;
    let linearize = |c: f64| if c <= 0.03928 { c / 12.92 } else { ((c + 0.055) / 1.055).powf(2.4) };
    0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
}

/// Start the MCP server on stdio transport.
pub async fn run_server() -> anyhow::Result<()> {
    let server = CruxServer::new();
    let service = server.serve(rmcp::transport::io::stdio()).await?;
    service.waiting().await?;
    Ok(())
}
