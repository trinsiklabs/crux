//! Cross-session memory — persistent fact storage.

use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::Utc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: String,
    pub fact: String,
    pub source: String,
    pub confidence: f64,
    pub created_at: String,
    pub last_used: String,
    pub use_count: u32,
}

impl MemoryEntry {
    pub fn new(fact: &str, source: &str) -> Self {
        let now = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
        Self {
            id: Uuid::new_v4().to_string()[..12].to_string(),
            fact: fact.to_string(),
            source: source.to_string(),
            confidence: 1.0,
            created_at: now.clone(),
            last_used: now,
            use_count: 0,
        }
    }
}
