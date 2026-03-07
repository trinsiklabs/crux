"""Tests for BIP MCP handlers — bip_generate, bip_approve, bip_status."""

import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from scripts.lib.crux_bip import BIPConfig, BIPState, save_config, save_state
from scripts.lib.crux_mcp_handlers import (
    handle_bip_generate,
    handle_bip_approve,
    handle_bip_status,
)


@pytest.fixture
def env(tmp_path):
    """A project with .crux/ dirs and BIP config."""
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    crux = project / ".crux"
    for d in ["sessions", "corrections", "knowledge", "bip", "bip/drafts",
              "analytics/interactions", "analytics/conversations"]:
        (crux / d).mkdir(parents=True)

    # Git repo
    subprocess.run(["git", "init"], cwd=str(project), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(project), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(project), capture_output=True)
    (project / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(project), capture_output=True)

    bip_dir = str(crux / "bip")
    save_config(BIPConfig(), bip_dir)
    save_state(BIPState(), bip_dir)

    return {"project": str(project), "home": str(home), "bip_dir": bip_dir}


# ---------------------------------------------------------------------------
# bip_generate
# ---------------------------------------------------------------------------

class TestBIPGenerate:
    def test_skips_when_no_trigger(self, env):
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
        )
        assert result["status"] == "skipped"
        assert "state" in result

    def test_ready_when_threshold_met(self, env):
        save_state(BIPState(commits_since_last_post=5), env["bip_dir"])
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
        )
        assert result["status"] == "ready"
        assert "context" in result
        assert "voice" in result

    def test_force_bypasses_thresholds(self, env):
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
            force=True,
        )
        assert result["status"] == "ready"

    def test_event_trigger(self, env):
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
            event="test_green",
        )
        assert result["status"] == "ready"
        assert "test_green" in result["trigger_reason"]

    def test_cooldown_blocks(self, env):
        now = datetime.now(timezone.utc).isoformat()
        save_state(BIPState(
            commits_since_last_post=10,
            last_queued_at=now,
        ), env["bip_dir"])
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
        )
        assert result["status"] == "skipped"

    def test_context_includes_commits(self, env):
        # Add a commit
        p = Path(env["project"])
        (p / "feature.py").write_text("# feature")
        subprocess.run(["git", "add", "."], cwd=env["project"], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add cool feature"], cwd=env["project"], capture_output=True)

        save_state(BIPState(commits_since_last_post=5), env["bip_dir"])
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
        )
        assert result["status"] == "ready"
        assert len(result["context"]["commit_messages"]) > 0

    def test_voice_rules_included(self, env):
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
            force=True,
        )
        assert "never_words" in result["voice"]
        assert "Revolutionary" in result["voice"]["never_words"]

    def test_platform_passed_through(self, env):
        result = handle_bip_generate(
            project_dir=env["project"], home=env["home"],
            force=True, platform="reddit",
        )
        assert result["platform"] == "reddit"


# ---------------------------------------------------------------------------
# bip_approve
# ---------------------------------------------------------------------------

class TestBIPApprove:
    def test_saves_draft_file(self, env):
        result = handle_bip_approve(
            project_dir=env["project"],
            draft_text="just shipped crux adopt #buildinpublic",
        )
        assert result["status"] in ("saved", "queued")
        # Draft path not exposed in response (PLAN-166), verify via filesystem
        drafts_dir = os.path.join(env["project"], ".crux", "bip", "drafts")
        draft_files = list(Path(drafts_dir).glob("*.md"))
        assert len(draft_files) >= 1
        assert "crux adopt" in draft_files[0].read_text()

    def test_records_history(self, env):
        handle_bip_approve(
            project_dir=env["project"],
            draft_text="test post",
            source_keys=["git:abc123", "correction:001"],
        )
        from scripts.lib.crux_bip import is_in_history
        bip_dir = os.path.join(env["project"], ".crux", "bip")
        assert is_in_history(bip_dir, "git:abc123")
        assert is_in_history(bip_dir, "correction:001")

    def test_updates_state(self, env):
        save_state(BIPState(commits_since_last_post=10, interactions_since_last_post=30), env["bip_dir"])
        handle_bip_approve(
            project_dir=env["project"],
            draft_text="test post",
        )
        from scripts.lib.crux_bip import load_state
        state = load_state(env["bip_dir"])
        assert state.commits_since_last_post == 0
        assert state.interactions_since_last_post == 0
        assert state.posts_today == 1
        assert state.last_queued_at is not None

    def test_saves_without_typefully_key(self, env):
        # No typefully.key — should save but not queue
        result = handle_bip_approve(
            project_dir=env["project"],
            draft_text="test without typefully",
        )
        assert result["status"] == "saved"
        assert result["queue_error"] is not None


# ---------------------------------------------------------------------------
# bip_status
# ---------------------------------------------------------------------------

class TestBIPStatus:
    def test_returns_state(self, env):
        save_state(BIPState(
            commits_since_last_post=3,
            posts_today=2,
        ), env["bip_dir"])
        result = handle_bip_status(project_dir=env["project"])
        assert result["commits_since_last_post"] == 3
        assert result["posts_today"] == 2
        assert "cooldown_ok" in result
        assert "thresholds" in result

    def test_includes_recent_posts(self, env):
        from scripts.lib.crux_bip import record_history
        record_history(env["bip_dir"], "git:abc", "test post 1")
        record_history(env["bip_dir"], "git:def", "test post 2")

        result = handle_bip_status(project_dir=env["project"])
        assert result["total_posts"] == 2
        assert len(result["recent_posts"]) == 2

    def test_empty_state(self, env):
        result = handle_bip_status(project_dir=env["project"])
        assert result["commits_since_last_post"] == 0
        assert result["total_posts"] == 0
