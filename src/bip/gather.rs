//! BIP content gathering — collect material for a draft.

use std::fs;
use std::path::Path;
use std::process::Command;

pub struct GatheredContent {
    pub commits: Vec<String>,
    pub corrections: Vec<String>,
    pub knowledge: Vec<String>,
    pub working_on: String,
}

/// Gather content from git, corrections, knowledge, and session state.
pub fn gather(project_dir: &Path, crux_dir: &Path) -> GatheredContent {
    GatheredContent {
        commits: gather_git(project_dir),
        corrections: gather_corrections(crux_dir),
        knowledge: gather_knowledge(crux_dir),
        working_on: gather_working_on(crux_dir),
    }
}

fn gather_git(project_dir: &Path) -> Vec<String> {
    let output = Command::new("git")
        .args(["log", "--oneline", "-10"])
        .current_dir(project_dir)
        .output()
        .ok();

    match output {
        Some(o) if o.status.success() => {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .map(|l| l.to_string())
                .collect()
        }
        _ => Vec::new(),
    }
}

fn gather_corrections(crux_dir: &Path) -> Vec<String> {
    let path = crux_dir.join("corrections/corrections.jsonl");
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return Vec::new(),
    };

    content.lines()
        .rev()
        .take(5)
        .filter_map(|line| {
            serde_json::from_str::<serde_json::Value>(line).ok()
                .and_then(|v| v["content"].as_str().map(String::from))
        })
        .collect()
}

fn gather_knowledge(crux_dir: &Path) -> Vec<String> {
    let dir = crux_dir.join("knowledge");
    if !dir.exists() { return Vec::new(); }

    fs::read_dir(&dir)
        .ok()
        .map(|entries| {
            entries.filter_map(|e| e.ok())
                .filter(|e| e.path().extension().map_or(false, |ext| ext == "md"))
                .filter_map(|e| e.path().file_stem().map(|s| s.to_string_lossy().to_string()))
                .collect()
        })
        .unwrap_or_default()
}

fn gather_working_on(crux_dir: &Path) -> String {
    let path = crux_dir.join("sessions/state.json");
    fs::read_to_string(&path).ok()
        .and_then(|s| serde_json::from_str::<serde_json::Value>(&s).ok())
        .and_then(|v| v["working_on"].as_str().map(String::from))
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn gather_empty_dir() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        fs::create_dir_all(&crux).unwrap();
        let content = gather(tmp.path(), &crux);
        assert!(content.working_on.is_empty());
    }
}
