//! External MCP server registry — configure once, use everywhere.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Forbidden env keys — never forwarded to external servers.
const FORBIDDEN_ENV: &[&str] = &["CRUX_HOME", "CRUX_PROJECT", "PYTHONPATH", "HOME", "USER"];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub name: String,
    pub command: Vec<String>,
    #[serde(default)]
    pub env: HashMap<String, String>,
    pub allowed_tools: Option<Vec<String>>,
    #[serde(default = "default_timeout")]
    pub timeout: u32,
    #[serde(default = "default_true")]
    pub enabled: bool,
}

fn default_timeout() -> u32 { 30 }
fn default_true() -> bool { true }

fn registry_path(crux_dir: &Path) -> PathBuf {
    crux_dir.join("mcp-servers.json")
}

fn sanitize_env(env: &HashMap<String, String>) -> HashMap<String, String> {
    env.iter()
        .filter(|(k, _)| !FORBIDDEN_ENV.contains(&k.as_str()))
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect()
}

#[derive(Serialize, Deserialize, Default)]
struct Registry {
    #[serde(default)]
    servers: HashMap<String, ServerConfig>,
}

pub fn load_registry(crux_dir: &Path) -> HashMap<String, ServerConfig> {
    let path = registry_path(crux_dir);
    match fs::read_to_string(&path) {
        Ok(content) => serde_json::from_str::<Registry>(&content)
            .map(|r| r.servers)
            .unwrap_or_default(),
        Err(_) => HashMap::new(),
    }
}

pub fn save_registry(crux_dir: &Path, servers: &HashMap<String, ServerConfig>) -> anyhow::Result<()> {
    let path = registry_path(crux_dir);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let reg = Registry { servers: servers.clone() };
    fs::write(&path, serde_json::to_string_pretty(&reg)?)?;
    Ok(())
}

pub fn register_server(
    crux_dir: &Path,
    name: &str,
    command: Vec<String>,
    env: HashMap<String, String>,
    allowed_tools: Option<Vec<String>>,
    timeout: u32,
) -> anyhow::Result<()> {
    let mut servers = load_registry(crux_dir);
    servers.insert(name.into(), ServerConfig {
        name: name.into(),
        command,
        env: sanitize_env(&env),
        allowed_tools,
        timeout,
        enabled: true,
    });
    save_registry(crux_dir, &servers)
}

pub fn remove_server(crux_dir: &Path, name: &str) -> bool {
    let mut servers = load_registry(crux_dir);
    if servers.remove(name).is_some() {
        let _ = save_registry(crux_dir, &servers);
        true
    } else {
        false
    }
}

pub fn list_servers(crux_dir: &Path) -> Vec<ServerConfig> {
    load_registry(crux_dir).into_values().collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn register_and_load() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        register_server(crux, "test", vec!["test-mcp".into()], HashMap::new(), None, 30).unwrap();
        let loaded = load_registry(crux);
        assert!(loaded.contains_key("test"));
    }

    #[test]
    fn sanitizes_forbidden_env() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        let mut env = HashMap::new();
        env.insert("CRUX_HOME".into(), "/bad".into());
        env.insert("TOKEN".into(), "ok".into());
        register_server(crux, "test", vec!["cmd".into()], env, None, 30).unwrap();
        let loaded = load_registry(crux);
        assert!(!loaded["test"].env.contains_key("CRUX_HOME"));
        assert!(loaded["test"].env.contains_key("TOKEN"));
    }

    #[test]
    fn remove_existing() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path();
        register_server(crux, "test", vec!["cmd".into()], HashMap::new(), None, 30).unwrap();
        assert!(remove_server(crux, "test"));
        assert!(load_registry(crux).is_empty());
    }

    #[test]
    fn remove_nonexistent() {
        let tmp = TempDir::new().unwrap();
        assert!(!remove_server(tmp.path(), "nope"));
    }

    #[test]
    fn load_empty() {
        let tmp = TempDir::new().unwrap();
        assert!(load_registry(tmp.path()).is_empty());
    }
}
