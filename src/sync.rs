//! Tool-specific config generation — write MCP configs for each AI tool.

use serde_json::json;
use std::fs;
use std::path::Path;

use crate::recipes::get_recipe;

/// Generate MCP config for a target tool.
pub fn generate_mcp_config(
    tool_id: &str,
    project_dir: &Path,
    crux_binary: &str,
) -> anyhow::Result<bool> {
    let recipe = match get_recipe(tool_id) {
        Some(r) => r,
        None => return Ok(false),
    };

    let config_path = if recipe.project_scoped {
        project_dir.join(&recipe.config_file)
    } else {
        let expanded = shellexpand::tilde(&recipe.config_file);
        std::path::PathBuf::from(expanded.as_ref())
    };

    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent)?;
    }

    // Read existing config to merge
    let mut existing: serde_json::Value = if config_path.exists() {
        fs::read_to_string(&config_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or(json!({}))
    } else {
        json!({})
    };

    // Build server entry
    let mut entry = json!({});

    if let Some(ref type_val) = recipe.type_value {
        entry["type"] = json!(type_val);
    }

    if recipe.command_format == "merged_array" {
        entry["command"] = json!([crux_binary, "mcp", "start"]);
    } else {
        entry["command"] = json!(crux_binary);
        entry["args"] = json!(["mcp", "start"]);
    }

    let env_key = &recipe.env_key;
    entry[env_key] = json!({
        "CRUX_PROJECT": project_dir.to_string_lossy(),
    });

    // Merge
    let root = existing.as_object_mut().unwrap();
    if !root.contains_key(&recipe.root_key) {
        root.insert(recipe.root_key.clone(), json!({}));
    }
    root[&recipe.root_key]["crux"] = entry;

    fs::write(&config_path, serde_json::to_string_pretty(&existing)?)?;
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn generates_claude_code_config() {
        let tmp = TempDir::new().unwrap();
        let project = tmp.path();
        generate_mcp_config("claude-code", project, "/usr/local/bin/crux").unwrap();
        let path = project.join(".mcp.json");
        assert!(path.exists());
        let content: serde_json::Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
        assert!(content["mcpServers"]["crux"]["type"].as_str() == Some("stdio"));
    }

    #[test]
    fn generates_cruxcli_config() {
        let tmp = TempDir::new().unwrap();
        let project = tmp.path();
        generate_mcp_config("cruxcli", project, "/usr/local/bin/crux").unwrap();
        let path = project.join(".cruxcli/cruxcli.jsonc");
        assert!(path.exists());
        let content: serde_json::Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
        assert!(content["mcp"]["crux"]["type"].as_str() == Some("local"));
        assert!(content["mcp"]["crux"]["command"].is_array());
    }

    #[test]
    fn generates_cursor_config() {
        let tmp = TempDir::new().unwrap();
        let project = tmp.path();
        generate_mcp_config("cursor", project, "/usr/local/bin/crux").unwrap();
        let path = project.join(".cursor/mcp.json");
        assert!(path.exists());
        let content: serde_json::Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
        // Cursor has no type field
        assert!(content["mcpServers"]["crux"].get("type").is_none());
    }

    #[test]
    fn unknown_tool_returns_false() {
        let tmp = TempDir::new().unwrap();
        assert!(!generate_mcp_config("nonexistent", tmp.path(), "crux").unwrap());
    }

    #[test]
    fn merges_existing_config() {
        let tmp = TempDir::new().unwrap();
        let project = tmp.path();
        let mcp_path = project.join(".mcp.json");
        fs::write(&mcp_path, r#"{"mcpServers":{"other":{"command":"other"}}}"#).unwrap();
        generate_mcp_config("claude-code", project, "crux").unwrap();
        let content: serde_json::Value = serde_json::from_str(&fs::read_to_string(&mcp_path).unwrap()).unwrap();
        assert!(content["mcpServers"]["other"].is_object());
        assert!(content["mcpServers"]["crux"].is_object());
    }
}
