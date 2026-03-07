"""Tests for crux_adopt.py — mid-session adoption of Crux into an existing project."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.lib.crux_adopt import adopt_project, AdoptResult


@pytest.fixture
def project_with_git(tmp_path):
    """A project with git history simulating real usage."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()

    # Init a git repo with some history
    subprocess.run(["git", "init"], cwd=str(project), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(project), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(project), capture_output=True,
    )

    # Create files and commits
    (project / "src").mkdir()
    (project / "src" / "auth.py").write_text("# Auth module\nimport jwt\n")
    (project / "src" / "models.py").write_text("# Models\nfrom dataclasses import dataclass\n")
    subprocess.run(
        ["git", "add", "."], cwd=str(project), capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add auth module with JWT support"],
        cwd=str(project), capture_output=True,
    )

    (project / "src" / "cache.py").write_text("# Cache layer\nimport redis\n")
    (project / "tests").mkdir()
    (project / "tests" / "test_auth.py").write_text("def test_auth(): pass\n")
    subprocess.run(
        ["git", "add", "."], cwd=str(project), capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add Redis cache layer and auth tests"],
        cwd=str(project), capture_output=True,
    )

    # Add a CLAUDE.md
    (project / "CLAUDE.md").write_text(
        "# Project Notes\n\nThis is a FastAPI app.\nUse pytest for testing.\n"
    )
    subprocess.run(
        ["git", "add", "CLAUDE.md"], cwd=str(project), capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add CLAUDE.md"],
        cwd=str(project), capture_output=True,
    )

    return {"home": str(home), "project": str(project)}


