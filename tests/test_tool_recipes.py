"""Tests for crux_tool_recipes — tool recipe engine for MCP config generation."""

import json
import os

import pytest

from scripts.lib.crux_tool_recipes import (
    ToolRecipe, RECIPES, get_recipe, generate_mcp_config,
)


class TestToolRecipe:
    def test_all_six_tools_have_recipes(self):
        expected = {"claude-code", "cruxcli", "opencode", "cursor", "windsurf", "zed"}
        assert set(RECIPES.keys()) == expected

    def test_recipe_fields(self):
        r = RECIPES["claude-code"]
        assert isinstance(r, ToolRecipe)
        assert r.tool_id == "claude-code"
        assert r.config_file
        assert r.root_key
        assert r.env_key

    def test_get_recipe_valid(self):
        r = get_recipe("claude-code")
        assert r.tool_id == "claude-code"

    def test_get_recipe_invalid(self):
        assert get_recipe("nonexistent") is None


class TestGenerateMcpConfig:
    @pytest.fixture
    def project(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        p = home / "project"
        p.mkdir()
        return str(p)

    def test_claude_code_format(self, project, tmp_path):
        generate_mcp_config("claude-code", project, "/repo", "/repo/.venv/bin/python")
        path = os.path.join(project, ".mcp.json")
        assert os.path.isfile(path)
        with open(path) as f:
            config = json.load(f)
        assert "mcpServers" in config
        assert "crux" in config["mcpServers"]
        entry = config["mcpServers"]["crux"]
        assert entry["type"] == "stdio"
        assert isinstance(entry["command"], str)
        assert isinstance(entry["args"], list)
        assert entry["env"]["CRUX_PROJECT"] == project

    def test_cruxcli_format(self, project, tmp_path):
        generate_mcp_config("cruxcli", project, "/repo", "/repo/.venv/bin/python")
        path = os.path.join(project, ".cruxcli", "cruxcli.jsonc")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        # Should be valid JSON (we write without comments)
        config = json.loads(content)
        assert "mcp" in config
        assert "crux" in config["mcp"]
        entry = config["mcp"]["crux"]
        assert entry["type"] == "local"
        assert isinstance(entry["command"], list)
        assert "environment" in entry

    def test_opencode_format(self, project, tmp_path):
        generate_mcp_config("opencode", project, "/repo", "/repo/.venv/bin/python")
        path = os.path.join(project, ".opencode", "opencode.jsonc")
        assert os.path.isfile(path)

    def test_cursor_format(self, project, tmp_path):
        generate_mcp_config("cursor", project, "/repo", "/repo/.venv/bin/python")
        path = os.path.join(project, ".cursor", "mcp.json")
        assert os.path.isfile(path)
        with open(path) as f:
            config = json.load(f)
        assert "mcpServers" in config
        entry = config["mcpServers"]["crux"]
        assert "type" not in entry  # Cursor has no type field

    def test_windsurf_global(self, project, tmp_path, monkeypatch):
        fake_home = str(tmp_path / "fakehome")
        os.makedirs(fake_home)
        monkeypatch.setenv("HOME", fake_home)
        generate_mcp_config("windsurf", project, "/repo", "/repo/.venv/bin/python")
        path = os.path.join(fake_home, ".codeium", "windsurf", "mcp_config.json")
        assert os.path.isfile(path)
        with open(path) as f:
            config = json.load(f)
        assert "mcpServers" in config

    def test_zed_global(self, project, tmp_path, monkeypatch):
        fake_home = str(tmp_path / "fakehome")
        os.makedirs(fake_home)
        monkeypatch.setenv("HOME", fake_home)
        generate_mcp_config("zed", project, "/repo", "/repo/.venv/bin/python")
        path = os.path.join(fake_home, ".config", "zed", "settings.json")
        assert os.path.isfile(path)
        with open(path) as f:
            config = json.load(f)
        assert "context_servers" in config

    def test_unknown_tool_returns_false(self, project):
        result = generate_mcp_config("nonexistent", project, "/repo", "/repo/.venv/bin/python")
        assert result is False

    def test_merges_existing_config(self, project, tmp_path):
        # Write an existing config with another server
        mcp_path = os.path.join(project, ".mcp.json")
        existing = {"mcpServers": {"other": {"command": "other-server"}}}
        with open(mcp_path, "w") as f:
            json.dump(existing, f)
        generate_mcp_config("claude-code", project, "/repo", "/repo/.venv/bin/python")
        with open(mcp_path) as f:
            config = json.load(f)
        assert "other" in config["mcpServers"]
        assert "crux" in config["mcpServers"]

    def test_corrupt_existing_config(self, project):
        mcp_path = os.path.join(project, ".mcp.json")
        with open(mcp_path, "w") as f:
            f.write("not valid json{{{")
        generate_mcp_config("claude-code", project, "/repo", "/repo/.venv/bin/python")
        with open(mcp_path) as f:
            config = json.load(f)
        assert "crux" in config["mcpServers"]

    def test_zed_merges_existing_settings(self, project, tmp_path, monkeypatch):
        fake_home = str(tmp_path / "fakehome")
        zed_dir = os.path.join(fake_home, ".config", "zed")
        os.makedirs(zed_dir)
        existing = {"theme": "dark", "font_size": 14}
        with open(os.path.join(zed_dir, "settings.json"), "w") as f:
            json.dump(existing, f)
        monkeypatch.setenv("HOME", fake_home)
        generate_mcp_config("zed", project, "/repo", "/repo/.venv/bin/python")
        with open(os.path.join(zed_dir, "settings.json")) as f:
            config = json.load(f)
        assert config["theme"] == "dark"
        assert "context_servers" in config
