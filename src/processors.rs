//! Background processors — threshold-triggered continuous learning.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProcessorState {
    pub last_digest: Option<String>,
    pub last_corrections: Option<String>,
    pub last_mode_audit: Option<String>,
}

/// Check which thresholds are exceeded.
pub fn check_thresholds(crux_dir: &Path) -> ThresholdResult {
    let corrections_count = count_lines(&crux_dir.join("corrections/corrections.jsonl"));
    let state = load_state(crux_dir);

    ThresholdResult {
        corrections_exceeded: corrections_count >= 10,
        interactions_exceeded: false, // Check analytics
        token_exceeded: false,
        corrections_count,
    }
}

#[derive(Debug, Serialize)]
pub struct ThresholdResult {
    pub corrections_exceeded: bool,
    pub interactions_exceeded: bool,
    pub token_exceeded: bool,
    pub corrections_count: usize,
}

/// Generate a daily digest from accumulated data.
pub fn generate_digest(crux_dir: &Path) -> String {
    let corrections_count = count_lines(&crux_dir.join("corrections/corrections.jsonl"));
    let knowledge_count = fs::read_dir(crux_dir.join("knowledge"))
        .map(|entries| entries.filter_map(|e| e.ok()).count())
        .unwrap_or(0);

    let date = chrono::Utc::now().format("%Y-%m-%d").to_string();

    let digest = format!(
        "# Daily Digest — {date}\n\n\
        ## Corrections\n- {corrections_count} corrections captured\n\n\
        ## Knowledge\n- {knowledge_count} knowledge entries\n\n"
    );

    // Save digest
    let digest_dir = crux_dir.join("analytics/digests");
    let _ = fs::create_dir_all(&digest_dir);
    let _ = fs::write(digest_dir.join(format!("{date}.md")), &digest);

    // Update processor state
    let mut state = load_state(crux_dir);
    state.last_digest = Some(chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string());
    save_state(crux_dir, &state);

    digest
}

pub fn load_state(crux_dir: &Path) -> ProcessorState {
    let path = crux_dir.join("analytics/processor_state.json");
    fs::read_to_string(&path).ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn save_state(crux_dir: &Path, state: &ProcessorState) {
    let path = crux_dir.join("analytics/processor_state.json");
    let _ = fs::create_dir_all(path.parent().unwrap());
    let _ = fs::write(&path, serde_json::to_string_pretty(state).unwrap_or_default());
}

fn count_lines(path: &Path) -> usize {
    fs::read_to_string(path)
        .map(|c| c.lines().filter(|l| !l.trim().is_empty()).count())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn check_thresholds_empty() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        fs::create_dir_all(crux.join("corrections")).unwrap();
        let result = check_thresholds(crux);
        assert!(!result.corrections_exceeded);
    }

    #[test]
    fn generate_digest_creates_file() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        fs::create_dir_all(crux.join("analytics/digests")).unwrap();
        fs::create_dir_all(crux.join("knowledge")).unwrap();
        fs::create_dir_all(crux.join("corrections")).unwrap();
        let digest = generate_digest(crux);
        assert!(digest.contains("Daily Digest"));
    }
}
