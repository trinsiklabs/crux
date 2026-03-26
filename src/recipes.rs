//! Tool recipe engine — MCP config formats per AI coding tool.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolRecipe {
    pub tool_id: String,
    pub config_file: String,
    pub root_key: String,
    pub type_value: Option<String>,
    pub command_format: String,     // "string_args" or "merged_array"
    pub env_key: String,            // "env" or "environment"
    pub project_scoped: bool,
    pub launch_command: String,
}

pub fn get_recipe(tool_id: &str) -> Option<ToolRecipe> {
    match tool_id {
        "claude-code" => Some(ToolRecipe {
            tool_id: "claude-code".into(),
            config_file: ".mcp.json".into(),
            root_key: "mcpServers".into(),
            type_value: Some("stdio".into()),
            command_format: "string_args".into(),
            env_key: "env".into(),
            project_scoped: true,
            launch_command: "claude".into(),
        }),
        "cruxcli" => Some(ToolRecipe {
            tool_id: "cruxcli".into(),
            config_file: ".cruxcli/cruxcli.jsonc".into(),
            root_key: "mcp".into(),
            type_value: Some("local".into()),
            command_format: "merged_array".into(),
            env_key: "environment".into(),
            project_scoped: true,
            launch_command: "cruxcli".into(),
        }),
        "opencode" => Some(ToolRecipe {
            tool_id: "opencode".into(),
            config_file: ".opencode/opencode.jsonc".into(),
            root_key: "mcp".into(),
            type_value: Some("local".into()),
            command_format: "merged_array".into(),
            env_key: "environment".into(),
            project_scoped: true,
            launch_command: "opencode".into(),
        }),
        "cursor" => Some(ToolRecipe {
            tool_id: "cursor".into(),
            config_file: ".cursor/mcp.json".into(),
            root_key: "mcpServers".into(),
            type_value: None,
            command_format: "string_args".into(),
            env_key: "env".into(),
            project_scoped: true,
            launch_command: "cursor .".into(),
        }),
        "windsurf" => Some(ToolRecipe {
            tool_id: "windsurf".into(),
            config_file: "~/.codeium/windsurf/mcp_config.json".into(),
            root_key: "mcpServers".into(),
            type_value: None,
            command_format: "string_args".into(),
            env_key: "env".into(),
            project_scoped: false,
            launch_command: "windsurf .".into(),
        }),
        "zed" => Some(ToolRecipe {
            tool_id: "zed".into(),
            config_file: "~/.config/zed/settings.json".into(),
            root_key: "context_servers".into(),
            type_value: None,
            command_format: "string_args".into(),
            env_key: "env".into(),
            project_scoped: false,
            launch_command: "zed .".into(),
        }),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_six_tools_have_recipes() {
        for id in &["claude-code", "cruxcli", "opencode", "cursor", "windsurf", "zed"] {
            assert!(get_recipe(id).is_some(), "Missing recipe for {id}");
        }
    }

    #[test]
    fn unknown_tool_returns_none() {
        assert!(get_recipe("nonexistent").is_none());
    }

    #[test]
    fn claude_code_is_stdio() {
        let r = get_recipe("claude-code").unwrap();
        assert_eq!(r.type_value, Some("stdio".into()));
        assert_eq!(r.root_key, "mcpServers");
    }

    #[test]
    fn cruxcli_is_local() {
        let r = get_recipe("cruxcli").unwrap();
        assert_eq!(r.type_value, Some("local".into()));
        assert_eq!(r.env_key, "environment");
        assert_eq!(r.command_format, "merged_array");
    }

    #[test]
    fn windsurf_is_global() {
        let r = get_recipe("windsurf").unwrap();
        assert!(!r.project_scoped);
    }
}
