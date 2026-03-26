//! Cross-session memory — persistent fact storage in JSONL.

use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: String,
    pub fact: String,
    pub source: String,
    pub confidence: f64,
    pub created_at: String,
    pub last_used: String,
    pub use_count: u32,
}

impl MemoryEntry {
    pub fn new(fact: &str, source: &str) -> Self {
        let now = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
        Self {
            id: Uuid::new_v4().to_string()[..12].to_string(),
            fact: fact.into(),
            source: source.into(),
            confidence: 1.0,
            created_at: now.clone(),
            last_used: now,
            use_count: 0,
        }
    }
}

fn memory_path(scope: &str, crux_dir: &Path) -> PathBuf {
    crux_dir.join("memory").join(scope).join("memories.jsonl")
}

pub fn save_memory(entry: &MemoryEntry, scope: &str, crux_dir: &Path) -> anyhow::Result<()> {
    let mut entries = load_memories(scope, crux_dir);

    // Deduplicate by fact text
    if let Some(existing) = entries.iter_mut().find(|e| e.fact.to_lowercase() == entry.fact.to_lowercase()) {
        existing.use_count += 1;
        existing.last_used = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
        existing.confidence = (existing.confidence + 0.1).min(2.0);
    } else {
        entries.push(entry.clone());
    }

    write_all(&entries, scope, crux_dir)
}

fn write_all(entries: &[MemoryEntry], scope: &str, crux_dir: &Path) -> anyhow::Result<()> {
    let path = memory_path(scope, crux_dir);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut content = String::new();
    for entry in entries {
        content.push_str(&serde_json::to_string(entry)?);
        content.push('\n');
    }
    fs::write(&path, content)?;
    Ok(())
}

pub fn load_memories(scope: &str, crux_dir: &Path) -> Vec<MemoryEntry> {
    let path = memory_path(scope, crux_dir);
    let file = match fs::File::open(&path) {
        Ok(f) => f,
        Err(_) => return Vec::new(),
    };
    let reader = BufReader::new(file);
    let mut entries = Vec::new();
    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(entry) = serde_json::from_str::<MemoryEntry>(trimmed) {
            entries.push(entry);
        }
    }
    entries
}

pub fn search_memories(query: &str, scope: &str, crux_dir: &Path) -> Vec<MemoryEntry> {
    if query.is_empty() {
        return Vec::new();
    }
    let lower = query.to_lowercase();
    load_memories(scope, crux_dir)
        .into_iter()
        .filter(|e| e.fact.to_lowercase().contains(&lower))
        .collect()
}

pub fn forget_memory(id: &str, scope: &str, crux_dir: &Path) -> bool {
    let mut entries = load_memories(scope, crux_dir);
    let before = entries.len();
    entries.retain(|e| e.id != id);
    if entries.len() < before {
        let _ = write_all(&entries, scope, crux_dir);
        true
    } else {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup() -> (TempDir, PathBuf) {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        fs::create_dir_all(crux.join("memory/project")).unwrap();
        (tmp, crux)
    }

    #[test]
    fn save_and_load() {
        let (_tmp, crux) = setup();
        let entry = MemoryEntry::new("uses pytest", "detection");
        save_memory(&entry, "project", &crux).unwrap();
        let loaded = load_memories("project", &crux);
        assert_eq!(loaded.len(), 1);
        assert_eq!(loaded[0].fact, "uses pytest");
    }

    #[test]
    fn deduplication() {
        let (_tmp, crux) = setup();
        save_memory(&MemoryEntry::new("uses pytest", "s"), "project", &crux).unwrap();
        save_memory(&MemoryEntry::new("uses pytest", "s"), "project", &crux).unwrap();
        let loaded = load_memories("project", &crux);
        assert_eq!(loaded.len(), 1);
        assert!(loaded[0].use_count >= 1);
    }

    #[test]
    fn search_finds_matching() {
        let (_tmp, crux) = setup();
        save_memory(&MemoryEntry::new("uses PostgreSQL", "s"), "project", &crux).unwrap();
        save_memory(&MemoryEntry::new("prefers dark mode", "s"), "project", &crux).unwrap();
        let results = search_memories("postgresql", "project", &crux);
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn search_empty_query() {
        let (_tmp, crux) = setup();
        save_memory(&MemoryEntry::new("fact", "s"), "project", &crux).unwrap();
        assert!(search_memories("", "project", &crux).is_empty());
    }

    #[test]
    fn forget_existing() {
        let (_tmp, crux) = setup();
        let entry = MemoryEntry::new("bad fact", "s");
        let id = entry.id.clone();
        save_memory(&entry, "project", &crux).unwrap();
        assert!(forget_memory(&id, "project", &crux));
        assert!(load_memories("project", &crux).is_empty());
    }

    #[test]
    fn forget_nonexistent() {
        let (_tmp, crux) = setup();
        assert!(!forget_memory("nope", "project", &crux));
    }

    #[test]
    fn load_empty() {
        let tmp = TempDir::new().unwrap();
        assert!(load_memories("project", tmp.path()).is_empty());
    }
}
