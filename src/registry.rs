//! External MCP server registry — configure once, use everywhere.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub name: String,
    pub command: Vec<String>,
    #[serde(default)]
    pub env: std::collections::HashMap<String, String>,
    pub allowed_tools: Option<Vec<String>>,
    #[serde(default = "default_timeout")]
    pub timeout: u32,
    #[serde(default = "default_true")]
    pub enabled: bool,
}

fn default_timeout() -> u32 { 30 }
fn default_true() -> bool { true }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn serverconfig_roundtrip() {
        let cfg = ServerConfig {
            name: "github".into(),
            command: vec!["gh-mcp".into()],
            env: Default::default(),
            allowed_tools: None,
            timeout: 30,
            enabled: true,
        };
        let json = serde_json::to_string(&cfg).unwrap();
        let parsed: ServerConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.name, "github");
        assert_eq!(parsed.timeout, 30);
    }
}
