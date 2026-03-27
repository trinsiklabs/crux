//! Session state management — the bridge between tools.
//!
//! Stores session state in .crux/sessions/state.json so any tool
//! can pick up where another left off.

use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

use crate::security::atomic_write;

const MAX_HANDOFF_ITEMS: usize = 50;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SessionState {
    pub active_mode: String,
    pub active_tool: String,
    pub started_at: String,
    pub updated_at: String,
    pub working_on: String,
    #[serde(default)]
    pub key_decisions: Vec<String>,
    #[serde(default)]
    pub files_touched: Vec<String>,
    #[serde(default)]
    pub pending: Vec<String>,
    #[serde(default)]
    pub context_summary: String,
    #[serde(default)]
    pub session_ttl_hours: Option<u64>,
}

const DEFAULT_TTL_HOURS: u64 = 24;

impl SessionState {
    /// Check if this session state is stale (older than TTL).
    pub fn is_stale(&self) -> bool {
        if self.updated_at.is_empty() {
            return true;
        }
        let ttl = self.session_ttl_hours.unwrap_or(DEFAULT_TTL_HOURS);
        if let Ok(updated) = chrono::DateTime::parse_from_rfc3339(&self.updated_at) {
            let age = chrono::Utc::now().signed_duration_since(updated);
            age.num_hours() as u64 > ttl
        } else {
            // Try the non-RFC3339 format we use (YYYY-MM-DDTHH:MM:SSZ)
            if let Ok(updated) = chrono::NaiveDateTime::parse_from_str(&self.updated_at, "%Y-%m-%dT%H:%M:%SZ") {
                let age = chrono::Utc::now().naive_utc().signed_duration_since(updated);
                age.num_hours() as u64 > ttl
            } else {
                true // Can't parse = stale
            }
        }
    }

    pub fn new() -> Self {
        let now = now_iso();
        Self {
            active_mode: "build-py".into(),
            started_at: now.clone(),
            updated_at: now,
            ..Default::default()
        }
    }
}

fn now_iso() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

fn state_path(crux_dir: &Path) -> PathBuf {
    crux_dir.join("sessions").join("state.json")
}

fn handoff_path(crux_dir: &Path) -> PathBuf {
    crux_dir.join("sessions").join("handoff.md")
}

pub fn save_session(state: &SessionState, crux_dir: &Path) -> anyhow::Result<()> {
    let path = state_path(crux_dir);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let json = serde_json::to_string_pretty(state)?;
    atomic_write(&path, &json)
}

pub fn load_session(crux_dir: &Path) -> SessionState {
    let path = state_path(crux_dir);
    match fs::read_to_string(&path) {
        Ok(content) => serde_json::from_str(&content).unwrap_or_default(),
        Err(_) => SessionState::new(),
    }
}

pub fn update_session(
    crux_dir: &Path,
    working_on: Option<&str>,
    add_decision: Option<&str>,
    add_file: Option<&str>,
    add_pending: Option<&str>,
    active_tool: Option<&str>,
) -> SessionState {
    let mut state = load_session(crux_dir);
    state.updated_at = now_iso();

    if let Some(w) = working_on {
        state.working_on = w.to_string();
    }
    if let Some(d) = add_decision {
        state.key_decisions.push(d.to_string());
    }
    if let Some(f) = add_file {
        state.files_touched.push(f.to_string());
    }
    if let Some(p) = add_pending {
        state.pending.push(p.to_string());
    }
    if let Some(t) = active_tool {
        state.active_tool = t.to_string();
    }

    let _ = save_session(&state, crux_dir);
    state
}

pub fn auto_handoff(crux_dir: &Path) -> String {
    let state = load_session(crux_dir);
    let mut lines = vec!["# Session Handoff (auto-generated)".to_string(), String::new()];

    if !state.active_mode.is_empty() {
        lines.push(format!("**Mode:** {}", state.active_mode));
    }
    if !state.active_tool.is_empty() {
        lines.push(format!("**Tool:** {}", state.active_tool));
    }
    if !state.working_on.is_empty() {
        lines.push(format!("**Working on:** {}", state.working_on));
    }
    lines.push(String::new());

    // Filter garbage decisions
    let clean: Vec<&str> = state
        .key_decisions
        .iter()
        .filter(|d| !d.is_empty() && !d.starts_with("$(") && d.len() < 300)
        .map(|s| s.as_str())
        .collect();

    if !clean.is_empty() {
        lines.push("## Key Decisions".into());
        for d in clean.iter().rev().take(MAX_HANDOFF_ITEMS).rev() {
            lines.push(format!("- {d}"));
        }
        lines.push(String::new());
    }

    if !state.files_touched.is_empty() {
        lines.push("## Files Touched".into());
        for f in state.files_touched.iter().rev().take(MAX_HANDOFF_ITEMS).rev() {
            lines.push(format!("- {f}"));
        }
        lines.push(String::new());
    }

    if !state.pending.is_empty() {
        lines.push("## Pending Tasks".into());
        for p in &state.pending {
            lines.push(format!("- {p}"));
        }
        lines.push(String::new());
    }

    let content = lines.join("\n");
    let _ = write_handoff(crux_dir, &content);
    content
}

