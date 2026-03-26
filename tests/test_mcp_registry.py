"""Tests for crux_mcp_registry — external MCP server registry and connection."""

import json
import os
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from scripts.lib.crux_mcp_registry import (
    ServerConfig,
    load_registry,
    save_registry,
    register_server,
    remove_server,
    list_servers,
)
from scripts.lib.crux_init import init_project


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = home / "project"
    project.mkdir()
    init_project(project_dir=str(project))
    crux_dir = str(project / ".crux")
    return {"project": str(project), "crux_dir": crux_dir}


class TestServerConfig:
    def test_fields(self):
        cfg = ServerConfig(
            name="github",
            command=["github-mcp-server"],
            env={"GITHUB_TOKEN": "xxx"},
        )
        assert cfg.name == "github"
        assert cfg.command == ["github-mcp-server"]
        assert cfg.env["GITHUB_TOKEN"] == "xxx"

    def test_defaults(self):
        cfg = ServerConfig(name="test", command=["test-server"])
        assert cfg.env == {}
        assert cfg.allowed_tools is None
        assert cfg.timeout == 30
        assert cfg.enabled is True


class TestRegistry:
    def test_load_empty(self, env):
        servers = load_registry(env["crux_dir"])
        assert servers == {}

    def test_save_and_load(self, env):
        cfg = ServerConfig(name="github", command=["gh-mcp"])
        save_registry(env["crux_dir"], {"github": cfg})
        loaded = load_registry(env["crux_dir"])
        assert "github" in loaded
        assert loaded["github"].command == ["gh-mcp"]

    def test_register_server(self, env):
        result = register_server(
            env["crux_dir"],
            name="postgres",
            command=["postgres-mcp"],
            env={"PG_URL": "postgresql://localhost/db"},
        )
        assert result["registered"] is True
        loaded = load_registry(env["crux_dir"])
        assert "postgres" in loaded

    def test_register_overwrites(self, env):
        register_server(env["crux_dir"], name="test", command=["v1"])
        register_server(env["crux_dir"], name="test", command=["v2"])
        loaded = load_registry(env["crux_dir"])
        assert loaded["test"].command == ["v2"]

    def test_remove_server(self, env):
        register_server(env["crux_dir"], name="test", command=["test"])
        result = remove_server(env["crux_dir"], "test")
        assert result["removed"] is True
        loaded = load_registry(env["crux_dir"])
        assert "test" not in loaded

    def test_remove_nonexistent(self, env):
        result = remove_server(env["crux_dir"], "nope")
        assert result["removed"] is False

    def test_list_servers(self, env):
        register_server(env["crux_dir"], name="a", command=["a"])
        register_server(env["crux_dir"], name="b", command=["b"])
        result = list_servers(env["crux_dir"])
        assert len(result["servers"]) == 2
        names = [s["name"] for s in result["servers"]]
        assert "a" in names
        assert "b" in names

    def test_list_empty(self, env):
        result = list_servers(env["crux_dir"])
        assert result["servers"] == []

    def test_allowed_tools_filter(self, env):
        register_server(
            env["crux_dir"],
            name="limited",
            command=["limited-mcp"],
            allowed_tools=["safe_tool_1", "safe_tool_2"],
        )
        loaded = load_registry(env["crux_dir"])
        assert loaded["limited"].allowed_tools == ["safe_tool_1", "safe_tool_2"]

    def test_timeout_custom(self, env):
        register_server(
            env["crux_dir"],
            name="slow",
            command=["slow-mcp"],
            timeout=60,
        )
        loaded = load_registry(env["crux_dir"])
        assert loaded["slow"].timeout == 60

    def test_non_dict_server_entry(self, env):
        path = os.path.join(env["crux_dir"], "mcp-servers.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"servers": {"bad": "not a dict", "good": {"command": ["test"]}}}, f)
        loaded = load_registry(env["crux_dir"])
        assert "bad" not in loaded
        assert "good" in loaded

    def test_corrupt_registry_file(self, env):
        path = os.path.join(env["crux_dir"], "mcp-servers.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("not json{{{")
        servers = load_registry(env["crux_dir"])
        assert servers == {}

    def test_no_credential_leakage(self, env):
        """Registry never stores CRUX_HOME or session paths in server env."""
        register_server(
            env["crux_dir"],
            name="test",
            command=["test"],
            env={"CRUX_HOME": "/should/not/store", "TOKEN": "ok"},
        )
        loaded = load_registry(env["crux_dir"])
        # CRUX_HOME should be stripped
        assert "CRUX_HOME" not in loaded["test"].env
        assert loaded["test"].env["TOKEN"] == "ok"
