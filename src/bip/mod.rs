//! Build-in-Public pipeline — state, config, triggers, gathering, publishing.

pub mod config;
pub mod gather;
pub mod triggers;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BipState {
    pub last_queued_at: String,
    pub last_queued_id: Option<String>,
    pub commits_since_last_post: u32,
    pub tokens_since_last_post: u32,
    pub interactions_since_last_post: u32,
    pub posts_today: u32,
    pub posts_this_hour: u32,
}
