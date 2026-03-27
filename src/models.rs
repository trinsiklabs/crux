//! Model quality tracking + tier system.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Model tier definitions.
pub const TIERS: &[(&str, &[&str])] = &[
    ("micro", &["qwen3:8b", "qwen3:4b"]),
    ("fast", &["claude-haiku", "gpt-5-nano", "qwen3.5:9b"]),
    ("local", &["qwen3-coder:30b", "qwen3.5:27b"]),
    ("standard", &["claude-sonnet", "gpt-5-mini"]),
    ("frontier", &["claude-opus", "gpt-5"]),
];

/// Task → tier routing table.
pub fn task_tier(task_type: &str) -> &'static str {
    match task_type {
        "title" | "compaction" => "micro",
        "plan_audit" | "doc_audit" | "e2e_test" => "fast",
        "write" | "code_audit" | "fix_generation" => "standard",
        "security_audit" | "independence" => "frontier",
        _ => "standard",
    }
}

/// Mode → tier routing.
pub fn mode_tier(mode: &str) -> &'static str {
    match mode {
        "plan" | "debug" | "security" | "review" | "infra-architect" |
        "design-review" | "design-accessibility" | "legal" | "strategist" | "psych" => "standard",
        _ => "fast",
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct QualityEntry {
    pub model: String,
    pub task_type: String,
    pub success: bool,
    pub latency_ms: u64,
    pub timestamp: String,
}

/// Record a quality outcome.
pub fn record_outcome(crux_dir: &Path, entry: &QualityEntry) {
    let path = crux_dir.join("analytics/model_quality.jsonl");
    let _ = fs::create_dir_all(path.parent().unwrap());
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(&path) {
        let _ = std::io::Write::write_all(&mut f,
            format!("{}\n", serde_json::to_string(entry).unwrap_or_default()).as_bytes()
        );
    }
}

/// Get quality stats — success rate per model per task type.
pub fn get_stats(crux_dir: &Path) -> HashMap<String, f64> {
    let path = crux_dir.join("analytics/model_quality.jsonl");
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return HashMap::new(),
    };

    let mut counts: HashMap<String, (u32, u32)> = HashMap::new(); // (success, total)
    for line in content.lines() {
        if let Ok(entry) = serde_json::from_str::<QualityEntry>(line) {
            let key = format!("{}:{}", entry.model, entry.task_type);
            let (success, total) = counts.entry(key).or_insert((0, 0));
            if entry.success { *success += 1; }
            *total += 1;
        }
    }

    counts.into_iter()
        .map(|(k, (s, t))| (k, s as f64 / t.max(1) as f64))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn task_tier_routing() {
        assert_eq!(task_tier("security_audit"), "frontier");
        assert_eq!(task_tier("title"), "micro");
        assert_eq!(task_tier("code_audit"), "standard");
    }

    #[test]
    fn mode_tier_routing() {
        assert_eq!(mode_tier("debug"), "standard");
        assert_eq!(mode_tier("build-py"), "fast");
    }
}
