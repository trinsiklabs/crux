//! Knowledge management — clustering, staleness, categories, promotion.

use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Cluster similar corrections by keyword overlap.
pub fn cluster_corrections(crux_dir: &Path) -> Vec<(String, Vec<String>)> {
    let path = crux_dir.join("corrections/corrections.jsonl");
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return Vec::new(),
    };

    let corrections: Vec<String> = content.lines()
        .filter_map(|line| {
            serde_json::from_str::<serde_json::Value>(line).ok()
                .and_then(|v| v["content"].as_str().map(String::from))
        })
        .collect();

    // Simple word-frequency clustering
    let mut word_groups: HashMap<String, Vec<String>> = HashMap::new();
    for correction in &corrections {
        let words: Vec<&str> = correction.split_whitespace()
            .filter(|w| w.len() > 3)
            .take(3)
            .collect();
        let key = words.join(" ").to_lowercase();
        if !key.is_empty() {
            word_groups.entry(key).or_default().push(correction.clone());
        }
    }

    // Return clusters with 2+ corrections
    word_groups.into_iter()
        .filter(|(_, v)| v.len() >= 2)
        .collect()
}

/// Check knowledge entries for staleness (not used in 30+ days).
pub fn check_staleness(crux_dir: &Path) -> Vec<String> {
    let knowledge_dir = crux_dir.join("knowledge");
    if !knowledge_dir.exists() { return Vec::new(); }

    let mut stale = Vec::new();
    if let Ok(entries) = fs::read_dir(&knowledge_dir) {
        for entry in entries.flatten() {
            if let Ok(metadata) = entry.metadata() {
                if let Ok(modified) = metadata.modified() {
                    let age = modified.elapsed().unwrap_or_default();
                    if age.as_secs() > 30 * 24 * 3600 {
                        stale.push(entry.file_name().to_string_lossy().to_string());
                    }
                }
            }
        }
    }
    stale
}

/// Knowledge categories.
pub const CATEGORIES: &[&str] = &[
    "architecture", "patterns", "conventions", "security",
    "testing", "performance", "dependencies", "deployment",
];

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn cluster_empty() {
        let tmp = TempDir::new().unwrap();
        assert!(cluster_corrections(tmp.path()).is_empty());
    }

    #[test]
    fn categories_exist() {
        assert!(CATEGORIES.contains(&"architecture"));
        assert!(CATEGORIES.contains(&"security"));
    }
}
