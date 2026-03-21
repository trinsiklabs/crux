"""Tests for crux_status.py — runtime health and insight reporting."""

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_session import SessionState, save_session


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    init_user(home=str(home))
    init_project(project_dir=str(project))

    crux_dir = str(project / ".crux")
    state = SessionState(
        active_mode="build-py",
        active_tool="claude-code",
        working_on="Building API",
        key_decisions=["Use REST", "Use JWT"],
        files_touched=["src/app.py", "tests/test_app.py"],
        pending=["Add auth", "Write docs"],
    )
    save_session(state, project_crux_dir=crux_dir)

    # Knowledge
    pk = project / ".crux" / "knowledge"
    (pk / "api-design.md").write_text("# API Design\nREST conventions.")
    (pk / "auth-patterns.md").write_text("# Auth\nJWT patterns.")

    # Modes
    modes_dir = home / ".crux" / "modes"
    (modes_dir / "build-py.md").write_text("Python mode.")
    (modes_dir / "debug.md").write_text("Debug mode.")

    return {"home": str(home), "project": str(project), "crux_dir": crux_dir}


def _write_interactions(project_dir, entries):
    """Helper to write interaction log entries."""
    log_dir = os.path.join(project_dir, ".crux", "analytics", "interactions")
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{today}.jsonl")
    with open(log_file, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _write_corrections(project_dir, entries):
    """Helper to write correction entries."""
    corr_dir = os.path.join(project_dir, ".crux", "corrections")
    os.makedirs(corr_dir, exist_ok=True)
    corr_file = os.path.join(corr_dir, "corrections.jsonl")
    with open(corr_file, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# get_status — the main status report
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_returns_dict(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert isinstance(result, dict)

    def test_includes_session_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "session" in result
        assert result["session"]["active_mode"] == "build-py"
        assert result["session"]["active_tool"] == "claude-code"
        assert result["session"]["working_on"] == "Building API"

    def test_includes_knowledge_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "knowledge" in result
        assert result["knowledge"]["project_entries"] == 2
        assert isinstance(result["knowledge"]["entry_names"], list)

    def test_includes_modes_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "modes" in result
        assert result["modes"]["total"] == 2
        assert "build-py" in result["modes"]["available"]

    def test_includes_hooks_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "hooks" in result
        assert isinstance(result["hooks"]["active"], bool)

    def test_hooks_active_when_settings_has_hooks(self, env):
        from scripts.lib.crux_status import get_status
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        settings = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "crux_hook_runner"}]}]}}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["hooks"]["active"] is True
        assert result["hooks"]["events_registered"] >= 1

    def test_hooks_inactive_when_no_settings(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["hooks"]["active"] is False

    def test_includes_interactions_section(self, env):
        from scripts.lib.crux_status import get_status

        _write_interactions(env["project"], [
            {"timestamp": "2026-03-06T01:00:00Z", "tool_name": "Bash", "tool_input": {}},
            {"timestamp": "2026-03-06T01:01:00Z", "tool_name": "Edit", "tool_input": {}},
            {"timestamp": "2026-03-06T01:02:00Z", "tool_name": "Bash", "tool_input": {}},
        ])

        result = get_status(project_dir=env["project"], home=env["home"])
        assert "interactions" in result
        assert result["interactions"]["today"] == 3
        assert result["interactions"]["tool_breakdown"]["Bash"] == 2
        assert result["interactions"]["tool_breakdown"]["Edit"] == 1

    def test_interactions_zero_when_no_log(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["interactions"]["today"] == 0

    def test_interactions_handles_empty_and_corrupt_lines(self, env):
        from scripts.lib.crux_status import get_status
        log_dir = os.path.join(env["project"], ".crux", "analytics", "interactions")
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(os.path.join(log_dir, f"{today}.jsonl"), "w") as f:
            f.write('{"tool_name":"Bash","tool_input":{},"timestamp":"t"}\n')
            f.write("\n")  # empty line
            f.write("not json\n")  # corrupt line
            f.write('{"tool_name":"Edit","tool_input":{},"timestamp":"t"}\n')

        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["interactions"]["today"] == 2

    def test_includes_corrections_section(self, env):
        from scripts.lib.crux_status import get_status

        _write_corrections(env["project"], [
            {"original": "bad", "corrected": "good", "category": "style", "mode": "build-py", "timestamp": "2026-03-06T01:00:00Z"},
            {"original": "wrong", "corrected": "right", "category": "logic", "mode": "build-py", "timestamp": "2026-03-06T01:01:00Z"},
        ])

        result = get_status(project_dir=env["project"], home=env["home"])
        assert "corrections" in result
        assert result["corrections"]["total"] == 2
        assert result["corrections"]["by_category"]["style"] == 1
        assert result["corrections"]["by_category"]["logic"] == 1

    def test_corrections_zero_when_no_file(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["corrections"]["total"] == 0

    def test_corrections_handles_empty_and_corrupt_lines(self, env):
        from scripts.lib.crux_status import get_status
        corr_dir = os.path.join(env["project"], ".crux", "corrections")
        os.makedirs(corr_dir, exist_ok=True)
        with open(os.path.join(corr_dir, "corrections.jsonl"), "w") as f:
            f.write('{"category":"style","original":"x","corrected":"y","mode":"m","timestamp":"t"}\n')
            f.write("\n")
            f.write("bad\n")
            f.write('{"category":"logic","original":"a","corrected":"b","mode":"m","timestamp":"t"}\n')

        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["corrections"]["total"] == 2

    def test_includes_mcp_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "mcp" in result
        assert isinstance(result["mcp"]["registered"], bool)

    def test_mcp_registered_when_config_exists(self, env):
        from scripts.lib.crux_status import get_status
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        mcp_config = {"mcpServers": {"crux": {"command": "python"}}}
        with open(os.path.join(claude_dir, "mcp.json"), "w") as f:
            json.dump(mcp_config, f)

        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["mcp"]["registered"] is True
        assert result["mcp"]["tool_count"] == 42

    def test_mcp_not_registered_when_no_config(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["mcp"]["registered"] is False

    def test_mcp_tool_count_zero_on_import_error(self, env, monkeypatch):
        from scripts.lib.crux_status import get_status
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        mcp_config = {"mcpServers": {"crux": {"command": "python"}}}
        with open(os.path.join(claude_dir, "mcp.json"), "w") as f:
            json.dump(mcp_config, f)

        # Simulate import failure
        import scripts.lib.crux_status as status_mod
        original_check = status_mod._check_mcp

        def broken_check(project_dir):
            # Temporarily break the import
            import builtins
            real_import = builtins.__import__
            def fail_import(name, *args, **kwargs):
                if "crux_mcp_server" in name:
                    raise ImportError("simulated")
                return real_import(name, *args, **kwargs)
            builtins.__import__ = fail_import
            try:
                result = original_check(project_dir)
            finally:
                builtins.__import__ = real_import
            return result

        monkeypatch.setattr(status_mod, "_check_mcp", broken_check)
        result = get_status(project_dir=env["project"], home=env["home"])
        assert result["mcp"]["registered"] is True
        assert result["mcp"]["tool_count"] == 0

    def test_includes_pending_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "pending" in result
        assert result["pending"]["count"] == 2
        assert "Add auth" in result["pending"]["items"]

    def test_includes_files_section(self, env):
        from scripts.lib.crux_status import get_status
        result = get_status(project_dir=env["project"], home=env["home"])
        assert "files" in result
        assert result["files"]["tracked"] == 2


# ---------------------------------------------------------------------------
# format_status — human-readable output
# ---------------------------------------------------------------------------

class TestFormatStatus:
    def test_returns_string(self, env):
        from scripts.lib.crux_status import get_status, format_status
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_includes_session_info(self, env):
        from scripts.lib.crux_status import get_status, format_status
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "build-py" in output
        assert "Building API" in output

    def test_includes_hook_status(self, env):
        from scripts.lib.crux_status import get_status, format_status
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "HOOK" in output or "Hook" in output or "hook" in output

    def test_includes_interaction_count(self, env):
        from scripts.lib.crux_status import get_status, format_status
        _write_interactions(env["project"], [
            {"timestamp": "t", "tool_name": "Bash", "tool_input": {}},
        ])
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "1" in output

    def test_includes_knowledge_count(self, env):
        from scripts.lib.crux_status import get_status, format_status
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "2" in output  # 2 knowledge entries

    def test_includes_corrections_count(self, env):
        from scripts.lib.crux_status import get_status, format_status
        _write_corrections(env["project"], [
            {"original": "x", "corrected": "y", "category": "style", "mode": "m", "timestamp": "t"},
        ])
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "correction" in output.lower()

    def test_shows_pending_tasks(self, env):
        from scripts.lib.crux_status import get_status, format_status
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "Add auth" in output

    def test_shows_mcp_status(self, env):
        from scripts.lib.crux_status import get_status, format_status
        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "MCP" in output

    def test_shows_hooks_events_when_active(self, env):
        from scripts.lib.crux_status import get_status, format_status
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        settings = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "x"}]}]}}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "ACTIVE" in output
        assert "PostToolUse" in output

    def test_shows_pending_none_when_empty(self, env):
        from scripts.lib.crux_status import get_status, format_status
        from scripts.lib.crux_session import load_session, save_session
        state = load_session(env["crux_dir"])
        state.pending = []
        save_session(state, project_crux_dir=env["crux_dir"])

        status = get_status(project_dir=env["project"], home=env["home"])
        output = format_status(status)
        assert "PENDING: none" in output


