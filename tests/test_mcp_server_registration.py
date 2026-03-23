"""Tests for crux_mcp_server.py — MCP tool registration, env helpers, and tool wrappers."""

import os
from pathlib import Path

import pytest

from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_session import SessionState, save_session


@pytest.fixture
def server_module(monkeypatch):
    """Import the server module with controlled environment."""
    monkeypatch.setenv("CRUX_HOME", "/tmp/test-home")
    monkeypatch.setenv("CRUX_PROJECT", "/tmp/test-project")
    from scripts.lib import crux_mcp_server
    return crux_mcp_server


@pytest.fixture
def live_env(tmp_path, monkeypatch):
    """Full Crux environment wired to the MCP server env vars."""
    home = tmp_path / "home"
    home.mkdir()
    project = home / "project"
    project.mkdir()

    init_user(home=str(home))
    init_project(project_dir=str(project))

    # Mode definitions
    modes_dir = home / ".crux" / "modes"
    (modes_dir / "build-py.md").write_text("You are a Python specialist.")
    (modes_dir / "debug.md").write_text("You are a debugging specialist.")

    # Knowledge
    pk = project / ".crux" / "knowledge"
    (pk / "api-design.md").write_text("# API Design\nUse REST conventions.\nTags: api")

    # Session
    crux_dir = str(project / ".crux")
    state = SessionState(
        active_mode="build-py",
        active_tool="claude-code",
        working_on="Building API",
    )
    save_session(state, project_crux_dir=crux_dir)

    monkeypatch.setenv("CRUX_HOME", str(home))
    monkeypatch.setenv("CRUX_PROJECT", str(project))

    from scripts.lib import crux_mcp_server
    return {
        "home": str(home),
        "project": str(project),
        "mod": crux_mcp_server,
    }


class TestEnvironmentHelpers:
    def test_home_uses_crux_home_env(self, monkeypatch):
        monkeypatch.setenv("CRUX_HOME", "/custom/home")
        from scripts.lib.crux_mcp_server import _home
        assert _home() == "/custom/home"

    def test_home_falls_back_to_HOME(self, monkeypatch):
        monkeypatch.delenv("CRUX_HOME", raising=False)
        monkeypatch.setenv("HOME", "/fallback/home")
        from scripts.lib.crux_mcp_server import _home
        assert _home() == "/fallback/home"

    def test_project_uses_crux_project_env(self, monkeypatch):
        monkeypatch.setenv("CRUX_PROJECT", "/custom/project")
        from scripts.lib.crux_mcp_server import _project
        assert _project() == "/custom/project"

    def test_project_falls_back_to_cwd(self, monkeypatch):
        monkeypatch.delenv("CRUX_PROJECT", raising=False)
        from scripts.lib.crux_mcp_server import _project
        assert _project() == os.getcwd()


class TestMCPToolRegistration:
    def test_mcp_server_created(self, server_module):
        assert server_module.mcp is not None
        assert server_module.mcp.name == "crux"

    def test_all_tools_registered(self, server_module):
        """All handler functions should be registered as MCP tools."""
        tools = server_module.mcp._tool_manager._tools
        expected = {
            "lookup_knowledge",
            "get_session_state",
            "update_session",
            "write_handoff",
            "read_handoff",
            "get_digest",
            "get_mode_prompt",
            "list_modes",
            "validate_script",
            "promote_knowledge",
            "get_project_context",
            "switch_tool_to",
            "log_correction",
            "log_interaction",
            "get_pipeline_config",
            "get_active_gates",
            "start_tdd_gate",
            "check_tdd_status",
            "start_security_audit",
            "security_audit_summary",
            "start_design_validation",
            "design_validation_summary",
            "check_contrast",
            "restore_context",
            "verify_health",
            "audit_script_8b",
            "audit_script_32b",
            "check_processor_thresholds",
            "run_background_processors",
            "get_processor_status",
            "register_project",
            "get_cross_project_digest",
            "figma_get_tokens",
            "figma_get_components",
            "analyze_impact",
        }
        registered = set(tools.keys())
        assert expected.issubset(registered), f"Missing tools: {expected - registered}"

    def test_tool_count(self, server_module):
        tools = server_module.mcp._tool_manager._tools
        assert len(tools) >= 34


