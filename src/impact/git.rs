//! Git history signals — churn, recency, co-change.

use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

fn run_git(root: &Path, args: &[&str]) -> Option<String> {
    if !root.is_dir() {
        return None;
    }
    let output = Command::new("git")
        .args(args)
        .current_dir(root)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&output.stdout).to_string())
}

/// Count commits touching each file in the last N days.
pub fn churn(root: &Path, days: u32) -> HashMap<String, u32> {
    let since = if days > 0 {
        format!("--since={days} days ago")
    } else {
        "--since=0 seconds ago".into()
    };
    let out = match run_git(root, &["log", "--name-only", "--pretty=format:", &since]) {
        Some(s) => s,
        None => return HashMap::new(),
    };

    let mut counts: HashMap<String, u32> = HashMap::new();
    for line in out.lines() {
        let trimmed = line.trim();
        if !trimmed.is_empty() {
            *counts.entry(trimmed.into()).or_insert(0) += 1;
        }
    }
    counts
}

/// Score files 0-1 by recency (1 = most recently changed).
pub fn recency(root: &Path) -> HashMap<String, f64> {
    let out = match run_git(root, &["log", "--format=%ct", "--name-only", "--no-merges"]) {
        Some(s) => s,
        None => return HashMap::new(),
    };

    let mut timestamps: HashMap<String, i64> = HashMap::new();
    let mut current_ts: Option<i64> = None;

    for line in out.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(ts) = trimmed.parse::<i64>() {
            current_ts = Some(ts);
        } else if let Some(ts) = current_ts {
            timestamps.entry(trimmed.into()).or_insert(ts);
        }
    }

    if timestamps.is_empty() {
        return HashMap::new();
    }

    let now = chrono::Utc::now().timestamp();
    let max_age = timestamps.values().map(|ts| now - ts).max().unwrap_or(1).max(1);

    timestamps
        .into_iter()
        .map(|(fp, ts)| (fp, 1.0 - ((now - ts) as f64 / max_age as f64)))
        .collect()
}

/// Find files that change together with filepath.
pub fn cochange(root: &Path, filepath: &str, days: u32) -> Vec<String> {
    let since = if days > 0 {
        format!("--since={days} days ago")
    } else {
        "--since=0 seconds ago".into()
    };

    let commit_out = match run_git(root, &["log", "--format=%H", &since, "--", filepath]) {
        Some(s) if !s.trim().is_empty() => s,
        _ => return Vec::new(),
    };

    let commits: Vec<&str> = commit_out.lines().filter(|l| !l.trim().is_empty()).collect();
    if commits.is_empty() {
        return Vec::new();
    }

    let mut counts: HashMap<String, u32> = HashMap::new();
    for sha in commits {
        if let Some(files_out) = run_git(root, &["diff-tree", "--no-commit-id", "--name-only", "-r", sha.trim()]) {
            for f in files_out.lines() {
                let f = f.trim();
                if !f.is_empty() && f != filepath {
                    *counts.entry(f.into()).or_insert(0) += 1;
                }
            }
        }
    }

    let mut pairs: Vec<(String, u32)> = counts.into_iter().collect();
    pairs.sort_by(|a, b| b.1.cmp(&a.1));
    pairs.into_iter().map(|(f, _)| f).collect()
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

        let env: Vec<(&str, &str)> = vec![
            ("GIT_AUTHOR_NAME", "T"), ("GIT_AUTHOR_EMAIL", "t@t"),
            ("GIT_COMMITTER_NAME", "T"), ("GIT_COMMITTER_EMAIL", "t@t"),
        ];

        let run = |args: &[&str]| {
            Command::new(args[0])
                .args(&args[1..])
                .current_dir(&r)
                .envs(env.iter().copied())
                .output()
                .unwrap();
        };

        run(&["git", "init"]);
        run(&["git", "config", "user.name", "T"]);
        run(&["git", "config", "user.email", "t@t"]);

        fs::write(r.join("auth.py"), "# v1\n").unwrap();
        fs::write(r.join("db.py"), "# v1\n").unwrap();
        run(&["git", "add", "."]);
        run(&["git", "commit", "-m", "init"]);

        fs::write(r.join("auth.py"), "# v2\n").unwrap();
        fs::write(r.join("db.py"), "# v2\n").unwrap();
        run(&["git", "add", "."]);
        run(&["git", "commit", "-m", "update both"]);

        fs::write(r.join("auth.py"), "# v3\n").unwrap();
        run(&["git", "add", "."]);
        run(&["git", "commit", "-m", "update auth"]);

        (tmp, r)
    }

    #[test]
    fn churn_counts() {
        let (_tmp, r) = make_repo();
        let c = churn(&r, 90);
        assert_eq!(*c.get("auth.py").unwrap(), 3);
        assert_eq!(*c.get("db.py").unwrap(), 2);
    }

    #[test]
    fn recency_returns_values() {
        let (_tmp, r) = make_repo();
        let rec = recency(&r);
        assert!(rec.contains_key("auth.py"));
        // All values should be between 0 and 1
        for v in rec.values() {
            assert!(*v >= 0.0 && *v <= 1.0);
        }
    }

    #[test]
    fn cochange_finds_db() {
        let (_tmp, r) = make_repo();
        let co = cochange(&r, "auth.py", 90);
        assert!(co.contains(&"db.py".to_string()));
    }

    #[test]
    fn nonexistent_root() {
        assert!(churn(Path::new("/nonexistent"), 90).is_empty());
        assert!(recency(Path::new("/nonexistent")).is_empty());
        assert!(cochange(Path::new("/nonexistent"), "x", 90).is_empty());
    }
}
