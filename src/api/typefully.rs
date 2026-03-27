//! Typefully REST API client — X/Twitter post scheduling.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

const API_BASE: &str = "https://api.typefully.com/v2";

#[derive(Debug, Serialize)]
struct DraftRequest {
    content: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    publish_at: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Draft {
    pub id: Option<u64>,
    pub status: Option<String>,
}

/// Load API key from .crux/bip/typefully.key or .crux/marketing/typefully.key
pub fn load_api_key(crux_dir: &Path) -> Option<String> {
    for subdir in &["bip", "marketing"] {
        let path = crux_dir.join(subdir).join("typefully.key");
        if let Ok(key) = fs::read_to_string(&path) {
            let key = key.trim().to_string();
            if !key.is_empty() {
                return Some(key);
            }
        }
    }
    None
}

/// Create a draft post.
pub fn create_draft(api_key: &str, content: &str, publish_at: Option<&str>) -> Result<Draft, String> {
    let client = reqwest::blocking::Client::new();
    let req = DraftRequest {
        content: content.into(),
        publish_at: publish_at.map(String::from),
    };

    match client.post(&format!("{API_BASE}/drafts"))
        .bearer_auth(api_key)
        .json(&req)
        .send()
    {
        Ok(resp) => {
            if resp.status().is_success() {
                resp.json::<Draft>().map_err(|e| e.to_string())
            } else {
                Err(format!("Typefully error: {}", resp.status()))
            }
        }
        Err(e) => Err(format!("Connection failed: {e}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn load_api_key_from_bip() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        let bip = crux.join("bip");
        fs::create_dir_all(&bip).unwrap();
        fs::write(bip.join("typefully.key"), "test-key-123").unwrap();
        assert_eq!(load_api_key(crux), Some("test-key-123".into()));
    }

    #[test]
    fn load_api_key_missing() {
        let tmp = TempDir::new().unwrap();
        assert_eq!(load_api_key(tmp.path()), None);
    }
}
