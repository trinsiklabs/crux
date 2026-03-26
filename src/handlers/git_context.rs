//! Git-aware editing context — version history for better AI edits.

use serde::Serialize;
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

fn git(root: &Path, args: &[&str]) -> String {
    if !root.is_dir() {
        return String::new();
    }
    Command::new("git")
        .args(args)
        .current_dir(root)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
        .unwrap_or_default()
}

#[derive(Debug, Serialize)]
pub struct CommitInfo {
    pub hash: String,
    pub message: String,
    pub author: String,
    pub date: String,
}

pub fn current_diff(root: &Path) -> String {
    let staged = git(root, &["diff", "--cached"]);
    let unstaged = git(root, &["diff"]);
    format!("{staged}{unstaged}").trim().to_string()
}

pub fn file_history(root: &Path, filepath: &str, n: usize) -> Vec<CommitInfo> {
    let n_str = format!("-{n}");
    let out = git(root, &["log", &n_str, "--format=%H|%s|%an|%ci", "--", filepath]);
    out.lines()
        .filter_map(|line| {
            let parts: Vec<&str> = line.splitn(4, '|').collect();
            if parts.len() >= 4 {
                Some(CommitInfo {
                    hash: parts[0].into(),
                    message: parts[1].into(),
                    author: parts[2].into(),
                    date: parts[3].into(),
                })
            } else {
                None
            }
        })
        .collect()
}

pub fn branch_context(root: &Path) -> Option<(String, usize)> {
    let branch = git(root, &["branch", "--show-current"]);
    let branch = branch.trim();
    if branch.is_empty() {
        return None;
    }
    let count = git(root, &["log", "--oneline", "-20"])
        .lines()
        .count();
    Some((branch.into(), count))
}

pub fn suggest_commit(root: &Path) -> String {
    let stat = git(root, &["diff", "--cached", "--stat"]);
    if stat.trim().is_empty() {
        return String::new();
    }
    let files: Vec<&str> = stat
        .lines()
        .filter_map(|l| l.split('|').next().map(|s| s.trim()))
        .filter(|s| !s.is_empty() && !s.contains("changed"))
        .collect();

    match files.len() {
        0 => String::new(),
        1 => format!("Update {}", files[0]),
        n => format!("Update {} files: {}", n, files[..3.min(n)].join(", ")),
    }
}

pub fn risky_files(root: &Path, top_n: usize) -> Vec<(String, u32)> {
    let out = git(root, &["log", "--name-only", "--pretty=format:", "--since=90 days ago"]);
    let mut counts: HashMap<String, u32> = HashMap::new();
    for line in out.lines() {
        let trimmed = line.trim();
        if !trimmed.is_empty() {
            *counts.entry(trimmed.into()).or_insert(0) += 1;
        }
    }
    let mut pairs: Vec<(String, u32)> = counts.into_iter().collect();
    pairs.sort_by(|a, b| b.1.cmp(&a.1));
    pairs.truncate(top_n);
    pairs
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn make_repo() -> (TempDir, std::path::PathBuf) {
        let tmp = TempDir::new().unwrap();
        let r = tmp.path().join("repo");
        fs::create_dir_all(&r).unwrap();
        let env = [("GIT_AUTHOR_NAME", "T"), ("GIT_AUTHOR_EMAIL", "t@t"),
                    ("GIT_COMMITTER_NAME", "T"), ("GIT_COMMITTER_EMAIL", "t@t")];
        let run = |args: &[&str]| {
            Command::new(args[0]).args(&args[1..]).current_dir(&r)
                .envs(env.iter().copied()).output().unwrap();
        };
        run(&["git", "init"]);
        run(&["git", "config", "user.name", "T"]);
        run(&["git", "config", "user.email", "t@t"]);
        fs::write(r.join("auth.py"), "# v1\n").unwrap();
        run(&["git", "add", "."]);
        run(&["git", "commit", "-m", "init"]);
        fs::write(r.join("auth.py"), "# v2\n").unwrap();
        run(&["git", "add", "."]);
        run(&["git", "commit", "-m", "update auth"]);
        (tmp, r)
    }

    #[test]
    fn no_diff_when_clean() {
        let (_tmp, r) = make_repo();
        assert!(current_diff(&r).is_empty());
    }

    #[test]
    fn file_history_returns_commits() {
        let (_tmp, r) = make_repo();
        let history = file_history(&r, "auth.py", 10);
        assert!(history.len() >= 2);
        assert!(!history[0].message.is_empty());
    }

    #[test]
    fn branch_context_works() {
        let (_tmp, r) = make_repo();
        let (branch, count) = branch_context(&r).unwrap();
        assert!(!branch.is_empty());
        assert!(count > 0);
    }

    #[test]
    fn risky_files_returns_auth() {
        let (_tmp, r) = make_repo();
        let risky = risky_files(&r, 5);
        assert!(risky.iter().any(|(f, _)| f == "auth.py"));
    }
}
