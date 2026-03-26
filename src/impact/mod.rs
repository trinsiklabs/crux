//! Impact analysis — file relevance ranking.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RankedFile {
    pub path: String,
    pub score: f64,
    pub reasons: HashMap<String, f64>,
}

pub const DEFAULT_WEIGHTS: &[(&str, f64)] = &[
    ("keyword", 0.25),
    ("churn", 0.15),
    ("ast", 0.25),
    ("symbol", 0.15),
    ("proximity", 0.20),
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn weights_sum_to_one() {
        let sum: f64 = DEFAULT_WEIGHTS.iter().map(|(_, w)| w).sum();
        assert!((sum - 1.0).abs() < 0.001);
    }

    #[test]
    fn ranked_file_serializes() {
        let rf = RankedFile {
            path: "auth.py".into(),
            score: 0.85,
            reasons: HashMap::from([("keyword".into(), 0.5), ("churn".into(), 0.35)]),
        };
        let json = serde_json::to_string(&rf).unwrap();
        assert!(json.contains("auth.py"));
    }
}
