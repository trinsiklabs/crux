"""Tests for session activation on restore_context — auto-detect uningest sessions."""

import json
import os

import pytest

from scripts.lib.crux_mcp_handlers import handle_restore_context
from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_session import SessionState, save_session, load_session


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = home / "project"
    project.mkdir()
    init_user(home=str(home))
    init_project(project_dir=str(project))

    # Create mode file
    modes_dir = home / ".crux" / "modes"
    (modes_dir / "build-py.md").write_text("You are a Python specialist.")

    crux_dir = str(project / ".crux")
    state = SessionState(active_mode="build-py", active_tool="claude-code")
    save_session(state, crux_dir)
    return {"home": str(home), "project": str(project), "crux_dir": crux_dir}


class TestRestoreContextActivatesSession:
    def test_updates_session_timestamp(self, env):
        old_state = load_session(env["crux_dir"])
        old_ts = old_state.updated_at

        handle_restore_context(env["project"], env["home"])

        new_state = load_session(env["crux_dir"])
        assert new_state.updated_at >= old_ts

    def test_returns_context(self, env):
        result = handle_restore_context(env["project"], env["home"])
        assert "context" in result
        assert "build-py" in result["context"]


class TestSessionAdoptionDetection:
    def test_no_adoption_when_no_jsonl(self, env):
        result = handle_restore_context(env["project"], env["home"])
        assert result.get("session_adoption") is None or result["session_adoption"]["available"] is False

    def test_detects_uningest_session_files(self, env):
        # Create fake Claude Code session .jsonl files
        claude_projects = os.path.join(env["home"], ".claude", "projects")
        project_hash = "-" + env["project"].replace("/", "-")
        session_dir = os.path.join(claude_projects, project_hash)
        os.makedirs(session_dir, exist_ok=True)

        # Write a session file with some content
        session_file = os.path.join(session_dir, "abc123.jsonl")
        entries = [
            {"type": "human", "message": {"content": "build the auth module"}},
            {"type": "assistant", "message": {"content": "I'll create auth.py"}},
        ]
        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = handle_restore_context(env["project"], env["home"])
        adoption = result.get("session_adoption", {})
        assert adoption.get("available") is True
        assert adoption.get("session_count", 0) >= 1
        assert adoption.get("total_lines", 0) >= 2

    def test_no_adoption_when_already_ingested(self, env):
        # Create session file AND checkpoint
        claude_projects = os.path.join(env["home"], ".claude", "projects")
        project_hash = "-" + env["project"].replace("/", "-")
        session_dir = os.path.join(claude_projects, project_hash)
        os.makedirs(session_dir, exist_ok=True)

        session_file = os.path.join(session_dir, "abc123.jsonl")
        with open(session_file, "w") as f:
            f.write('{"type": "human"}\n')

        # Create ingest checkpoint marking this file as processed
        ingest_dir = os.path.join(env["crux_dir"], "ingest")
        os.makedirs(ingest_dir, exist_ok=True)
        checkpoint = {
            "ingested_files": [session_file],
            "status": "completed",
        }
        with open(os.path.join(ingest_dir, "checkpoint.json"), "w") as f:
            json.dump(checkpoint, f)

        result = handle_restore_context(env["project"], env["home"])
        adoption = result.get("session_adoption", {})
        assert adoption.get("available") is False

    def test_adoption_message_is_clear(self, env):
        # Create session file
        claude_projects = os.path.join(env["home"], ".claude", "projects")
        project_hash = "-" + env["project"].replace("/", "-")
        session_dir = os.path.join(claude_projects, project_hash)
        os.makedirs(session_dir, exist_ok=True)

        session_file = os.path.join(session_dir, "def456.jsonl")
        with open(session_file, "w") as f:
            for _ in range(100):
                f.write('{"type": "human", "message": {"content": "work"}}\n')

        result = handle_restore_context(env["project"], env["home"])
        adoption = result.get("session_adoption", {})
        assert "message" in adoption
        assert "session" in adoption["message"].lower()
