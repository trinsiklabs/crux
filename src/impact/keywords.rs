//! Keyword extraction and grep-based file matching.

use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::process::Command;
use walkdir::WalkDir;

const STOPWORDS: &[&str] = &[
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "and", "but", "or", "not", "so",
    "if", "when", "where", "how", "what", "which", "who", "this", "that", "it", "its",
    "add", "fix", "update", "remove", "delete", "change", "modify", "make",
    "get", "set", "use", "try", "check", "create", "build", "run",
];

/// Extract searchable keywords from a natural language prompt.
pub fn extract_keywords(prompt: &str) -> Vec<String> {
    if prompt.trim().is_empty() {
        return Vec::new();
    }

    let re = Regex::new(r"[A-Za-z0-9_]+").unwrap();
    let camel_split = Regex::new(r"([a-z0-9])([A-Z])").unwrap();

    let mut seen = std::collections::HashSet::new();
    let mut result = Vec::new();

    for token in re.find_iter(prompt) {
        let token = token.as_str();
        // Split on underscores
        for part in token.split('_') {
            // Split camelCase
            let expanded = camel_split.replace_all(part, "${1}_${2}");
            for sub in expanded.split('_') {
                let low = sub.to_lowercase();
                if low.len() > 1
                    && !STOPWORDS.contains(&low.as_str())
                    && seen.insert(low.clone())
                {
                    result.push(low);
                }
            }
        }
    }

    result
}

/// Find files matching keywords and score by match density.
pub fn grep_matches(root: &Path, keywords: &[String]) -> HashMap<String, f64> {
    if keywords.is_empty() || !root.is_dir() {
        return HashMap::new();
    }

    let skip = ["node_modules", ".git", ".venv", "__pycache__", "vendor", "dist", "build", "_site", "target"];
    let extensions = [
        "py", "js", "ts", "tsx", "jsx", "ex", "exs", "rs", "go",
        "md", "json", "yaml", "yml", "toml", "sh", "html", "css",
    ];

    let mut counts: HashMap<String, u32> = HashMap::new();

    for kw in keywords {
        let output = Command::new("grep")
            .args(&["-r", "-i", "-l"])
            .args(skip.iter().map(|d| format!("--exclude-dir={d}")))
            .args(extensions.iter().map(|e| format!("--include=*.{e}")))
            .arg(kw)
            .arg(root)
            .output();

        if let Ok(out) = output {
            if out.status.success() {
                for path in String::from_utf8_lossy(&out.stdout).lines() {
                    let trimmed = path.trim();
                    if !trimmed.is_empty() {
                        if let Ok(rel) = pathdiff(trimmed, root) {
                            *counts.entry(rel).or_insert(0) += 1;
                        }
                    }
                }
            }
        }
    }

    if counts.is_empty() {
        return HashMap::new();
    }

    // Calculate density
    let mut scores = HashMap::new();
    for (rel, count) in &counts {
        let full = root.join(rel);
        let lines = fs::read_to_string(&full)
            .map(|c| c.lines().count().max(1))
            .unwrap_or(1);
        scores.insert(rel.clone(), *count as f64 / lines as f64);
    }

    scores
}

fn pathdiff(abs: &str, base: &Path) -> anyhow::Result<String> {
    let abs = Path::new(abs);
    Ok(abs.strip_prefix(base)?.to_string_lossy().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn extract_splits_camel() {
        let kws = extract_keywords("fix AuthService bug");
        assert!(kws.contains(&"auth".to_string()));
        assert!(kws.contains(&"service".to_string()));
    }

    #[test]
    fn extract_splits_snake() {
        let kws = extract_keywords("update user_profile");
        assert!(kws.contains(&"user".to_string()));
        assert!(kws.contains(&"profile".to_string()));
    }

    #[test]
    fn extract_removes_stopwords() {
        let kws = extract_keywords("add the login to the system");
        assert!(!kws.contains(&"the".to_string()));
        assert!(!kws.contains(&"to".to_string()));
    }

    #[test]
    fn extract_empty() {
        assert!(extract_keywords("").is_empty());
    }

    #[test]
    fn grep_finds_files() {
        let tmp = TempDir::new().unwrap();
        let r = tmp.path();
        fs::write(r.join("auth.py"), "class AuthService:\n    pass\n").unwrap();
        fs::write(r.join("db.py"), "class Database:\n    pass\n").unwrap();
        let results = grep_matches(r, &["auth".into()]);
        assert!(results.contains_key("auth.py"));
    }

    #[test]
    fn grep_empty_keywords() {
        let tmp = TempDir::new().unwrap();
        assert!(grep_matches(tmp.path(), &[]).is_empty());
    }
}
