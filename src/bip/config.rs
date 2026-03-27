//! BIP configuration — Typefully account, triggers, voice rules.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

use super::BipState;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BipConfig {
    pub typefully: Option<TypefullyConfig>,
    pub triggers: TriggerConfig,
    pub voice: VoiceConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypefullyConfig {
    pub social_set_id: Option<u64>,
    pub api_key_path: String,
    pub account: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggerConfig {
    pub commit_threshold: u32,
    pub token_threshold: u32,
    pub interaction_threshold: u32,
    pub cooldown_minutes: u32,
    pub high_signal_events: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceConfig {
    pub style: String,
    pub tone: String,
    pub never: Vec<String>,
}

impl Default for BipConfig {
    fn default() -> Self {
        Self {
            typefully: None,
            triggers: TriggerConfig {
                commit_threshold: 4,
                token_threshold: 50000,
                interaction_threshold: 30,
                cooldown_minutes: 15,
                high_signal_events: vec![
                    "test_green".into(), "new_mcp_tool".into(), "git_tag".into(),
                    "pr_merge".into(), "crux_switch".into(), "crux_adopt".into(),
                ],
            },
            voice: VoiceConfig {
                style: "all lowercase except proper nouns".into(),
                tone: "technical, direct, no hype, builder energy".into(),
                never: vec!["Revolutionary".into(), "Game-changing".into(), "Excited to announce".into()],
            },
        }
    }
}

pub fn load_config(crux_dir: &Path) -> BipConfig {
    for subdir in &["bip", "marketing"] {
        let path = crux_dir.join(subdir).join("config.json");
        if let Ok(content) = fs::read_to_string(&path) {
            if let Ok(config) = serde_json::from_str(&content) {
                return config;
            }
        }
    }
    BipConfig::default()
}

pub fn load_state(crux_dir: &Path) -> BipState {
    for subdir in &["bip", "marketing"] {
        let path = crux_dir.join(subdir).join("state.json");
        if let Ok(content) = fs::read_to_string(&path) {
            if let Ok(state) = serde_json::from_str(&content) {
                return state;
            }
        }
    }
    BipState::default()
}

pub fn save_state(crux_dir: &Path, state: &BipState) {
    let path = crux_dir.join("bip/state.json");
    let _ = fs::create_dir_all(path.parent().unwrap());
    let _ = fs::write(&path, serde_json::to_string_pretty(state).unwrap_or_default());
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn default_config() {
        let config = BipConfig::default();
        assert_eq!(config.triggers.commit_threshold, 4);
        assert_eq!(config.triggers.cooldown_minutes, 15);
    }

    #[test]
    fn load_missing_returns_default() {
        let tmp = TempDir::new().unwrap();
        let config = load_config(tmp.path());
        assert_eq!(config.triggers.commit_threshold, 4);
    }

    #[test]
    fn save_and_load_state() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        fs::create_dir_all(crux.join("bip")).unwrap();
        let state = BipState { posts_today: 5, ..Default::default() };
        save_state(crux, &state);
        let loaded = load_state(crux);
        assert_eq!(loaded.posts_today, 5);
    }
}
