//! Scoring engine — combine signals into ranked file list.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use super::git::churn;
use super::keywords::{extract_keywords, grep_matches};
use super::RankedFile;

/// Normalize scores to 0-1 range.
fn normalize(scores: &HashMap<String, f64>) -> HashMap<String, f64> {
    if scores.is_empty() {
        return HashMap::new();
    }
    let mx = scores.values().cloned().fold(0.0_f64, f64::max);
    if mx == 0.0 {
        return scores.iter().map(|(k, _)| (k.clone(), 0.0)).collect();
    }
    scores.iter().map(|(k, v)| (k.clone(), v / mx)).collect()
}

/// Rank files by relevance to a prompt.
pub fn rank_files(
    root: &Path,
    prompt: &str,
    top_n: usize,
    include_reasons: bool,
) -> Vec<RankedFile> {
    if !root.is_dir() {
        return Vec::new();
    }

    let keywords = extract_keywords(prompt);
    if keywords.is_empty() {
        return Vec::new();
    }

    // Gather raw signals
    let kw_raw = grep_matches(root, &keywords);
    let churn_raw: HashMap<String, f64> = churn(root, 90)
        .into_iter()
        .map(|(k, v)| (k, v as f64))
        .collect();

    // Normalize
    let kw_norm = normalize(&kw_raw);
    let churn_norm = normalize(&churn_raw);

    // Collect all files
    let mut all_files: HashSet<String> = HashSet::new();
    all_files.extend(kw_norm.keys().cloned());
    all_files.extend(churn_norm.keys().cloned());

    if all_files.is_empty() {
        return Vec::new();
    }

    let mut results: Vec<RankedFile> = all_files
        .into_iter()
        .map(|fp| {
            let kw_s = kw_norm.get(&fp).copied().unwrap_or(0.0);
            let ch_s = churn_norm.get(&fp).copied().unwrap_or(0.0);

            let score = 0.5 * kw_s + 0.3 * ch_s;
            // Proximity boost: placeholder (would need os::walk)
            let reasons = if include_reasons {
                HashMap::from([
                    ("keyword".into(), (kw_s * 10000.0).round() / 10000.0),
                    ("churn".into(), (ch_s * 10000.0).round() / 10000.0),
                ])
            } else {
                HashMap::new()
            };

            RankedFile {
                path: fp,
                score: (score * 1000000.0).round() / 1000000.0,
                reasons,
            }
        })
        .collect();

    results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    results.truncate(top_n);
    results
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn rank_returns_sorted() {
        let tmp = TempDir::new().unwrap();
        let r = tmp.path();
        fs::write(r.join("auth.py"), "class AuthService:\n    pass\n").unwrap();
        fs::write(r.join("db.py"), "class Database:\n    pass\n").unwrap();

        let results = rank_files(r, "auth service", 10, true);
        if results.len() > 1 {
            assert!(results[0].score >= results[1].score);
        }
    }

    #[test]
    fn empty_prompt() {
        let tmp = TempDir::new().unwrap();
        assert!(rank_files(tmp.path(), "", 10, true).is_empty());
    }

    #[test]
    fn nonexistent_root() {
        assert!(rank_files(Path::new("/nonexistent"), "test", 10, true).is_empty());
    }

    #[test]
    fn normalize_empty() {
        assert!(normalize(&HashMap::new()).is_empty());
    }

    #[test]
    fn normalize_values() {
        let input = HashMap::from([("a".into(), 5.0), ("b".into(), 10.0)]);
        let norm = normalize(&input);
        assert!((norm["b"] - 1.0).abs() < 0.001);
        assert!((norm["a"] - 0.5).abs() < 0.001);
    }
}
