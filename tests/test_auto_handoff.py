"""Tests for auto_handoff — generate handoff from accumulated session state."""

import os

import pytest

from scripts.lib.crux_session import (
    SessionState, save_session, auto_handoff, read_handoff,
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


class TestAutoHandoff:
    def test_returns_string(self, env):
        state = SessionState(active_mode="build-py", active_tool="claude-code")
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert isinstance(result, str)

    def test_contains_mode(self, env):
        state = SessionState(active_mode="debug", active_tool="claude-code")
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert "debug" in result

    def test_contains_tool(self, env):
        state = SessionState(active_mode="build-py", active_tool="cruxcli")
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert "cruxcli" in result

    def test_contains_working_on(self, env):
        state = SessionState(working_on="Building OAuth2 flow")
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert "Building OAuth2 flow" in result

    def test_contains_decisions(self, env):
        state = SessionState(key_decisions=["Use JWT tokens", "PostgreSQL for sessions"])
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert "JWT tokens" in result
        assert "PostgreSQL" in result

    def test_contains_files(self, env):
        state = SessionState(files_touched=["auth.py", "db.py"])
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert "auth.py" in result
        assert "db.py" in result

    def test_contains_pending(self, env):
        state = SessionState(pending=["Write tests", "Deploy to staging"])
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert "Write tests" in result

    def test_writes_handoff_file(self, env):
        state = SessionState(
            active_mode="build-py",
            active_tool="claude-code",
            working_on="Auth refactor",
        )
        save_session(state, env["crux_dir"])
        auto_handoff(env["crux_dir"])
        content = read_handoff(env["crux_dir"])
        assert content is not None
        assert "Auth refactor" in content

    def test_empty_state(self, env):
        state = SessionState()
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_session_file(self, env):
        # Don't save any session
        result = auto_handoff(env["crux_dir"])
        assert isinstance(result, str)

    def test_truncates_large_state(self, env):
        state = SessionState(
            key_decisions=[f"Decision {i}" for i in range(200)],
            files_touched=[f"file_{i}.py" for i in range(200)],
        )
        save_session(state, env["crux_dir"])
        result = auto_handoff(env["crux_dir"])
        # Should still be reasonable length, not 200 of each
        assert len(result) < 10000
