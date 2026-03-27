//! Gate 2: TDD enforcement — test-first development tracking.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TddState {
    pub phase: String, // "plan", "red", "green", "complete"
    pub feature: String,
    pub components: Vec<String>,
    pub edge_cases: Vec<String>,
    pub coverage_target: f64,
    pub started: bool,
    pub timestamp: String,
}

impl Default for TddState {
    fn default() -> Self {
        Self {
            phase: "plan".into(),
            feature: String::new(),
            components: Vec::new(),
            edge_cases: Vec::new(),
            coverage_target: 100.0,
            started: false,
            timestamp: chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        }
    }
}

pub fn start(crux_dir: &Path, feature: &str, components: Vec<String>, edge_cases: Vec<String>) -> TddState {
    let state = TddState {
        phase: "plan".into(),
        feature: feature.into(),
        components,
        edge_cases,
        started: true,
        ..Default::default()
    };
    let path = crux_dir.join("tdd/state.json");
    let _ = fs::create_dir_all(path.parent().unwrap());
    let _ = fs::write(&path, serde_json::to_string_pretty(&state).unwrap_or_default());
    state
}

pub fn check_status(crux_dir: &Path) -> TddState {
    let path = crux_dir.join("tdd/state.json");
    match fs::read_to_string(&path) {
        Ok(content) => serde_json::from_str(&content).unwrap_or_default(),
        Err(_) => TddState::default(),
    }
}

pub fn advance_phase(crux_dir: &Path) -> TddState {
    let mut state = check_status(crux_dir);
    state.phase = match state.phase.as_str() {
        "plan" => "red".into(),
        "red" => "green".into(),
        "green" => "complete".into(),
        _ => state.phase,
    };
    let path = crux_dir.join("tdd/state.json");
    let _ = fs::write(&path, serde_json::to_string_pretty(&state).unwrap_or_default());
    state
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn start_creates_state() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        fs::create_dir_all(&crux).unwrap();
        let state = start(&crux, "login", vec!["AuthService".into()], vec!["expired token".into()]);
        assert_eq!(state.phase, "plan");
        assert!(state.started);
    }

    #[test]
    fn advance_through_phases() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        fs::create_dir_all(&crux).unwrap();
        start(&crux, "test", vec![], vec![]);

        let state = advance_phase(&crux);
        assert_eq!(state.phase, "red");
        let state = advance_phase(&crux);
        assert_eq!(state.phase, "green");
        let state = advance_phase(&crux);
        assert_eq!(state.phase, "complete");
    }
}