@pytest.fixture
def project_no_git(tmp_path):
    """A project without git history."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (project / "main.py").write_text("print('hello')\n")
    return {"home": str(home), "project": str(project)}


# ---------------------------------------------------------------------------
# Core adoption
# ---------------------------------------------------------------------------

class TestAdoptProject:
    def test_returns_adopt_result(self, project_with_git):
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        assert isinstance(result, AdoptResult)
        assert result.success

    def test_initializes_crux_dirs(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        crux_dir = Path(project_with_git["project"]) / ".crux"
        assert crux_dir.is_dir()
        assert (crux_dir / "knowledge").is_dir()
        assert (crux_dir / "sessions").is_dir()
        assert (crux_dir / "corrections").is_dir()

        user_crux = Path(project_with_git["home"]) / ".crux"
        assert user_crux.is_dir()
        assert (user_crux / "modes").is_dir()

    def test_captures_git_files_touched(self, project_with_git):
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        assert "src/auth.py" in result.files_discovered
        assert "src/cache.py" in result.files_discovered

    def test_captures_git_commit_messages(self, project_with_git):
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        assert any("JWT" in d for d in result.decisions_discovered)

    def test_creates_session_state(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        state_file = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "state.json"
        )
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["active_tool"] == "claude-code"

    def test_imports_claude_md(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        imported = (
            Path(project_with_git["project"])
            / ".crux" / "context" / "CLAUDE.md.imported"
        )
        assert imported.exists()
        assert "FastAPI" in imported.read_text()

    def test_generates_project_md(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        project_md = (
            Path(project_with_git["project"]) / ".crux" / "context" / "PROJECT.md"
        )
        assert project_md.exists()
        content = project_md.read_text()
        assert "src/" in content or "auth.py" in content


# ---------------------------------------------------------------------------
# LLM-provided context
# ---------------------------------------------------------------------------

class TestAdoptWithContext:
    def test_working_on_persisted(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            working_on="Building OAuth2 flow with refresh tokens",
        )
        state_file = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "state.json"
        )
        data = json.loads(state_file.read_text())
        assert data["working_on"] == "Building OAuth2 flow with refresh tokens"

    def test_key_decisions_merged_with_git(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            key_decisions=["Use python-jose for JWT", "Redis for session cache"],
        )
        state_file = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "state.json"
        )
        data = json.loads(state_file.read_text())
        assert "Use python-jose for JWT" in data["key_decisions"]
        assert "Redis for session cache" in data["key_decisions"]

    def test_pending_tasks_saved(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            pending=["Add refresh token endpoint", "Write integration tests"],
        )
        state_file = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "state.json"
        )
        data = json.loads(state_file.read_text())
        assert "Add refresh token endpoint" in data["pending"]

    def test_context_summary_becomes_handoff(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            context_summary="Halfway through OAuth2. Auth module works but needs refresh tokens. Cache layer added for session storage. Tests passing but need integration tests.",
        )
        handoff = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "handoff.md"
        )
        assert handoff.exists()
        content = handoff.read_text()
        assert "OAuth2" in content
        assert "refresh tokens" in content

    def test_active_mode_override(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            active_mode="debug",
        )
        state_file = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "state.json"
        )
        data = json.loads(state_file.read_text())
        assert data["active_mode"] == "debug"

    def test_knowledge_entries_created(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            knowledge_entries={
                "auth-patterns": "# Auth Patterns\nUse JWT with httponly cookies.\nRotate refresh tokens on use.\nTags: auth, security",
                "testing-strategy": "# Testing Strategy\nUnit tests for business logic.\nIntegration tests for API endpoints.\nTags: testing",
            },
        )
        k_dir = Path(project_with_git["project"]) / ".crux" / "knowledge"
        assert (k_dir / "auth-patterns.md").exists()
        assert "httponly" in (k_dir / "auth-patterns.md").read_text()
        assert (k_dir / "testing-strategy.md").exists()


# ---------------------------------------------------------------------------
# MCP + hooks setup
# ---------------------------------------------------------------------------

class TestAdoptMCPSetup:
    def test_creates_mcp_json(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        mcp_json = Path(project_with_git["project"]) / ".claude" / "mcp.json"
        assert mcp_json.exists()
        data = json.loads(mcp_json.read_text())
        assert "crux" in data["mcpServers"]

    def test_mcp_json_has_absolute_python_path(self, project_with_git):
        from scripts.lib.crux_paths import get_crux_python
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        mcp_json = Path(project_with_git["project"]) / ".claude" / "mcp.json"
        data = json.loads(mcp_json.read_text())
        server = data["mcpServers"]["crux"]
        assert server["command"] == get_crux_python()
        assert os.path.isabs(server["command"])
        assert "-m" in server["args"]
        assert "scripts.lib.crux_mcp_server" in server["args"]

    def test_mcp_json_has_pythonpath(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        mcp_json = Path(project_with_git["project"]) / ".claude" / "mcp.json"
        data = json.loads(mcp_json.read_text())
        server = data["mcpServers"]["crux"]
        assert "PYTHONPATH" in server["env"]


class TestAdoptHooksSetup:
    def test_creates_settings_local_json(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        settings = Path(project_with_git["project"]) / ".claude" / "settings.local.json"
        assert settings.exists()

    def test_settings_has_all_hooks(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        settings = Path(project_with_git["project"]) / ".claude" / "settings.local.json"
        data = json.loads(settings.read_text())
        assert "hooks" in data
        for hook_name in ("SessionStart", "PostToolUse", "UserPromptSubmit", "Stop"):
            assert hook_name in data["hooks"], f"Missing hook: {hook_name}"

    def test_hooks_use_crux_hook_runner(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        settings = Path(project_with_git["project"]) / ".claude" / "settings.local.json"
        data = json.loads(settings.read_text())
        for hook_name, hook_list in data["hooks"].items():
            cmd = hook_list[0]["hooks"][0]["command"]
            assert "crux_hook_runner" in cmd
            assert hook_name in cmd

    def test_preserves_existing_settings(self, project_with_git):
        claude_dir = Path(project_with_git["project"]) / ".claude"
        claude_dir.mkdir(exist_ok=True)
        existing = {"permissions": {"allow": ["Bash(git:*)"]}}
        (claude_dir / "settings.local.json").write_text(json.dumps(existing))

        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        settings = Path(project_with_git["project"]) / ".claude" / "settings.local.json"
        data = json.loads(settings.read_text())
        assert data["permissions"]["allow"] == ["Bash(git:*)"]
        assert "hooks" in data

    def test_items_setup_mentions_hooks(self, project_with_git):
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        assert any("hooks" in item.lower() for item in result.items_setup)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestAdoptEdgeCases:
    def test_works_without_git(self, project_no_git):
        result = adopt_project(
            project_dir=project_no_git["project"],
            home=project_no_git["home"],
        )
        assert result.success
        assert result.files_discovered == []
        assert result.decisions_discovered == []

    def test_idempotent(self, project_with_git):
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            working_on="First run",
        )
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            working_on="Second run",
        )
        assert result.success
        state_file = (
            Path(project_with_git["project"]) / ".crux" / "sessions" / "state.json"
        )
        data = json.loads(state_file.read_text())
        assert data["working_on"] == "Second run"

    def test_does_not_overwrite_existing_knowledge(self, project_with_git):
        # Pre-create a knowledge entry
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        k_dir = Path(project_with_git["project"]) / ".crux" / "knowledge"
        (k_dir / "existing.md").write_text("# Existing\nDon't overwrite me.")

        # Re-adopt with same-named entry
        adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            knowledge_entries={"existing": "# Replaced"},
        )
        # Should NOT overwrite
        assert "Don't overwrite me" in (k_dir / "existing.md").read_text()

    def test_result_includes_summary(self, project_with_git):
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
            working_on="Test task",
            key_decisions=["Decision 1"],
        )
        assert len(result.items_setup) > 0
        assert any("session" in item.lower() for item in result.items_setup)

    def test_no_claude_md_is_fine(self, project_with_git):
        os.remove(os.path.join(project_with_git["project"], "CLAUDE.md"))
        result = adopt_project(
            project_dir=project_with_git["project"],
            home=project_with_git["home"],
        )
        assert result.success

    def test_deep_directory_capped(self, project_no_git):
        """Directories deeper than 3 levels are excluded from PROJECT.md."""
        deep = Path(project_no_git["project"]) / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("# deep")
        result = adopt_project(
            project_dir=project_no_git["project"],
            home=project_no_git["home"],
        )
        assert result.success
        project_md = (
            Path(project_no_git["project"]) / ".crux" / "context" / "PROJECT.md"
        )
        content = project_md.read_text()
        assert "deep.py" not in content

    def test_detects_python_tech_stack(self, project_no_git):
        (Path(project_no_git["project"]) / "pyproject.toml").write_text("[project]\n")
        result = adopt_project(
            project_dir=project_no_git["project"],
            home=project_no_git["home"],
        )
        assert result.success
        project_md = (
            Path(project_no_git["project"]) / ".crux" / "context" / "PROJECT.md"
        )
        assert "Python" in project_md.read_text()

    def test_detects_multiple_tech_stacks(self, project_no_git):
        p = Path(project_no_git["project"])
        (p / "package.json").write_text("{}")
        (p / "mix.exs").write_text("defmodule Mix do end")
        (p / "Cargo.toml").write_text("[package]")
        (p / "go.mod").write_text("module test")
        (p / "Dockerfile").write_text("FROM python")
        result = adopt_project(
            project_dir=project_no_git["project"],
            home=project_no_git["home"],
        )
        assert result.success
        content = (p / ".crux" / "context" / "PROJECT.md").read_text()
        assert "Node.js" in content
        assert "Elixir" in content
        assert "Rust" in content
        assert "Go" in content
        assert "Docker" in content

    def test_git_timeout_handled(self, project_no_git, monkeypatch):
        """If git commands timeout, adopt still succeeds."""
        import scripts.lib.crux_adopt as adopt_mod

        original_run = subprocess.run

        def slow_git(*args, **kwargs):
            if args and args[0] and args[0][0] == "git":
                raise subprocess.TimeoutExpired(cmd="git", timeout=10)
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", slow_git)
        result = adopt_project(
            project_dir=project_no_git["project"],
            home=project_no_git["home"],
        )
        assert result.success
        assert result.files_discovered == []
