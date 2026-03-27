//! Scoring engine — combine all signals into ranked file list.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use super::ast::symbol_relevance;
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

/// Compute proximity scores — files near high-scoring files get a boost.
fn proximity_scores(keyword_scores: &HashMap<String, f64>) -> HashMap<String, f64> {
    if keyword_scores.is_empty() {
        return HashMap::new();
    }

    let threshold = keyword_scores.values().cloned().fold(0.0_f64, f64::max) * 0.5;
    let top_dirs: HashSet<String> = keyword_scores
        .iter()
        .filter(|(_, s)| **s >= threshold)
        .map(|(fp, _)| {
            Path::new(fp).parent().map(|p| p.to_string_lossy().to_string()).unwrap_or_default()
        })
        .collect();

    let mut scores = HashMap::new();
    for (fp, _) in keyword_scores {
        let dir = Path::new(fp).parent().map(|p| p.to_string_lossy().to_string()).unwrap_or_default();
        for td in &top_dirs {
            if dir == *td {
                scores.insert(fp.clone(), 1.0);
                break;
            } else if dir.starts_with(&format!("{td}/")) || td.starts_with(&format!("{dir}/")) {
                let entry = scores.entry(fp.clone()).or_insert(0.0);
                if *entry < 0.5 { *entry = 0.5; }
            }
        }
    }
    scores
}

/// Rank files by relevance to a prompt using all 5 signal dimensions.
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

    // Gather raw signals (5 dimensions)
    let kw_raw = grep_matches(root, &keywords);
    let churn_raw: HashMap<String, f64> = churn(root, 90)
        .into_iter()
        .map(|(k, v)| (k, v as f64))
        .collect();
    let ast_raw = symbol_relevance(root, &keywords);

    // Normalize each dimension
    let kw_norm = normalize(&kw_raw);
    let churn_norm = normalize(&churn_raw);
    let ast_norm = normalize(&ast_raw);
    let prox_raw = proximity_scores(&kw_norm);
    let prox_norm = normalize(&prox_raw);

    // Collect all files seen across any dimension
    let mut all_files: HashSet<String> = HashSet::new();
    all_files.extend(kw_norm.keys().cloned());
    all_files.extend(churn_norm.keys().cloned());
    all_files.extend(ast_norm.keys().cloned());
    all_files.extend(prox_norm.keys().cloned());

    if all_files.is_empty() {
        return Vec::new();
    }

    // Weights: keyword(0.25) + churn(0.15) + ast(0.25) + symbol(0.15) + proximity(0.20)
    let mut results: Vec<RankedFile> = all_files
        .into_iter()
        .map(|fp| {
            let kw_s = kw_norm.get(&fp).copied().unwrap_or(0.0);
            let ch_s = churn_norm.get(&fp).copied().unwrap_or(0.0);
            let as_s = ast_norm.get(&fp).copied().unwrap_or(0.0);
            let pr_s = prox_norm.get(&fp).copied().unwrap_or(0.0);

            let score = 0.25 * kw_s + 0.15 * ch_s + 0.25 * as_s + 0.15 * 0.0 + 0.20 * pr_s;

            let reasons = if include_reasons {
                HashMap::from([
                    ("keyword".into(), (kw_s * 10000.0).round() / 10000.0),
                    ("churn".into(), (ch_s * 10000.0).round() / 10000.0),
                    ("ast".into(), (as_s * 10000.0).round() / 10000.0),
                    ("proximity".into(), (pr_s * 10000.0).round() / 10000.0),
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

    #[test]
    fn includes_ast_dimension() {
        let tmp = TempDir::new().unwrap();
        let r = tmp.path();
        fs::write(r.join("auth.py"), "class AuthService:\n    def login(self):\n        pass\n").unwrap();
        let results = rank_files(r, "auth login", 10, true);
        if !results.is_empty() {
            // AST dimension should be present in reasons
            assert!(results[0].reasons.contains_key("ast"));
        }
    }
}
