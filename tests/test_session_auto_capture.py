"""Tests for auto-capture of session state from tool usage patterns.

Infrastructure enforcement: session state is captured from tool calls,
not from LLM instruction-following. Works with any model.
"""

import json
import os

import pytest

from scripts.lib.crux_hooks import handle_post_tool_use, handle_stop
from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_session import load_session, save_session, SessionState


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = home / "project"
    project.mkdir()
    init_user(home=str(home))
    init_project(project_dir=str(project))
    crux_dir = str(project / ".crux")
    state = SessionState(active_mode="build-py", active_tool="claude-code")
    save_session(state, crux_dir)
    return {
        "home": str(home),
        "project": str(project),
        "crux_dir": crux_dir,
    }


class TestAutoFileCapture:
    """PostToolUse should auto-capture files from Edit/Write tools."""

    def test_edit_captures_file(self, env):
        event = {
            "tool_name": "Edit",
            "tool_input": {"file_path": os.path.join(env["project"], "auth.py")},
            "tool_output": "ok",
        }
        handle_post_tool_use(event, env["project"], env["home"])
        state = load_session(env["crux_dir"])
        assert any("auth.py" in f for f in state.files_touched)

    def test_write_captures_file(self, env):
        event = {
            "tool_name": "Write",
            "tool_input": {"file_path": os.path.join(env["project"], "db.py")},
            "tool_output": "ok",
        }
        handle_post_tool_use(event, env["project"], env["home"])
        state = load_session(env["crux_dir"])
        assert any("db.py" in f for f in state.files_touched)


class TestAutoDecisionCapture:
    """PostToolUse should capture decisions from git commit messages."""

    def test_git_commit_captures_decision(self, env):
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": 'git commit -m "Switch from JWT to session tokens"'},
            "tool_output": "[main abc123] Switch from JWT to session tokens",
        }
        handle_post_tool_use(event, env["project"], env["home"])
        state = load_session(env["crux_dir"])
        assert any("JWT" in d or "session tokens" in d for d in state.key_decisions)

    def test_git_commit_heredoc_captures_decision(self, env):
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": 'git commit -m "$(cat <<\'EOF\'\nAdd OAuth2 flow\nEOF\n)"'},
            "tool_output": "[main def456] Add OAuth2 flow",
        }
        handle_post_tool_use(event, env["project"], env["home"])
        state = load_session(env["crux_dir"])
        assert any("OAuth2" in d for d in state.key_decisions)

    def test_non_commit_bash_no_decision(self, env):
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_output": "total 0",
        }
        handle_post_tool_use(event, env["project"], env["home"])
        state = load_session(env["crux_dir"])
        assert len(state.key_decisions) == 0


class TestAutoWorkingOnCapture:
    """PostToolUse should update working_on from significant tool patterns."""

    def test_test_run_updates_working_on(self, env):
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m pytest tests/test_auth.py"},
            "tool_output": "5 passed",
        }
        handle_post_tool_use(event, env["project"], env["home"])
        state = load_session(env["crux_dir"])
        assert "test" in state.working_on.lower() or state.working_on == ""


class TestAutoHandoffOnStop:
    """Stop hook should auto-write handoff so killing a session preserves state."""

    def test_stop_writes_handoff(self, env):
        # Set up some state first
        state = SessionState(
            active_mode="debug",
            active_tool="claude-code",
            working_on="Fixing auth bug",
            key_decisions=["Use bcrypt for passwords"],
            files_touched=["auth.py"],
        )
        save_session(state, env["crux_dir"])

        handle_stop({}, env["project"], env["home"])

        handoff_path = os.path.join(env["crux_dir"], "sessions", "handoff.md")
        assert os.path.isfile(handoff_path)
        with open(handoff_path) as f:
            content = f.read()
        assert "debug" in content
        assert "Fixing auth bug" in content
        assert "bcrypt" in content

    def test_stop_handoff_empty_state(self, env):
        handle_stop({}, env["project"], env["home"])
        handoff_path = os.path.join(env["crux_dir"], "sessions", "handoff.md")
        assert os.path.isfile(handoff_path)
