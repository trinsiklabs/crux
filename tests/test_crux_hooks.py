"""Tests for crux_hooks.py — Claude Code hook handlers for Crux integration.

These hooks fire on Claude Code events (SessionStart, PostToolUse, Stop, etc.)
and capture interactions, file touches, and corrections into the Crux system.
"""

import json
import os

import pytest

from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_session import load_session, save_session, SessionState


@pytest.fixture
def env(tmp_path):
    """Full Crux environment for hook testing."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    init_user(home=str(home))
    init_project(project_dir=str(project))

    # Seed a session
    crux_dir = str(project / ".crux")
    state = SessionState(
        active_mode="build-py",
        active_tool="claude-code",
        working_on="Building API",
    )
    save_session(state, project_crux_dir=crux_dir)

    # Create a mode file
    modes_dir = home / ".crux" / "modes"
    (modes_dir / "build-py.md").write_text("You are a Python specialist.")

    return {"home": str(home), "project": str(project), "crux_dir": crux_dir}


# ---------------------------------------------------------------------------
# session_start hook
# ---------------------------------------------------------------------------

class TestHandleSessionStart:
    def test_returns_context_on_startup(self, env):
        from scripts.lib.crux_hooks import handle_session_start

        result = handle_session_start(
            event_data={"source": "startup"},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert "context" in result
        assert "build-py" in result["context"]  # mode name in context

    def test_returns_context_on_resume(self, env):
        from scripts.lib.crux_hooks import handle_session_start

        result = handle_session_start(
            event_data={"source": "resume"},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert "Building API" in result["context"]  # working_on in context

    def test_includes_pending_tasks(self, env):
        from scripts.lib.crux_hooks import handle_session_start

        # Add pending tasks
        state = load_session(env["crux_dir"])
        state.pending.append("Fix login bug")
        save_session(state, project_crux_dir=env["crux_dir"])

        result = handle_session_start(
            event_data={"source": "startup"},
            project_dir=env["project"],
            home=env["home"],
        )
        assert "Fix login bug" in result["context"]

    def test_includes_mode_prompt(self, env):
        from scripts.lib.crux_hooks import handle_session_start

        result = handle_session_start(
            event_data={"source": "startup"},
            project_dir=env["project"],
            home=env["home"],
        )
        assert "Python specialist" in result["context"]

    def test_auto_sets_active_tool_to_claude_code(self, env):
        from scripts.lib.crux_hooks import handle_session_start

        # Start with a different tool
        state = load_session(env["crux_dir"])
        state.active_tool = "opencode"
        save_session(state, project_crux_dir=env["crux_dir"])

        handle_session_start(
            event_data={"source": "startup"},
            project_dir=env["project"],
            home=env["home"],
        )

        # Session should now say claude-code
        updated = load_session(env["crux_dir"])
        assert updated.active_tool == "claude-code"

    def test_includes_key_decisions(self, env):
        from scripts.lib.crux_hooks import handle_session_start

        state = load_session(env["crux_dir"])
        state.key_decisions.append("Use REST not GraphQL")
        save_session(state, project_crux_dir=env["crux_dir"])

        result = handle_session_start(
            event_data={"source": "startup"},
            project_dir=env["project"],
            home=env["home"],
        )
        assert "Use REST not GraphQL" in result["context"]
        assert "Key Decisions" in result["context"]

    def test_handles_missing_session(self, tmp_path):
        from scripts.lib.crux_hooks import handle_session_start

        home = tmp_path / "home"
        project = tmp_path / "project"
        home.mkdir()
        project.mkdir()
        init_user(home=str(home))
        init_project(project_dir=str(project))

        result = handle_session_start(
            event_data={"source": "startup"},
            project_dir=str(project),
            home=str(home),
        )
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# post_tool_use hook — file tracking
# ---------------------------------------------------------------------------

class TestHandlePostToolUseFileTracking:
    def test_tracks_edited_file(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        # Use path within project dir (PLAN-166 validates paths)
        file_path = os.path.join(env["project"], "src", "app.py")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        result = handle_post_tool_use(
            event_data={
                "tool_name": "Edit",
                "tool_input": {"file_path": file_path},
            },
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert result["file_tracked"] == file_path

        state = load_session(env["crux_dir"])
        assert file_path in state.files_touched

    def test_tracks_written_file(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        file_path = os.path.join(env["project"], "src", "new_file.py")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        handle_post_tool_use(
            event_data={
                "tool_name": "Write",
                "tool_input": {"file_path": file_path},
            },
            project_dir=env["project"],
            home=env["home"],
        )
        state = load_session(env["crux_dir"])
        assert file_path in state.files_touched

    def test_no_duplicate_file_tracking(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        file_path = os.path.join(env["project"], "src", "app.py")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        for _ in range(3):
            handle_post_tool_use(
                event_data={
                    "tool_name": "Edit",
                    "tool_input": {"file_path": file_path},
                },
                project_dir=env["project"],
                home=env["home"],
            )
        state = load_session(env["crux_dir"])
        assert state.files_touched.count(file_path) == 1

    def test_ignores_non_file_tools(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        result = handle_post_tool_use(
            event_data={
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
            },
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert result.get("file_tracked") is None

    def test_handles_missing_file_path(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        result = handle_post_tool_use(
            event_data={
                "tool_name": "Edit",
                "tool_input": {},
            },
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert result.get("file_tracked") is None


# ---------------------------------------------------------------------------
# post_tool_use hook — interaction logging
# ---------------------------------------------------------------------------

class TestHandlePostToolUseInteractionLogging:
    def test_logs_bash_interaction(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        handle_post_tool_use(
            event_data={
                "tool_name": "Bash",
                "tool_input": {"command": "pytest tests/"},
            },
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "interactions")
        log_files = os.listdir(log_dir)
        assert len(log_files) == 1

        with open(os.path.join(log_dir, log_files[0])) as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        assert entry["tool_name"] == "Bash"
        assert entry["tool_input"]["command"] == "pytest tests/"

    def test_logs_all_tool_interactions(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        for tool in ["Bash", "Edit", "Read", "Grep"]:
            handle_post_tool_use(
                event_data={
                    "tool_name": tool,
                    "tool_input": {"command": "test"} if tool == "Bash" else {"file_path": "/f"},
                },
                project_dir=env["project"],
                home=env["home"],
            )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "interactions")
        log_files = os.listdir(log_dir)
        assert len(log_files) == 1

        with open(os.path.join(log_dir, log_files[0])) as f:
            lines = f.readlines()
        assert len(lines) == 4

    def test_logs_mcp_tool_interactions(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        handle_post_tool_use(
            event_data={
                "tool_name": "mcp__crux__lookup_knowledge",
                "tool_input": {"query": "api"},
            },
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "interactions")
        log_files = os.listdir(log_dir)
        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["tool_name"] == "mcp__crux__lookup_knowledge"


# ---------------------------------------------------------------------------
# stop hook — session summary update
# ---------------------------------------------------------------------------

class TestHandleStop:
    def test_updates_session_timestamp(self, env):
        from scripts.lib.crux_hooks import handle_stop

        old_state = load_session(env["crux_dir"])
        old_ts = old_state.updated_at

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"

        new_state = load_session(env["crux_dir"])
        assert new_state.updated_at >= old_ts

    def test_records_interaction_count(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use, handle_stop

        # Generate some interactions first
        for i in range(5):
            handle_post_tool_use(
                event_data={
                    "tool_name": "Bash",
                    "tool_input": {"command": f"echo {i}"},
                },
                project_dir=env["project"],
                home=env["home"],
            )

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["interaction_count"] >= 5


# ---------------------------------------------------------------------------
# correction detection
# ---------------------------------------------------------------------------

class TestHandleCorrectionDetection:
    def test_detects_correction_phrase(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        result = handle_user_prompt(
            event_data={
                "prompt": "no, that's wrong. Use snake_case not camelCase.",
            },
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["correction_detected"] is True
        assert result["status"] == "ok"

        # Check correction was logged
        from scripts.lib.crux_paths import get_project_paths
        paths = get_project_paths(env["project"])
        assert os.path.exists(paths.corrections_file)

    def test_no_false_positive_on_normal_prompt(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        result = handle_user_prompt(
            event_data={
                "prompt": "now add a login endpoint",
            },
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["correction_detected"] is False

    def test_detects_multiple_correction_patterns(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        correction_phrases = [
            "actually, do it this way instead",
            "no that's not right",
            "wrong, use pytest not unittest",
            "I said use snake_case",
            "that's incorrect, the port should be 8080",
            "stop, you're doing it wrong",
            "not like that, like this",
        ]
        for phrase in correction_phrases:
            result = handle_user_prompt(
                event_data={"prompt": phrase},
                project_dir=env["project"],
                home=env["home"],
            )
            assert result["correction_detected"] is True, f"Failed to detect: {phrase}"

    def test_correction_logged_with_prompt_text(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt
        from scripts.lib.crux_paths import get_project_paths

        handle_user_prompt(
            event_data={
                "prompt": "no, use aiohttp not requests",
            },
            project_dir=env["project"],
            home=env["home"],
        )

        paths = get_project_paths(env["project"])
        with open(paths.corrections_file) as f:
            entry = json.loads(f.readline())
        assert entry["category"] == "user-correction"
        assert "aiohttp" in entry["original"]

    def test_no_correction_on_empty_prompt(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        result = handle_user_prompt(
            event_data={"prompt": ""},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["correction_detected"] is False


# ---------------------------------------------------------------------------
# full-text conversation logging (UserPromptSubmit)
# ---------------------------------------------------------------------------

class TestUserPromptConversationLogging:
    """All user messages should be logged to conversations JSONL, not just corrections."""

    def test_normal_message_is_logged(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        handle_user_prompt(
            event_data={"prompt": "add a login endpoint"},
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        log_files = os.listdir(log_dir)
        assert len(log_files) == 1

        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["role"] == "user"
        assert entry["content"] == "add a login endpoint"
        assert "timestamp" in entry

    def test_correction_message_is_also_logged_to_conversations(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        handle_user_prompt(
            event_data={"prompt": "no, use aiohttp instead"},
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        log_files = os.listdir(log_dir)
        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["role"] == "user"
        assert "aiohttp" in entry["content"]

    def test_empty_prompt_is_not_logged(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        handle_user_prompt(
            event_data={"prompt": ""},
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        assert not os.path.exists(log_dir) or len(os.listdir(log_dir)) == 0

    def test_whitespace_only_prompt_is_not_logged(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        handle_user_prompt(
            event_data={"prompt": "   \n  "},
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        assert not os.path.exists(log_dir) or len(os.listdir(log_dir)) == 0

    def test_logs_include_active_mode(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        handle_user_prompt(
            event_data={"prompt": "build the API"},
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        log_files = os.listdir(log_dir)
        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["mode"] == "build-py"

    def test_logs_include_tool_name(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        handle_user_prompt(
            event_data={"prompt": "build the API"},
            project_dir=env["project"],
            home=env["home"],
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        log_files = os.listdir(log_dir)
        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["tool"] == "claude-code"

    def test_logs_include_metadata_when_provided(self, env):
        from scripts.lib.crux_hooks import _log_conversation

        _log_conversation(
            role="user",
            content="test with metadata",
            project_dir=env["project"],
            mode="build-py",
            tool="claude-code",
            metadata={"source": "test"},
        )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        log_files = os.listdir(log_dir)
        with open(os.path.join(log_dir, log_files[0])) as f:
            entry = json.loads(f.readline())
        assert entry["metadata"] == {"source": "test"}

    def test_multiple_messages_append_to_same_file(self, env):
        from scripts.lib.crux_hooks import handle_user_prompt

        for msg in ["first message", "second message", "third message"]:
            handle_user_prompt(
                event_data={"prompt": msg},
                project_dir=env["project"],
                home=env["home"],
            )
        log_dir = os.path.join(env["project"], ".crux", "analytics", "conversations")
        log_files = os.listdir(log_dir)
        assert len(log_files) == 1  # all in one daily file

        with open(os.path.join(log_dir, log_files[0])) as f:
            lines = f.readlines()
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# build_hook_settings — generates the settings config
# ---------------------------------------------------------------------------

class TestBuildHookSettings:
    def test_generates_valid_json(self, env):
        from scripts.lib.crux_hooks import build_hook_settings

        settings = build_hook_settings(
            project_dir=env["project"],
            home=env["home"],
        )
        assert "hooks" in settings
        # Must be JSON-serializable
        json.dumps(settings)

    def test_has_session_start_hook(self, env):
        from scripts.lib.crux_hooks import build_hook_settings

        settings = build_hook_settings(
            project_dir=env["project"],
            home=env["home"],
        )
        assert "SessionStart" in settings["hooks"]
        hook = settings["hooks"]["SessionStart"][0]
        assert hook["hooks"][0]["type"] == "command"

    def test_has_post_tool_use_hook(self, env):
        from scripts.lib.crux_hooks import build_hook_settings

        settings = build_hook_settings(
            project_dir=env["project"],
            home=env["home"],
        )
        assert "PostToolUse" in settings["hooks"]

    def test_has_stop_hook(self, env):
        from scripts.lib.crux_hooks import build_hook_settings

        settings = build_hook_settings(
            project_dir=env["project"],
            home=env["home"],
        )
        assert "Stop" in settings["hooks"]

    def test_has_user_prompt_hook(self, env):
        from scripts.lib.crux_hooks import build_hook_settings

        settings = build_hook_settings(
            project_dir=env["project"],
            home=env["home"],
        )
        assert "UserPromptSubmit" in settings["hooks"]

    def test_hook_commands_reference_crux_hook_runner(self, env):
        from scripts.lib.crux_hooks import build_hook_settings

        settings = build_hook_settings(
            project_dir=env["project"],
            home=env["home"],
        )
        for event_name, event_hooks in settings["hooks"].items():
            for hook_group in event_hooks:
                for hook in hook_group["hooks"]:
                    assert "crux_hook_runner" in hook["command"]


# ---------------------------------------------------------------------------
# hook_runner — the shell entry point that dispatches to handlers
# ---------------------------------------------------------------------------

class TestHookRunner:
    def test_dispatches_session_start(self, env):
        from scripts.lib.crux_hooks import run_hook

        event_data = json.dumps({
            "hook_event_name": "SessionStart",
            "source": "startup",
            "cwd": env["project"],
        })
        result = run_hook(
            event_json=event_data,
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"

    def test_dispatches_post_tool_use(self, env):
        from scripts.lib.crux_hooks import run_hook

        event_data = json.dumps({
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/main.py"},
        })
        result = run_hook(
            event_json=event_data,
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"

    def test_dispatches_stop(self, env):
        from scripts.lib.crux_hooks import run_hook

        event_data = json.dumps({
            "hook_event_name": "Stop",
        })
        result = run_hook(
            event_json=event_data,
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"

    def test_dispatches_user_prompt(self, env):
        from scripts.lib.crux_hooks import run_hook

        event_data = json.dumps({
            "hook_event_name": "UserPromptSubmit",
            "prompt": "no, use async instead",
        })
        result = run_hook(
            event_json=event_data,
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert result["correction_detected"] is True

    def test_unknown_event_is_noop(self, env):
        from scripts.lib.crux_hooks import run_hook

        event_data = json.dumps({
            "hook_event_name": "UnknownEvent",
        })
        result = run_hook(
            event_json=event_data,
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"

    def test_invalid_json_returns_error(self, env):
        from scripts.lib.crux_hooks import run_hook

        result = run_hook(
            event_json="not json",
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# TDD compliance checker
# ---------------------------------------------------------------------------

class TestCheckTddCompliance:
    """Tests for the TDD enforcement check that runs in handle_stop.

    The checker examines files_touched in session state and warns when
    source files were modified without corresponding test files.
    """

    def test_no_files_returns_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([])
        assert result["compliant"] is True
        assert result["warnings"] == []

    def test_only_test_files_returns_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "tests/test_crux_hooks.py",
            "tests/setup_syntax.bats",
        ])
        assert result["compliant"] is True
        assert result["warnings"] == []

    def test_python_source_without_test_warns(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_hooks.py",
        ])
        assert result["compliant"] is False
        assert len(result["warnings"]) == 1
        assert "crux_hooks.py" in result["warnings"][0]

    def test_python_source_with_test_is_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_hooks.py",
            "tests/test_crux_hooks.py",
        ])
        assert result["compliant"] is True

    def test_setup_sh_without_test_warns(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "setup.sh",
        ])
        assert result["compliant"] is False
        assert any("setup.sh" in w for w in result["warnings"])

    def test_setup_sh_with_any_setup_test_is_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "setup.sh",
            "tests/setup_helpers.bats",
        ])
        assert result["compliant"] is True

    def test_bin_crux_without_test_warns(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "bin/crux",
        ])
        assert result["compliant"] is False
        assert any("bin/crux" in w for w in result["warnings"])

    def test_bin_crux_with_test_is_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "bin/crux",
            "tests/crux_cli.bats",
        ])
        assert result["compliant"] is True

    def test_js_plugin_without_test_warns(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "plugins/session-logger.js",
        ])
        assert result["compliant"] is False
        assert any("session-logger.js" in w for w in result["warnings"])

    def test_js_plugin_with_test_is_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "plugins/session-logger.js",
            "tests/plugins.test.js",
        ])
        assert result["compliant"] is True

    def test_js_tool_without_test_warns(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "tools/run_script.js",
        ])
        assert result["compliant"] is False

    def test_js_tool_with_test_is_compliant(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "tools/run_script.js",
            "tests/tools.test.js",
        ])
        assert result["compliant"] is True

    def test_multiple_sources_partial_coverage_warns(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_hooks.py",
            "scripts/lib/crux_session.py",
            "tests/test_crux_hooks.py",
            # missing tests/test_crux_session.py
        ])
        assert result["compliant"] is False
        assert len(result["warnings"]) == 1
        assert "crux_session.py" in result["warnings"][0]

    def test_non_source_files_are_ignored(self):
        """Config files, docs, etc. don't need tests."""
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "CLAUDE.md",
            ".claude/settings.local.json",
            "modes/build-py.md",
            "knowledge/corrections.jsonl",
        ])
        assert result["compliant"] is True

    def test_init_py_is_ignored(self):
        """__init__.py files don't need their own tests."""
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/__init__.py",
            "scripts/__init__.py",
        ])
        assert result["compliant"] is True

    def test_alternate_test_naming_accepted(self):
        """Some test files use non-standard names (e.g. test_mcp_handlers_expanded)."""
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_mcp_handlers.py",
            "tests/test_mcp_handlers_expanded.py",
        ])
        assert result["compliant"] is True

    def test_mcp_server_with_its_test(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_mcp_server.py",
            "tests/test_mcp_server.py",
        ])
        assert result["compliant"] is True

    def test_absolute_paths_are_normalized(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "/Users/user/personal/crux/scripts/lib/crux_hooks.py",
            "/Users/user/personal/crux/tests/test_crux_hooks.py",
        ])
        assert result["compliant"] is True

    def test_uncovered_sources_listed_in_result(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_hooks.py",
            "setup.sh",
        ])
        assert result["compliant"] is False
        assert "uncovered_sources" in result
        assert len(result["uncovered_sources"]) == 2

    def test_expected_test_files_included(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance([
            "scripts/lib/crux_session.py",
        ])
        assert result["compliant"] is False
        assert "expected_tests" in result
        assert "tests/test_crux_session.py" in result["expected_tests"]

    def test_expected_test_for_setup_sh(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance(["setup.sh"])
        assert "expected_tests" in result
        # setup.sh maps to tests/setup_*.bats — show the pattern
        assert any("setup_" in t for t in result["expected_tests"])

    def test_expected_test_for_bin_crux(self):
        from scripts.lib.crux_hooks import check_tdd_compliance

        result = check_tdd_compliance(["bin/crux"])
        assert "tests/crux_cli.bats" in result["expected_tests"]


# ---------------------------------------------------------------------------
# Background processor integration
# ---------------------------------------------------------------------------

class TestHandleStopBackgroundProcessor:
    def test_stop_triggers_processor_when_thresholds_met(self, env):
        from scripts.lib.crux_hooks import handle_stop, handle_post_tool_use

        # Write enough corrections to exceed threshold (default 10)
        corr_dir = os.path.join(env["project"], ".crux", "corrections")
        os.makedirs(corr_dir, exist_ok=True)
        with open(os.path.join(corr_dir, "corrections.jsonl"), "w") as f:
            for i in range(15):
                f.write(json.dumps({"original": f"bad{i}", "corrected": f"good{i}",
                                    "category": "style", "mode": "build-py",
                                    "timestamp": "2026-03-06T01:00:00Z"}) + "\n")

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert "processors_run" in result
        assert len(result["processors_run"]) > 0

    def test_stop_skips_processor_when_below_thresholds(self, env):
        from scripts.lib.crux_hooks import handle_stop

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert "processors_run" not in result

    def test_processor_failure_doesnt_break_stop(self, env, monkeypatch):
        from scripts.lib.crux_hooks import handle_stop
        import scripts.lib.crux_background_processor as bp
        monkeypatch.setattr(bp, "should_process", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"
        assert "processors_run" not in result


class TestPostToolUsePeriodicProcessor:
    def test_triggers_processor_at_interval(self, env, monkeypatch):
        from scripts.lib.crux_hooks import handle_post_tool_use
        import scripts.lib.crux_hooks as hooks_mod

        # Write corrections to exceed threshold
        corr_dir = os.path.join(env["project"], ".crux", "corrections")
        os.makedirs(corr_dir, exist_ok=True)
        with open(os.path.join(corr_dir, "corrections.jsonl"), "w") as f:
            for i in range(15):
                f.write(json.dumps({"original": f"bad{i}", "corrected": f"good{i}",
                                    "category": "style", "mode": "build-py",
                                    "timestamp": "2026-03-06T01:00:00Z"}) + "\n")

        # Mock _count_interactions to return exactly the interval
        monkeypatch.setattr(hooks_mod, "_count_interactions", lambda pd: 50)

        result = handle_post_tool_use(
            event_data={"tool_name": "Bash", "tool_input": {"command": "echo"}},
            project_dir=env["project"],
            home=env["home"],
        )
        assert "processors_run" in result

    def test_no_trigger_between_intervals(self, env, monkeypatch):
        from scripts.lib.crux_hooks import handle_post_tool_use
        import scripts.lib.crux_hooks as hooks_mod

        monkeypatch.setattr(hooks_mod, "_count_interactions", lambda pd: 25)

        result = handle_post_tool_use(
            event_data={"tool_name": "Bash", "tool_input": {"command": "echo"}},
            project_dir=env["project"],
            home=env["home"],
        )
        assert "processors_run" not in result


class TestPostToolUseBIPCounter:
    """Verify PostToolUse increments BIP interaction counter."""

    def test_increments_bip_interactions(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        # Create bip dir
        bip_dir = os.path.join(env["project"], ".crux", "bip")
        os.makedirs(bip_dir, exist_ok=True)

        handle_post_tool_use(
            event_data={"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}},
            project_dir=env["project"],
            home=env["home"],
        )
        handle_post_tool_use(
            event_data={"tool_name": "Grep", "tool_input": {"pattern": "foo"}},
            project_dir=env["project"],
            home=env["home"],
        )

        from scripts.lib.crux_bip import load_state
        state = load_state(bip_dir)
        assert state.interactions_since_last_post == 2

    def test_no_crash_without_bip_dir(self, env):
        from scripts.lib.crux_hooks import handle_post_tool_use

        # No bip dir — should not crash
        result = handle_post_tool_use(
            event_data={"tool_name": "Read", "tool_input": {}},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["status"] == "ok"


class TestHandleStopTddCheck:
    """Verify that handle_stop includes TDD compliance in its result."""

    def test_stop_includes_tdd_compliance(self, env):
        from scripts.lib.crux_hooks import handle_stop

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert "tdd_compliant" in result

    def test_stop_warns_when_source_touched_without_tests(self, env):
        from scripts.lib.crux_hooks import handle_stop
        from scripts.lib.crux_session import load_session, save_session

        # Simulate editing a source file without its test
        state = load_session(env["crux_dir"])
        state.files_touched = ["scripts/lib/crux_hooks.py"]
        save_session(state, project_crux_dir=env["crux_dir"])

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["tdd_compliant"] is False
        assert len(result["tdd_warnings"]) > 0

    def test_stop_compliant_when_source_and_test_both_touched(self, env):
        from scripts.lib.crux_hooks import handle_stop
        from scripts.lib.crux_session import load_session, save_session

        state = load_session(env["crux_dir"])
        state.files_touched = [
            "scripts/lib/crux_hooks.py",
            "tests/test_crux_hooks.py",
        ]
        save_session(state, project_crux_dir=env["crux_dir"])

        result = handle_stop(
            event_data={},
            project_dir=env["project"],
            home=env["home"],
        )
        assert result["tdd_compliant"] is True