pub fn write_handoff(crux_dir: &Path, content: &str) -> anyhow::Result<()> {
    let path = handoff_path(crux_dir);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    atomic_write(&path, content)
}

pub fn read_handoff(crux_dir: &Path) -> Option<String> {
    fs::read_to_string(handoff_path(crux_dir)).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup() -> (TempDir, PathBuf) {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        fs::create_dir_all(crux.join("sessions")).unwrap();
        (tmp, crux)
    }

    #[test]
    fn new_session_has_timestamps() {
        let state = SessionState::new();
        assert!(!state.started_at.is_empty());
        assert!(!state.updated_at.is_empty());
        assert_eq!(state.active_mode, "build-py");
    }

    #[test]
    fn save_and_load_roundtrip() {
        let (_tmp, crux) = setup();
        let mut state = SessionState::new();
        state.working_on = "test task".into();
        state.key_decisions.push("use JWT".into());
        save_session(&state, &crux).unwrap();

        let loaded = load_session(&crux);
        assert_eq!(loaded.working_on, "test task");
        assert_eq!(loaded.key_decisions, vec!["use JWT"]);
    }

    #[test]
    fn load_nonexistent_returns_default() {
        let tmp = TempDir::new().unwrap();
        let state = load_session(tmp.path());
        assert_eq!(state.active_mode, "build-py");
    }

    #[test]
    fn update_session_adds_fields() {
        let (_tmp, crux) = setup();
        save_session(&SessionState::new(), &crux).unwrap();

        let state = update_session(
            &crux,
            Some("building auth"),
            Some("use bcrypt"),
            Some("auth.py"),
            None,
            Some("claude-code"),
        );

        assert_eq!(state.working_on, "building auth");
        assert!(state.key_decisions.contains(&"use bcrypt".to_string()));
        assert!(state.files_touched.contains(&"auth.py".to_string()));
        assert_eq!(state.active_tool, "claude-code");
    }

    #[test]
    fn auto_handoff_generates_content() {
        let (_tmp, crux) = setup();
        let mut state = SessionState::new();
        state.working_on = "auth refactor".into();
        state.key_decisions.push("use JWT".into());
        state.files_touched.push("auth.py".into());
        save_session(&state, &crux).unwrap();

        let content = auto_handoff(&crux);
        assert!(content.contains("auth refactor"));
        assert!(content.contains("JWT"));
        assert!(content.contains("auth.py"));
    }

    #[test]
    fn auto_handoff_filters_garbage() {
        let (_tmp, crux) = setup();
        let mut state = SessionState::new();
        state.key_decisions.push("good decision".into());
        state.key_decisions.push("$(cat <<'EOF'\ngarbage\nEOF\n)".into());
        state.key_decisions.push("x".repeat(500));
        save_session(&state, &crux).unwrap();

        let content = auto_handoff(&crux);
        assert!(content.contains("good decision"));
        assert!(!content.contains("$(cat"));
    }

    #[test]
    fn write_and_read_handoff() {
        let (_tmp, crux) = setup();
        write_handoff(&crux, "test handoff content").unwrap();
        let read = read_handoff(&crux);
        assert_eq!(read, Some("test handoff content".to_string()));
    }

    #[test]
    fn read_handoff_nonexistent() {
        let tmp = TempDir::new().unwrap();
        assert!(read_handoff(tmp.path()).is_none());
    }

    #[test]
    fn fresh_state_is_not_stale() {
        let state = SessionState::new();
        assert!(!state.is_stale());
    }

    #[test]
    fn old_state_is_stale() {
        let mut state = SessionState::new();
        state.updated_at = "2020-01-01T00:00:00Z".into();
        assert!(state.is_stale());
    }

    #[test]
    fn empty_updated_at_is_stale() {
        let mut state = SessionState::new();
        state.updated_at.clear();
        assert!(state.is_stale());
    }

    #[test]
    fn custom_ttl() {
        let mut state = SessionState::new();
        state.updated_at = "2020-01-01T00:00:00Z".into();
        state.session_ttl_hours = Some(1); // 1 hour TTL, state from 2020 = stale
        assert!(state.is_stale());
    }
}