# ---------------------------------------------------------------------------
# check_health — pass/fail health checks
# ---------------------------------------------------------------------------

class TestCheckHealth:
    def test_returns_list_of_checks(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        assert isinstance(checks, list)
        assert len(checks) > 0
        assert all("name" in c and "passed" in c for c in checks)

    def test_session_exists_check(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        session_check = next(c for c in checks if "session" in c["name"].lower())
        assert session_check["passed"] is True

    def test_knowledge_check(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        kb_check = next(c for c in checks if "knowledge" in c["name"].lower())
        assert kb_check["passed"] is True

    def test_hooks_check_fails_when_no_hooks(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        hooks_check = next(c for c in checks if "hook" in c["name"].lower())
        assert hooks_check["passed"] is False

    def test_hooks_check_passes_when_hooks_active(self, env):
        from scripts.lib.crux_status import check_health
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        settings = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "crux_hook_runner"}]}]}}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        checks = check_health(project_dir=env["project"], home=env["home"])
        hooks_check = next(c for c in checks if "hook" in c["name"].lower())
        assert hooks_check["passed"] is True

    def test_interactions_check_fails_when_no_logs(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        int_check = next(c for c in checks if "interaction" in c["name"].lower())
        assert int_check["passed"] is False

    def test_interactions_check_passes_with_logs(self, env):
        from scripts.lib.crux_status import check_health
        _write_interactions(env["project"], [
            {"timestamp": "t", "tool_name": "Bash", "tool_input": {}},
        ])
        checks = check_health(project_dir=env["project"], home=env["home"])
        int_check = next(c for c in checks if "interaction" in c["name"].lower())
        assert int_check["passed"] is True

    def test_mcp_check(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        mcp_check = next(c for c in checks if "mcp" in c["name"].lower())
        assert mcp_check["passed"] is False

    def test_modes_check(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        modes_check = next(c for c in checks if "mode" in c["name"].lower())
        assert modes_check["passed"] is True

    def test_all_checks_have_message(self, env):
        from scripts.lib.crux_status import check_health
        checks = check_health(project_dir=env["project"], home=env["home"])
        for c in checks:
            assert "message" in c
            assert len(c["message"]) > 0


# ---------------------------------------------------------------------------
# Liveness checks — verify components are actually working at runtime
# ---------------------------------------------------------------------------

def _write_conversations(project_dir, entries):
    """Helper to write conversation log entries."""
    log_dir = os.path.join(project_dir, ".crux", "analytics", "conversations")
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{today}.jsonl")
    with open(log_file, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _setup_hooks(project_dir, events=None):
    """Helper to configure hooks in settings.local.json."""
    if events is None:
        events = ["SessionStart", "PostToolUse", "UserPromptSubmit", "Stop"]
    claude_dir = os.path.join(project_dir, ".claude")
    os.makedirs(claude_dir, exist_ok=True)
    hooks = {}
    for event in events:
        hooks[event] = [{"matcher": "", "hooks": [{"type": "command", "command": "/usr/bin/python3 -m scripts.lib.crux_hook_runner " + event}]}]
    settings = {"hooks": hooks}
    with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
        json.dump(settings, f)


class TestCheckLiveness:
    """Liveness checks verify components are actually producing data at runtime."""

    def test_returns_list_of_checks(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        assert isinstance(checks, list)
        assert len(checks) > 0
        assert all("name" in c and "passed" in c and "message" in c for c in checks)

    # --- Hook completeness ---

    def test_hook_completeness_passes_with_all_four(self, env):
        from scripts.lib.crux_status import check_liveness
        _setup_hooks(env["project"])
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        hook_check = next(c for c in checks if "hook completeness" in c["name"].lower())
        assert hook_check["passed"] is True

    def test_hook_completeness_fails_with_missing_hooks(self, env):
        from scripts.lib.crux_status import check_liveness
        _setup_hooks(env["project"], events=["PostToolUse", "Stop"])
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        hook_check = next(c for c in checks if "hook completeness" in c["name"].lower())
        assert hook_check["passed"] is False
        assert "SessionStart" in hook_check["message"] or "UserPromptSubmit" in hook_check["message"]

    def test_hook_completeness_fails_with_no_hooks(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        hook_check = next(c for c in checks if "hook completeness" in c["name"].lower())
        assert hook_check["passed"] is False

    # --- Conversation logging ---

    def test_conversation_logging_passes_with_todays_log(self, env):
        from scripts.lib.crux_status import check_liveness
        _write_conversations(env["project"], [
            {"timestamp": "2026-03-06T12:00:00Z", "role": "user", "content": "hello"},
        ])
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        conv_check = next(c for c in checks if "conversation" in c["name"].lower())
        assert conv_check["passed"] is True

    def test_conversation_logging_fails_with_no_log(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        conv_check = next(c for c in checks if "conversation" in c["name"].lower())
        assert conv_check["passed"] is False

    # --- Log consistency ---

    def test_log_consistency_passes_when_both_exist(self, env):
        from scripts.lib.crux_status import check_liveness
        _write_interactions(env["project"], [
            {"timestamp": "2026-03-06T12:00:00Z", "tool_name": "Bash", "tool_input": {}},
        ])
        _write_conversations(env["project"], [
            {"timestamp": "2026-03-06T12:00:00Z", "role": "user", "content": "test"},
        ])
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cons_check = next(c for c in checks if "consistency" in c["name"].lower())
        assert cons_check["passed"] is True

    def test_log_consistency_fails_when_interactions_but_no_conversations(self, env):
        from scripts.lib.crux_status import check_liveness
        _write_interactions(env["project"], [
            {"timestamp": "2026-03-06T12:00:00Z", "tool_name": "Bash", "tool_input": {}},
        ])
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cons_check = next(c for c in checks if "consistency" in c["name"].lower())
        assert cons_check["passed"] is False
        assert "UserPromptSubmit" in cons_check["message"]

    def test_log_consistency_passes_when_neither_exists(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cons_check = next(c for c in checks if "consistency" in c["name"].lower())
        assert cons_check["passed"] is True  # no data yet is fine

    # --- MCP server loadable ---

    def test_mcp_loadable_passes(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import subprocess
        # Mock subprocess.run to simulate MCP server loading successfully
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "37\n"
        mock_result.stderr = ""
        monkeypatch.setattr(subprocess, "run", lambda *args, **kw: mock_result)
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        mcp_check = next(c for c in checks if "mcp loadable" in c["name"].lower())
        assert mcp_check["passed"] is True
        assert "37" in mcp_check["message"]

    def test_mcp_loadable_reports_tool_count(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "42\n"
        mock_result.stderr = ""
        monkeypatch.setattr(subprocess, "run", lambda *args, **kw: mock_result)
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        mcp_check = next(c for c in checks if "mcp loadable" in c["name"].lower())
        assert "tools" in mcp_check["message"].lower()

    # --- Session freshness ---

    def test_session_freshness_passes_when_recent(self, env):
        from scripts.lib.crux_status import check_liveness
        # env fixture just saved session, so it's fresh
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        fresh_check = next(c for c in checks if "session freshness" in c["name"].lower())
        assert fresh_check["passed"] is True

    def test_session_freshness_fails_when_stale(self, env):
        from scripts.lib.crux_status import check_liveness
        from scripts.lib.crux_session import load_session as _load
        from datetime import timedelta
        # Write stale timestamp directly (save_session auto-updates updated_at)
        state = _load(env["crux_dir"])
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        state.updated_at = old_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        state_path = os.path.join(env["crux_dir"], "sessions", "state.json")
        with open(state_path, "w") as f:
            json.dump(state.to_dict(), f)

        checks = check_liveness(project_dir=env["project"], home=env["home"])
        fresh_check = next(c for c in checks if "session freshness" in c["name"].lower())
        assert fresh_check["passed"] is False
        assert "stale" in fresh_check["message"].lower() or "hour" in fresh_check["message"].lower()

    # --- Hook command valid ---

    def test_hook_command_valid_passes_with_real_python(self, env):
        from scripts.lib.crux_status import check_liveness
        import sys
        _setup_hooks(env["project"], events=["PostToolUse"])
        # Rewrite with actual python path
        claude_dir = os.path.join(env["project"], ".claude")
        settings = {"hooks": {"PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": f"{sys.executable} -m scripts.lib.crux_hook_runner PostToolUse"}]}]}}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cmd_check = next(c for c in checks if "hook command" in c["name"].lower())
        assert cmd_check["passed"] is True

    def test_hook_command_valid_fails_with_bad_python(self, env):
        from scripts.lib.crux_status import check_liveness
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        settings = {"hooks": {"PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "/nonexistent/python3 -m scripts.lib.crux_hook_runner PostToolUse"}]}]}}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cmd_check = next(c for c in checks if "hook command" in c["name"].lower())
        assert cmd_check["passed"] is False
        assert "nonexistent" in cmd_check["message"].lower() or "not found" in cmd_check["message"].lower()

    def test_hook_command_valid_with_env_var_prefix(self, env):
        """PYTHONPATH=... prefix should be skipped when finding the executable."""
        from scripts.lib.crux_status import check_liveness
        import sys
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        settings = {"hooks": {"PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": f"PYTHONPATH=/some/path {sys.executable} -m scripts.lib.crux_hook_runner PostToolUse"}]}]}}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cmd_check = next(c for c in checks if "hook command" in c["name"].lower())
        assert cmd_check["passed"] is True

    def test_hook_command_skipped_when_no_hooks(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cmd_check = next(c for c in checks if "hook command" in c["name"].lower())
        # No hooks = skip (pass with info message)
        assert "no hooks" in cmd_check["message"].lower()

    def test_mcp_loadable_fails_on_import_error(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import subprocess

        # MCP check now uses subprocess — mock it to simulate failure
        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
            if "crux_mcp_server" in cmd_str:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=1, stdout="", stderr="ImportError: simulated MCP failure"
                )
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)
        checks = check_liveness(env["project"], env["home"])
        mcp_check = next(c for c in checks if "mcp loadable" in c["name"].lower())
        assert mcp_check["passed"] is False
        assert "failed" in mcp_check["message"].lower()

    def test_session_freshness_fails_with_bad_timestamp(self, env):
        from scripts.lib.crux_status import check_liveness
        # Write invalid timestamp
        state_path = os.path.join(env["crux_dir"], "sessions", "state.json")
        with open(state_path) as f:
            data = json.load(f)
        data["updated_at"] = "not-a-timestamp"
        with open(state_path, "w") as f:
            json.dump(data, f)

        checks = check_liveness(project_dir=env["project"], home=env["home"])
        fresh_check = next(c for c in checks if "session freshness" in c["name"].lower())
        assert fresh_check["passed"] is False
        assert "parse" in fresh_check["message"].lower()

    def test_hook_command_handles_empty_matchers(self, env):
        from scripts.lib.crux_status import check_liveness
        claude_dir = os.path.join(env["project"], ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        # Hook event with empty list and one with empty command
        settings = {"hooks": {
            "SessionStart": [],
            "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": ""}]}],
        }}
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump(settings, f)

        checks = check_liveness(project_dir=env["project"], home=env["home"])
        cmd_check = next(c for c in checks if "hook command" in c["name"].lower())
        assert cmd_check["passed"] is True


# ---------------------------------------------------------------------------
# verify_health — combined static + liveness report
# ---------------------------------------------------------------------------

class TestVerifyHealth:
    def test_returns_dict_with_both_sections(self, env):
        from scripts.lib.crux_status import verify_health
        result = verify_health(project_dir=env["project"], home=env["home"])
        assert "static" in result
        assert "liveness" in result
        assert "summary" in result

    def test_summary_includes_pass_fail_counts(self, env):
        from scripts.lib.crux_status import verify_health
        result = verify_health(project_dir=env["project"], home=env["home"])
        assert "total" in result["summary"]
        assert "passed" in result["summary"]
        assert "failed" in result["summary"]

    def test_all_passed_is_true_when_everything_passes(self, env, monkeypatch):
        from scripts.lib.crux_status import verify_health
        import sys
        import subprocess
        import scripts.lib.crux_audit_backend as backend_mod
        # Mock audit backend to pass (PLAN-169)
        monkeypatch.setattr(backend_mod, "get_backend_status", lambda: {
            "active_backend": "Ollama (qwen3:8b)",
            "ollama_available": True,
            "claude_available": False,
        })
        # Mock subprocess for MCP check
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "37\n"
        mock_result.stderr = ""
        monkeypatch.setattr(subprocess, "run", lambda *args, **kw: mock_result)
        # Set up everything to pass
        _setup_hooks(env["project"])
        # Fix hook command to use real python
        claude_dir = os.path.join(env["project"], ".claude")
        hooks = {}
        for event in ["SessionStart", "PostToolUse", "UserPromptSubmit", "Stop"]:
            hooks[event] = [{"matcher": "", "hooks": [{"type": "command", "command": f"{sys.executable} -m scripts.lib.crux_hook_runner {event}"}]}]
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump({"hooks": hooks}, f)
        # Set up MCP config
        mcp_config = {"mcpServers": {"crux": {"command": "python"}}}
        with open(os.path.join(claude_dir, "mcp.json"), "w") as f:
            json.dump(mcp_config, f)
        # Write interactions and conversations
        _write_interactions(env["project"], [
            {"timestamp": "t", "tool_name": "Bash", "tool_input": {}},
        ])
        _write_conversations(env["project"], [
            {"timestamp": "t", "role": "user", "content": "test"},
        ])

        result = verify_health(project_dir=env["project"], home=env["home"])
        assert result["summary"]["failed"] == 0
        assert result["summary"]["all_passed"] is True

    def test_all_passed_is_false_when_failures_exist(self, env):
        from scripts.lib.crux_status import verify_health
        result = verify_health(project_dir=env["project"], home=env["home"])
        # Without hooks configured, some checks fail
        assert result["summary"]["all_passed"] is False
        assert result["summary"]["failed"] > 0


# ---------------------------------------------------------------------------
# New liveness checks — Ollama, processors, cross-project, Figma
# ---------------------------------------------------------------------------

class TestAuditBackendLivenessCheck:
    """Tests for the PLAN-169 audit backend health check."""

    def test_audit_backend_passes_with_ollama(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import scripts.lib.crux_audit_backend as backend_mod
        monkeypatch.setattr(backend_mod, "get_backend_status", lambda: {
            "active_backend": "Ollama (qwen3:8b)",
            "ollama_available": True,
            "claude_available": False,
        })
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        backend_check = next(c for c in checks if "audit backend" in c["name"].lower())
        assert backend_check["passed"] is True
        assert "Ollama" in backend_check["message"]

    def test_audit_backend_passes_with_claude_fallback(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import scripts.lib.crux_audit_backend as backend_mod
        monkeypatch.setattr(backend_mod, "get_backend_status", lambda: {
            "active_backend": "Claude subagent (security)",
            "ollama_available": False,
            "claude_available": True,
        })
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        backend_check = next(c for c in checks if "audit backend" in c["name"].lower())
        assert backend_check["passed"] is True
        assert "Claude" in backend_check["message"]

    def test_audit_backend_fails_when_disabled(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import scripts.lib.crux_audit_backend as backend_mod
        monkeypatch.setattr(backend_mod, "get_backend_status", lambda: {
            "active_backend": "DISABLED (no LLM available)",
            "ollama_available": False,
            "claude_available": False,
        })
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        backend_check = next(c for c in checks if "audit backend" in c["name"].lower())
        assert backend_check["passed"] is False
        assert "DISABLED" in backend_check["message"]

    def test_audit_fallback_message_when_using_claude(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import scripts.lib.crux_audit_backend as backend_mod
        monkeypatch.setattr(backend_mod, "get_backend_status", lambda: {
            "active_backend": "Claude subagent (security)",
            "ollama_available": False,
            "claude_available": True,
        })
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        fallback_check = next((c for c in checks if "audit fallback" in c["name"].lower()), None)
        assert fallback_check is not None
        assert fallback_check["passed"] is True
        assert "ollama down" in fallback_check["message"].lower()

    def test_audit_backend_error_handled(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import scripts.lib.crux_audit_backend as backend_mod
        monkeypatch.setattr(backend_mod, "get_backend_status", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        backend_check = next(c for c in checks if "audit backend" in c["name"].lower())
        assert backend_check["passed"] is False
        assert "could not check" in backend_check["message"].lower()


class TestBackgroundProcessorLivenessCheck:
    def test_processor_never_run(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        proc_check = next(c for c in checks if "background processor" in c["name"].lower())
        assert proc_check["passed"] is True
        assert "not yet run" in proc_check["message"].lower()

    def test_processor_has_run(self, env):
        from scripts.lib.crux_status import check_liveness
        from scripts.lib.crux_background_processor import _save_processor_state
        _save_processor_state(env["project"], {
            "last_digest": "2026-03-06T01:00:00Z",
            "last_corrections": "2026-03-06T01:00:00Z",
            "last_mode_audit": "2026-03-06T01:00:00Z",
        })
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        proc_check = next(c for c in checks if "background processor" in c["name"].lower())
        assert proc_check["passed"] is True
        assert "all processors" in proc_check["message"].lower()


    def test_processor_exception_handled(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        import scripts.lib.crux_background_processor as bp
        monkeypatch.setattr(bp, "get_processor_status", lambda pd: (_ for _ in ()).throw(RuntimeError("boom")))
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        proc_check = next(c for c in checks if "background processor" in c["name"].lower())
        assert proc_check["passed"] is False
        assert "could not" in proc_check["message"].lower()


class TestCrossProjectRegistryCheck:
    def test_no_registry(self, env):
        from scripts.lib.crux_status import check_liveness
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        reg_check = next(c for c in checks if "cross-project" in c["name"].lower())
        assert reg_check["passed"] is True
        assert "no projects" in reg_check["message"].lower()

    def test_has_registry(self, env):
        from scripts.lib.crux_status import check_liveness
        reg_path = os.path.join(env["home"], ".crux", "projects.json")
        os.makedirs(os.path.dirname(reg_path), exist_ok=True)
        with open(reg_path, "w") as f:
            json.dump({"projects": ["/proj1", "/proj2"]}, f)
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        reg_check = next(c for c in checks if "cross-project" in c["name"].lower())
        assert reg_check["passed"] is True
        assert "2" in reg_check["message"]


class TestFigmaTokenCheck:
    def test_figma_token_set(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        monkeypatch.setenv("FIGMA_TOKEN", "test-token")
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        figma_check = next(c for c in checks if "figma" in c["name"].lower())
        assert figma_check["passed"] is True
        assert "is set" in figma_check["message"]

    def test_figma_token_not_set(self, env, monkeypatch):
        from scripts.lib.crux_status import check_liveness
        monkeypatch.delenv("FIGMA_TOKEN", raising=False)
        checks = check_liveness(project_dir=env["project"], home=env["home"])
        figma_check = next(c for c in checks if "figma" in c["name"].lower())
        assert figma_check["passed"] is True
        assert "not set" in figma_check["message"]


# ---------------------------------------------------------------------------
# generate_findings — actionable insights
# ---------------------------------------------------------------------------

class TestGenerateFindings:
    def _make_status(self, **overrides):
        base = {
            "session": {
                "active_mode": "build-py",
                "active_tool": "claude-code",
                "working_on": "test",
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "decisions": 2,
            },
            "interactions": {"today": 50, "tool_breakdown": {"Bash": 50}},
            "corrections": {"total": 0, "by_category": {}},
            "knowledge": {"project_entries": 3, "entry_names": ["a", "b", "c"]},
            "mcp": {"registered": True, "tool_count": 34},
            "modes": {"total": 15, "available": ["build-py"]},
            "pending": {"count": 2, "items": ["a", "b"]},
            "files": {"tracked": 10},
            "hooks": {"active": True, "events_registered": 4, "events": []},
        }
        for k, v in overrides.items():
            if isinstance(v, dict) and k in base:
                base[k].update(v)
            else:
                base[k] = v
        return base

    def _make_health(self, all_passed=True):
        checks = [{"name": "Session state", "passed": True, "message": "ok"}]
        if not all_passed:
            checks.append({"name": "Ollama", "passed": False, "message": "Not reachable"})
        return {"static": checks, "liveness": [], "summary": {}}

    def test_returns_list(self):
        from scripts.lib.crux_status import generate_findings
        result = generate_findings(self._make_status(), self._make_health())
        assert isinstance(result, list)

    def test_failed_check_produces_critical(self):
        from scripts.lib.crux_status import generate_findings
        findings = generate_findings(self._make_status(), self._make_health(all_passed=False))
        critical = [f for f in findings if f["severity"] == "critical"]
        assert len(critical) == 1
        assert "Ollama" in critical[0]["title"]

    def test_stale_session_warning(self):
        from scripts.lib.crux_status import generate_findings
        old_ts = "2026-03-05T01:00:00Z"
        status = self._make_status(session={
            "active_mode": "build-py", "active_tool": "claude-code",
            "working_on": "x", "updated_at": old_ts, "decisions": 0,
        })
        findings = generate_findings(status, self._make_health())
        stale = [f for f in findings if "stale" in f["title"].lower()]
        assert len(stale) == 1
        assert stale[0]["severity"] == "warning"

    def test_many_corrections_warning(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(corrections={"total": 7, "by_category": {"style": 5, "logic": 2}})
        findings = generate_findings(status, self._make_health())
        corr = [f for f in findings if "correction" in f["title"].lower()]
        assert len(corr) == 1
        assert "style" in corr[0]["detail"]

    def test_zero_corrections_info(self):
        from scripts.lib.crux_status import generate_findings
        findings = generate_findings(self._make_status(), self._make_health())
        corr = [f for f in findings if "correction" in f["title"].lower()]
        assert len(corr) == 1
        assert corr[0]["severity"] == "info"

    def test_high_interactions_info(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(interactions={"today": 600, "tool_breakdown": {}})
        findings = generate_findings(status, self._make_health())
        high = [f for f in findings if "activity" in f["title"].lower()]
        assert len(high) == 1

    def test_zero_interactions_warning(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(interactions={"today": 0, "tool_breakdown": {}})
        findings = generate_findings(status, self._make_health())
        no_int = [f for f in findings if "interaction" in f["title"].lower()]
        assert len(no_int) == 1
        assert no_int[0]["severity"] == "warning"

    def test_empty_knowledge_warning(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(knowledge={"project_entries": 0, "entry_names": []})
        findings = generate_findings(status, self._make_health())
        kb = [f for f in findings if "knowledge" in f["title"].lower()]
        assert len(kb) == 1
        assert kb[0]["severity"] == "warning"

    def test_rich_knowledge_positive(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(knowledge={"project_entries": 12, "entry_names": []})
        findings = generate_findings(status, self._make_health())
        kb = [f for f in findings if "knowledge" in f["title"].lower()]
        assert len(kb) == 1
        assert kb[0]["severity"] == "positive"

    def test_many_pending_warning(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(pending={"count": 15, "items": []})
        findings = generate_findings(status, self._make_health())
        pend = [f for f in findings if "pending" in f["title"].lower()]
        assert len(pend) == 1
        assert pend[0]["severity"] == "warning"

    def test_mcp_positive(self):
        from scripts.lib.crux_status import generate_findings
        findings = generate_findings(self._make_status(), self._make_health())
        mcp = [f for f in findings if "mcp" in f["title"].lower()]
        assert len(mcp) == 1
        assert mcp[0]["severity"] == "positive"

    def test_modes_positive(self):
        from scripts.lib.crux_status import generate_findings
        findings = generate_findings(self._make_status(), self._make_health())
        modes = [f for f in findings if "mode" in f["title"].lower()]
        assert len(modes) == 1
        assert modes[0]["severity"] == "positive"

    def test_large_file_footprint_info(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(files={"tracked": 250})
        findings = generate_findings(status, self._make_health())
        ft = [f for f in findings if "file" in f["title"].lower()]
        assert len(ft) == 1
        assert ft[0]["severity"] == "info"

    def test_sorted_by_severity(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(interactions={"today": 0, "tool_breakdown": {}})
        findings = generate_findings(status, self._make_health(all_passed=False))
        severities = [f["severity"] for f in findings]
        order = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
        assert severities == sorted(severities, key=lambda s: order.get(s, 99))

    def test_invalid_timestamp_no_crash(self):
        from scripts.lib.crux_status import generate_findings
        status = self._make_status(session={
            "active_mode": "x", "active_tool": "y",
            "working_on": "", "updated_at": "bad", "decisions": 0,
        })
        # Should not raise
        findings = generate_findings(status, self._make_health())
        assert isinstance(findings, list)


class TestFormatFindings:
    def test_empty_findings(self):
        from scripts.lib.crux_status import format_findings
        result = format_findings([])
        assert "No findings" in result

    def test_formats_each_finding(self):
        from scripts.lib.crux_status import format_findings
        findings = [
            {"severity": "critical", "title": "Something broke", "detail": "Fix it"},
            {"severity": "positive", "title": "All good", "detail": "Nice"},
        ]
        result = format_findings(findings)
        assert "Something broke" in result
        assert "Fix it" in result
        assert "All good" in result

    def test_includes_findings_header(self):
        from scripts.lib.crux_status import format_findings
        result = format_findings([{"severity": "info", "title": "t", "detail": "d"}])
        assert result.startswith("FINDINGS")


# ---------------------------------------------------------------------------
# Coverage gap tests — lines 443-450
# ---------------------------------------------------------------------------

class TestLivenessMCPTimeoutAndException:
    """Test MCP loadable check exception branches."""

    def test_mcp_loadable_reports_timeout(self, env, monkeypatch):
        """Lines 443-448: subprocess.TimeoutExpired is caught."""
        from scripts.lib.crux_status import check_liveness
        import subprocess

        original_run = subprocess.run

        def timeout_run(cmd, *args, **kwargs):
            cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
            if "crux_mcp_server" in cmd_str:
                raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", timeout_run)
        checks = check_liveness(env["project"], env["home"])
        mcp_check = next(c for c in checks if "mcp loadable" in c["name"].lower())
        assert mcp_check["passed"] is False
        assert "timed out" in mcp_check["message"].lower()

    def test_mcp_loadable_reports_generic_exception(self, env, monkeypatch):
        """Lines 449-450: generic Exception is caught."""
        from scripts.lib.crux_status import check_liveness
        import subprocess

        original_run = subprocess.run

        def error_run(cmd, *args, **kwargs):
            cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
            if "crux_mcp_server" in cmd_str:
                raise PermissionError("no permission")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", error_run)
        checks = check_liveness(env["project"], env["home"])
        mcp_check = next(c for c in checks if "mcp loadable" in c["name"].lower())
        assert mcp_check["passed"] is False
        assert "failed" in mcp_check["message"].lower()
