"""Tool recipe engine — centralized knowledge of MCP config formats per tool.

Each AI coding tool has its own config format for MCP servers. This module
stores the "recipe" for each tool and generates correct configs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class ToolRecipe:
    """Configuration recipe for an AI coding tool's MCP setup."""
    tool_id: str
    config_file: str        # Relative to project (or absolute for global)
    root_key: str           # Top-level key: mcpServers, mcp, context_servers
    type_value: str | None  # "stdio", "local", or None
    command_format: str     # "string_args" or "merged_array"
    env_key: str            # "env" or "environment"
    project_scoped: bool    # True = per-project config, False = global only
    launch_command: str     # How to start the tool


RECIPES: dict[str, ToolRecipe] = {
    "claude-code": ToolRecipe(
        tool_id="claude-code",
        config_file=".mcp.json",
        root_key="mcpServers",
        type_value="stdio",
        command_format="string_args",
        env_key="env",
        project_scoped=True,
        launch_command="claude",
    ),
    "cruxcli": ToolRecipe(
        tool_id="cruxcli",
        config_file=os.path.join(".cruxcli", "cruxcli.jsonc"),
        root_key="mcp",
        type_value="local",
        command_format="merged_array",
        env_key="environment",
        project_scoped=True,
        launch_command="cruxcli",
    ),
    "opencode": ToolRecipe(
        tool_id="opencode",
        config_file=os.path.join(".opencode", "opencode.jsonc"),
        root_key="mcp",
        type_value="local",
        command_format="merged_array",
        env_key="environment",
        project_scoped=True,
        launch_command="opencode",
    ),
    "cursor": ToolRecipe(
        tool_id="cursor",
        config_file=os.path.join(".cursor", "mcp.json"),
        root_key="mcpServers",
        type_value=None,
        command_format="string_args",
        env_key="env",
        project_scoped=True,
        launch_command="cursor .",
    ),
    "windsurf": ToolRecipe(
        tool_id="windsurf",
        config_file=os.path.join("~", ".codeium", "windsurf", "mcp_config.json"),
        root_key="mcpServers",
        type_value=None,
        command_format="string_args",
        env_key="env",
        project_scoped=False,
        launch_command="windsurf .",
    ),
    "zed": ToolRecipe(
        tool_id="zed",
        config_file=os.path.join("~", ".config", "zed", "settings.json"),
        root_key="context_servers",
        type_value=None,
        command_format="string_args",
        env_key="env",
        project_scoped=False,
        launch_command="zed .",
    ),
}


def get_recipe(tool_id: str) -> ToolRecipe | None:
    """Get the recipe for a tool, or None if unknown."""
    return RECIPES.get(tool_id)


def _resolve_config_path(recipe: ToolRecipe, project_dir: str) -> str:
    """Resolve the config file path for a recipe."""
    if recipe.project_scoped:
        return os.path.join(project_dir, recipe.config_file)
    return os.path.expanduser(recipe.config_file)


def _build_server_entry(
    recipe: ToolRecipe,
    crux_python: str,
    crux_repo: str,
    project_dir: str,
) -> dict:
    """Build the MCP server entry dict for a recipe."""
    entry: dict = {}

    if recipe.type_value is not None:
        entry["type"] = recipe.type_value

    if recipe.command_format == "merged_array":
        entry["command"] = [crux_python, "-m", "scripts.lib.crux_mcp_server"]
    else:
        entry["command"] = crux_python
        entry["args"] = ["-m", "scripts.lib.crux_mcp_server"]

    entry[recipe.env_key] = {
        "CRUX_PROJECT": project_dir,
        "CRUX_HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": crux_repo,
    }

    return entry


def generate_mcp_config(
    tool_id: str,
    project_dir: str,
    crux_repo: str,
    crux_python: str,
) -> bool:
    """Generate the MCP config for a tool. Returns True on success, False if unknown tool."""
    recipe = get_recipe(tool_id)
    if recipe is None:
        return False

    config_path = _resolve_config_path(recipe, project_dir)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Read existing config to merge
    existing: dict = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    # Build the crux server entry
    server_entry = _build_server_entry(recipe, crux_python, crux_repo, project_dir)

    # Merge into existing config
    if recipe.root_key not in existing:
        existing[recipe.root_key] = {}
    existing[recipe.root_key]["crux"] = server_entry

    with open(config_path, "w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")

    return True
