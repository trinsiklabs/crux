//! Project context generation — auto-generate PROJECT.md from repo structure.

use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::process::Command;

/// Generate a PROJECT.md from the repository structure.
pub fn generate_project_context(project_dir: &Path) -> String {
    let mut sections = vec!["# Project Context".to_string(), String::new()];

    // Project name
    let name = project_dir.file_name().unwrap_or_default().to_string_lossy();
    sections.push(format!("**Project:** {name}"));

    // Tech stack detection
    let stack = detect_tech_stack(project_dir);
    if !stack.is_empty() {
        sections.push(format!("**Stack:** {}", stack.join(", ")));
    }

    // Git info
    if let Some(branch) = git_branch(project_dir) {
        sections.push(format!("**Branch:** {branch}"));
    }
    if let Some(commits) = git_recent_commits(project_dir, 5) {
        sections.push(String::new());
        sections.push("## Recent Commits".into());
        for c in commits {
            sections.push(format!("- {c}"));
        }
    }

    // File structure (top-level)
    sections.push(String::new());
    sections.push("## Structure".into());
    if let Ok(entries) = fs::read_dir(project_dir) {
        let mut items: Vec<String> = entries
            .filter_map(|e| e.ok())
            .filter(|e| {
                let name = e.file_name().to_string_lossy().to_string();
                !name.starts_with('.') && name != "node_modules" && name != "target" && name != ".venv"
            })
            .map(|e| {
                let name = e.file_name().to_string_lossy().to_string();
                if e.path().is_dir() { format!("{name}/") } else { name }
            })
            .collect();
        items.sort();
        for item in &items {
            sections.push(format!("- {item}"));
        }
    }

    // Dependencies
    let deps = detect_dependencies(project_dir);
    if !deps.is_empty() {
        sections.push(String::new());
        sections.push("## Dependencies".into());
        for (category, items) in &deps {
            sections.push(format!("### {category}"));
            for item in items {
                sections.push(format!("- {item}"));
            }
        }
    }

    sections.join("\n")
}

/// Detected project type with recommended mode.
#[derive(Debug, Clone)]
pub struct ProjectType {
    pub language: String,
    pub mode: String,
    pub confidence: f64,
}

/// Detect project type and recommended mode.
pub fn detect_project_type(dir: &Path) -> Option<ProjectType> {
    let stack = detect_tech_stack(dir);
    let primary = stack.first()?;
    let (mode, confidence) = match primary.as_str() {
        "Rust" => ("build-py", 0.9),  // No build-rs mode yet, use build-py
        "Python" => ("build-py", 0.95),
        "Elixir" => ("build-ex", 0.95),
        "TypeScript" | "Node.js" => ("build-py", 0.7), // No build-ts mode yet
        "Go" => ("build-py", 0.6),
        "Ruby" => ("build-py", 0.6),
        _ => ("build-py", 0.5),
    };
    // Lower confidence if multiple stacks detected (ambiguous)
    let adj = if stack.len() > 1 { confidence * 0.8 } else { confidence };
    Some(ProjectType {
        language: primary.clone(),
        mode: mode.into(),
        confidence: adj,
    })
}

fn detect_tech_stack(dir: &Path) -> Vec<String> {
    let mut stack = Vec::new();
    if dir.join("Cargo.toml").exists() { stack.push("Rust".into()); }
    if dir.join("package.json").exists() { stack.push("Node.js".into()); }
    if dir.join("pyproject.toml").exists() || dir.join("setup.py").exists() { stack.push("Python".into()); }
    if dir.join("mix.exs").exists() { stack.push("Elixir".into()); }
    if dir.join("go.mod").exists() { stack.push("Go".into()); }
    if dir.join("Gemfile").exists() { stack.push("Ruby".into()); }
    if dir.join("tsconfig.json").exists() { stack.push("TypeScript".into()); }
    stack
}

fn detect_dependencies(dir: &Path) -> Vec<(String, Vec<String>)> {
    let mut deps = Vec::new();

    // Cargo.toml
    if let Ok(content) = fs::read_to_string(dir.join("Cargo.toml")) {
        let mut crate_deps = Vec::new();
        let mut in_deps = false;
        for line in content.lines() {
            if line.starts_with("[dependencies]") { in_deps = true; continue; }
            if line.starts_with('[') && in_deps { break; }
            if in_deps {
                if let Some(name) = line.split('=').next() {
                    let name = name.trim();
                    if !name.is_empty() && !name.starts_with('#') {
                        crate_deps.push(name.to_string());
                    }
                }
            }
        }
        if !crate_deps.is_empty() {
            deps.push(("Rust Crates".into(), crate_deps));
        }
    }

    deps
}

fn git_branch(dir: &Path) -> Option<String> {
    Command::new("git")
        .args(["branch", "--show-current"])
        .current_dir(dir)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .filter(|s| !s.is_empty())
}

fn git_recent_commits(dir: &Path, n: usize) -> Option<Vec<String>> {
    let output = Command::new("git")
        .args(["log", &format!("-{n}"), "--oneline"])
        .current_dir(dir)
        .output()
        .ok()?;
    if !output.status.success() { return None; }
    let commits: Vec<String> = String::from_utf8_lossy(&output.stdout)
        .lines()
        .map(|l| l.to_string())
        .collect();
    if commits.is_empty() { None } else { Some(commits) }
}

/// Write project context to .crux/context/PROJECT.md
pub fn write_project_context(project_dir: &Path, crux_dir: &Path) -> anyhow::Result<()> {
    let content = generate_project_context(project_dir);
    let path = crux_dir.join("context/PROJECT.md");
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&path, content)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn generates_context_for_rust_project() {
        let tmp = TempDir::new().unwrap();
        let dir = tmp.path();
        fs::write(dir.join("Cargo.toml"), "[package]\nname = \"test\"\n[dependencies]\nserde = \"1\"").unwrap();
        fs::create_dir(dir.join("src")).unwrap();
        fs::write(dir.join("src/main.rs"), "fn main() {}").unwrap();

        let context = generate_project_context(dir);
        assert!(context.contains("Rust"));
        assert!(context.contains("src/"));
    }

    #[test]
    fn detects_multiple_stacks() {
        let tmp = TempDir::new().unwrap();
        let dir = tmp.path();
        fs::write(dir.join("Cargo.toml"), "").unwrap();
        fs::write(dir.join("package.json"), "{}").unwrap();
        let stack = detect_tech_stack(dir);
        assert!(stack.contains(&"Rust".to_string()));
        assert!(stack.contains(&"Node.js".to_string()));
    }

    #[test]
    fn writes_project_md() {
        let tmp = TempDir::new().unwrap();
        let project = tmp.path().join("project");
        let crux = project.join(".crux");
        fs::create_dir_all(&crux.join("context")).unwrap();
        fs::create_dir_all(&project).unwrap();
        fs::write(project.join("Cargo.toml"), "[package]\nname = \"x\"").unwrap();

        write_project_context(&project, &crux).unwrap();
        assert!(crux.join("context/PROJECT.md").exists());
    }
}
