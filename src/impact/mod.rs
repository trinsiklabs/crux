//! Impact analysis — file relevance ranking.

pub mod git;
pub mod keywords;
pub mod scorer;

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
}