class TestRunFunction:
    def test_run_is_async(self, server_module):
        import inspect
        assert inspect.iscoroutinefunction(server_module.run)


class TestToolWrappers:
    """Call the MCP tool wrapper functions directly to verify they delegate correctly."""

    def test_lookup_knowledge(self, live_env):
        result = live_env["mod"].lookup_knowledge(query="api")
        assert result["total_found"] > 0

    def test_get_session_state(self, live_env):
        result = live_env["mod"].get_session_state()
        assert result["active_mode"] == "build-py"

    def test_update_session(self, live_env):
        result = live_env["mod"].update_session(working_on="New task")
        assert result["working_on"] == "New task"

    def test_write_and_read_handoff(self, live_env):
        live_env["mod"].write_handoff(content="Test handoff")
        result = live_env["mod"].read_handoff()
        assert result["exists"]
        assert "Test handoff" in result["content"]

    def test_get_digest(self, live_env):
        result = live_env["mod"].get_digest()
        assert not result["found"]

    def test_get_mode_prompt(self, live_env):
        result = live_env["mod"].get_mode_prompt(mode="build-py")
        assert result["found"]

    def test_list_modes(self, live_env):
        result = live_env["mod"].list_modes()
        assert len(result["modes"]) >= 2

    def test_validate_script(self, live_env):
        result = live_env["mod"].validate_script(content="echo hello")
        assert not result["passed"]

    def test_promote_knowledge(self, live_env):
        result = live_env["mod"].promote_knowledge(entry_name="api-design")
        assert result["promoted"]

    def test_get_project_context(self, live_env):
        result = live_env["mod"].get_project_context()
        assert not result["found"]

    def test_switch_tool_to(self, live_env):
        result = live_env["mod"].switch_tool_to(target_tool="opencode")
        assert result["success"]

    def test_log_correction(self, live_env):
        result = live_env["mod"].log_correction(
            original="bad", corrected="good", category="style", mode="build-py"
        )
        assert result["logged"]

    def test_get_pipeline_config(self, live_env):
        result = live_env["mod"].get_pipeline_config()
        assert "metadata" in result
        assert result["metadata"]["version"] == "2.0"

    def test_get_active_gates(self, live_env):
        result = live_env["mod"].get_active_gates(mode="build-py", risk_level="high")
        assert 1 in result["active_gates"]
        assert 2 in result["active_gates"]

    def test_start_tdd_gate(self, live_env):
        result = live_env["mod"].start_tdd_gate(
            mode="build-py", feature="login",
            components=["AuthService"], edge_cases=["expired token"],
        )
        assert result["mode"] == "build-py"

    def test_check_tdd_status(self, live_env):
        result = live_env["mod"].check_tdd_status()
        assert "started" in result

    def test_start_security_audit(self, live_env):
        result = live_env["mod"].start_security_audit()
        assert result["max_iterations"] == 3

    def test_security_audit_summary(self, live_env):
        live_env["mod"].start_security_audit()
        result = live_env["mod"].security_audit_summary()
        assert result["total_findings"] == 0

    def test_start_design_validation(self, live_env):
        result = live_env["mod"].start_design_validation()
        assert result["wcag_level"] == "AA"

    def test_design_validation_summary(self, live_env):
        live_env["mod"].start_design_validation()
        result = live_env["mod"].design_validation_summary()
        assert result["status"] == "pass"

    def test_check_contrast(self, live_env):
        result = live_env["mod"].check_contrast(foreground="#000", background="#FFF")
        assert result["ratio"] == 21.0

    def test_restore_context(self, live_env):
        result = live_env["mod"].restore_context()
        assert "context" in result
        assert "build-py" in result["context"]
        assert "Building API" in result["context"]

    def test_log_interaction_user_message(self, live_env):
        result = live_env["mod"].log_interaction(
            role="user", content="test message from OpenCode"
        )
        assert result["logged"]

    def test_log_interaction_assistant_message(self, live_env):
        result = live_env["mod"].log_interaction(
            role="assistant", content="Here's the implementation..."
        )
        assert result["logged"]

    def test_verify_health(self, live_env):
        result = live_env["mod"].verify_health()
        assert "static" in result
        assert "liveness" in result
        assert "summary" in result
        assert isinstance(result["summary"]["total"], int)
        assert result["summary"]["total"] > 0

    def test_audit_script_8b(self, live_env):
        result = live_env["mod"].audit_script_8b(script_content="echo hello", risk_level="low")
        assert "passed" in result

    def test_audit_script_32b_skips_low(self, live_env):
        result = live_env["mod"].audit_script_32b(script_content="echo hello", risk_level="low")
        assert result["passed"] is True
        assert result.get("skipped") is True

    def test_check_processor_thresholds(self, live_env):
        result = live_env["mod"].check_processor_thresholds()
        assert "corrections_exceeded" in result

    def test_run_background_processors(self, live_env):
        result = live_env["mod"].run_background_processors()
        assert result["success"] is True

    def test_get_processor_status(self, live_env):
        result = live_env["mod"].get_processor_status()
        assert "last_digest" in result

    def test_register_project(self, live_env):
        result = live_env["mod"].register_project()
        assert result["registered"] is True

    def test_get_cross_project_digest(self, live_env):
        result = live_env["mod"].get_cross_project_digest()
        assert "date" in result

    def test_figma_get_tokens_error(self, live_env):
        result = live_env["mod"].figma_get_tokens(file_key="fake", token="fake")
        assert result["success"] is False

    def test_figma_get_components_error(self, live_env):
        result = live_env["mod"].figma_get_components(file_key="fake", token="fake")
        assert result["success"] is False

    def test_log_interaction_persists_to_file(self, live_env):
        import json
        live_env["mod"].log_interaction(
            role="user", content="build the login page"
        )
        log_dir = os.path.join(live_env["project"], ".crux", "analytics", "conversations")
        assert os.path.isdir(log_dir)
        log_files = os.listdir(log_dir)
        assert len(log_files) >= 1
        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["role"] == "user"
        assert entry["content"] == "build the login page"
        assert entry["tool"] == "claude-code"  # live_env fixture sets active_tool=claude-code


