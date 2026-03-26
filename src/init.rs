//! Project and user initialization — create .crux/ directory structure.

use std::fs;
use std::path::Path;

const PROJECT_DIRS: &[&str] = &[
    "sessions",
    "sessions/history",
    "knowledge",
    "corrections",
    "scripts/session",
    "scripts/archive",
    "analytics/conversations",
    "analytics/interactions",
    "analytics/digests",
    "memory/project",
    "index",
    "context",
];

const USER_DIRS: &[&str] = &[
    "knowledge/shared",
    "modes",
    "corrections",
    "analytics",
    "projects",
    "memory/user",
];

pub fn init_project(project_dir: &Path) -> anyhow::Result<Vec<String>> {
    let crux = project_dir.join(".crux");
    let mut created = Vec::new();

    for dir in PROJECT_DIRS {
        let path = crux.join(dir);
        if !path.exists() {
            fs::create_dir_all(&path)?;
            created.push(dir.to_string());
        }
    }

    Ok(created)
}

pub fn init_user(home: &Path) -> anyhow::Result<Vec<String>> {
    let crux = home.join(".crux");
    let mut created = Vec::new();

    for dir in USER_DIRS {
        let path = crux.join(dir);
        if !path.exists() {
            fs::create_dir_all(&path)?;
            created.push(dir.to_string());
        }
    }

    Ok(created)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn init_project_creates_dirs() {
        let tmp = TempDir::new().unwrap();
        let created = init_project(tmp.path()).unwrap();
        assert!(!created.is_empty());
        assert!(tmp.path().join(".crux/sessions").exists());
        assert!(tmp.path().join(".crux/knowledge").exists());
        assert!(tmp.path().join(".crux/memory/project").exists());
    }

    #[test]
    fn init_project_idempotent() {
        let tmp = TempDir::new().unwrap();
        init_project(tmp.path()).unwrap();
        let created = init_project(tmp.path()).unwrap();
        assert!(created.is_empty()); // nothing new to create
    }

    #[test]
    fn init_user_creates_dirs() {
        let tmp = TempDir::new().unwrap();
        let created = init_user(tmp.path()).unwrap();
        assert!(!created.is_empty());
        assert!(tmp.path().join(".crux/modes").exists());
        assert!(tmp.path().join(".crux/memory/user").exists());
    }
}
