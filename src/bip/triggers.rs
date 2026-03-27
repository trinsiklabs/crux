//! BIP trigger evaluation — when to generate a post.

use super::config::{BipConfig, load_state};
use std::path::Path;

pub struct TriggerResult {
    pub should_trigger: bool,
    pub reason: String,
}

pub fn evaluate(crux_dir: &Path, config: &BipConfig) -> TriggerResult {
    let state = load_state(crux_dir);

    // Check cooldown
    if !state.last_queued_at.is_empty() {
        if let Ok(last) = chrono::DateTime::parse_from_rfc3339(&state.last_queued_at) {
            let elapsed = chrono::Utc::now().signed_duration_since(last);
            if elapsed.num_minutes() < config.triggers.cooldown_minutes as i64 {
                return TriggerResult {
                    should_trigger: false,
                    reason: format!("Cooldown: {} min remaining", config.triggers.cooldown_minutes as i64 - elapsed.num_minutes()),
                };
            }
        }
    }

    // Check commit threshold
    if state.commits_since_last_post >= config.triggers.commit_threshold {
        return TriggerResult {
            should_trigger: true,
            reason: format!("Commit threshold: {} commits (threshold: {})", state.commits_since_last_post, config.triggers.commit_threshold),
        };
    }

    // Check interaction threshold
    if state.interactions_since_last_post >= config.triggers.interaction_threshold {
        return TriggerResult {
            should_trigger: true,
            reason: format!("Interaction threshold: {} (threshold: {})", state.interactions_since_last_post, config.triggers.interaction_threshold),
        };
    }

    TriggerResult {
        should_trigger: false,
        reason: format!(
            "No threshold met: {} commits (need {}), {} interactions (need {})",
            state.commits_since_last_post, config.triggers.commit_threshold,
            state.interactions_since_last_post, config.triggers.interaction_threshold,
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    #[test]
    fn no_trigger_when_below_threshold() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        fs::create_dir_all(crux.join("bip")).unwrap();
        let config = BipConfig::default();
        let result = evaluate(crux, &config);
        assert!(!result.should_trigger);
    }
}