# ---------------------------------------------------------------------------
# BIP tool wrapper coverage — lines 448, 467, 478
# ---------------------------------------------------------------------------

class TestBipToolWrappers:
    """Test the thin MCP tool wrappers for BIP functions."""

    def test_bip_generate_returns_result(self, live_env):
        result = live_env["mod"].bip_generate()
        # Should return a dict with trigger/content info
        assert isinstance(result, dict)

    def test_bip_approve_returns_result(self, live_env):
        result = live_env["mod"].bip_approve(draft_text="Shipped a new feature today!")
        assert isinstance(result, dict)

    def test_bip_status_returns_result(self, live_env):
        result = live_env["mod"].bip_status()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Impact analysis tool wrapper
# ---------------------------------------------------------------------------

class TestAnalyzeImpact:
    """Test the analyze_impact MCP tool wrapper."""

    def test_returns_dict(self, live_env):
        result = live_env["mod"].analyze_impact(prompt="auth login")
        assert isinstance(result, dict)
        assert "files" in result
        assert "total" in result

    def test_empty_prompt(self, live_env):
        result = live_env["mod"].analyze_impact(prompt="")
        assert result["files"] == []
        assert result["total"] == 0

    def test_top_n(self, live_env):
        result = live_env["mod"].analyze_impact(prompt="test", top_n=5)
        assert len(result["files"]) <= 5
