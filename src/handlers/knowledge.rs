//! Knowledge lookup and promotion — scope-based search.

use serde::Serialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Serialize)]
pub struct KnowledgeEntry {
    pub name: String,
    pub scope: String,
    pub preview: String,
    pub path: String,
}

/// Search knowledge entries across scopes: mode → project → user → shared.
pub fn lookup_knowledge(
    query: &str,
    mode: Option<&str>,
    project_dir: &Path,
    home: &Path,
) -> Vec<KnowledgeEntry> {
    let lower = query.to_lowercase();
    let mut results = Vec::new();

    // Search order: mode-specific → project → user → shared
    let search_dirs = build_search_dirs(mode, project_dir, home);

    for (scope, dir) in search_dirs {
        if !dir.exists() {
            continue;
        }
        if let Ok(entries) = fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if !path.is_file() {
                    continue;
                }
                let name = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
                if name.to_lowercase().contains(&lower) || file_contains(&path, &lower) {
                    let preview = read_preview(&path);
                    results.push(KnowledgeEntry {
                        name,
                        scope: scope.clone(),
                        preview,
                        path: path.to_string_lossy().to_string(),
                    });
                }
            }
        }
    }

    results
}

fn build_search_dirs(mode: Option<&str>, project_dir: &Path, home: &Path) -> Vec<(String, std::path::PathBuf)> {
    let mut dirs = Vec::new();

    if let Some(m) = mode {
        dirs.push(("mode".into(), project_dir.join(".crux/knowledge").join(m)));
    }
    dirs.push(("project".into(), project_dir.join(".crux/knowledge")));
    dirs.push(("user".into(), home.join(".crux/knowledge/shared")));

    dirs
}

fn file_contains(path: &Path, query: &str) -> bool {
    fs::read_to_string(path)
        .map(|content| content.to_lowercase().contains(query))
        .unwrap_or(false)
}

fn read_preview(path: &Path) -> String {
    fs::read_to_string(path)
        .map(|content| {
            content
                .lines()
                .filter(|l| !l.starts_with('#') && !l.starts_with("---") && !l.trim().is_empty())
                .take(2)
                .collect::<Vec<_>>()
                .join(" ")
                .chars()
                .take(150)
                .collect()
        })
        .unwrap_or_default()
}

/// Promote a knowledge entry from project scope to user scope.
pub fn promote_knowledge(entry_name: &str, project_dir: &Path, home: &Path) -> anyhow::Result<bool> {
    let src = project_dir.join(".crux/knowledge").join(format!("{entry_name}.md"));
    if !src.exists() {
        return Ok(false);
    }

    let dest_dir = home.join(".crux/knowledge/shared");
    fs::create_dir_all(&dest_dir)?;
    let dest = dest_dir.join(format!("{entry_name}.md"));
    fs::copy(&src, &dest)?;
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup() -> (TempDir, std::path::PathBuf, std::path::PathBuf) {
        let tmp = TempDir::new().unwrap();
        let home = tmp.path().join("home");
        let project = home.join("project");
        fs::create_dir_all(project.join(".crux/knowledge")).unwrap();
        fs::create_dir_all(home.join(".crux/knowledge/shared")).unwrap();
        (tmp, project, home)
    }

    #[test]
    fn finds_by_name() {
        let (_tmp, project, home) = setup();
        fs::write(
            project.join(".crux/knowledge/api-design.md"),
            "# API Design\nUse REST conventions.\nTags: api",
        ).unwrap();
        let results = lookup_knowledge("api", None, &project, &home);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "api-design");
    }

    #[test]
    fn finds_by_content() {
        let (_tmp, project, home) = setup();
        fs::write(
            project.join(".crux/knowledge/patterns.md"),
            "# Patterns\nAlways use PostgreSQL for persistence.",
        ).unwrap();
        let results = lookup_knowledge("postgresql", None, &project, &home);
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn no_match() {
        let (_tmp, project, home) = setup();
        fs::write(project.join(".crux/knowledge/test.md"), "unrelated content").unwrap();
        let results = lookup_knowledge("nonexistent", None, &project, &home);
        assert!(results.is_empty());
    }

    #[test]
    fn promote_works() {
        let (_tmp, project, home) = setup();
        fs::write(project.join(".crux/knowledge/patterns.md"), "content").unwrap();
        assert!(promote_knowledge("patterns", &project, &home).unwrap());
        assert!(home.join(".crux/knowledge/shared/patterns.md").exists());
    }

    #[test]
    fn promote_nonexistent() {
        let (_tmp, project, home) = setup();
        assert!(!promote_knowledge("nope", &project, &home).unwrap());
    }
}
