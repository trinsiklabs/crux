"""Tests for crux_bip.py — build-in-public state, config, and history management."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from scripts.lib.crux_bip import (
    BIPConfig,
    BIPState,
    load_config,
    save_config,
    load_state,
    save_state,
    record_history,
    is_in_history,
    load_history,
    reset_counters,
    increment_counter,
    check_cooldown,
    get_escalation_action,
    should_escalate_to_blog,
    get_escalation_cooldown,
)


@pytest.fixture
def bip_dir(tmp_path):
    """A .crux/bip/ directory ready for use."""
    d = tmp_path / ".crux" / "bip"
    d.mkdir(parents=True)
    (d / "drafts").mkdir()
    return str(d)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestBIPConfig:
    def test_default_config(self):
        cfg = BIPConfig()
        assert cfg.commit_threshold == 4
        assert cfg.cooldown_minutes == 15
        assert cfg.target_posts_per_hour == 1
        assert cfg.interaction_threshold == 30
        assert cfg.token_threshold == 50000
        assert "x" in cfg.platforms

    def test_save_and_load_config(self, bip_dir):
        cfg = BIPConfig(commit_threshold=6, cooldown_minutes=20)
        save_config(cfg, bip_dir)

        loaded = load_config(bip_dir)
        assert loaded.commit_threshold == 6
        assert loaded.cooldown_minutes == 20

    def test_load_missing_config_returns_defaults(self, bip_dir):
        cfg = load_config(bip_dir)
        assert cfg.commit_threshold == 4

    def test_load_corrupt_config_returns_defaults(self, bip_dir):
        Path(bip_dir, "config.json").write_text("not json{{{")
        cfg = load_config(bip_dir)
        assert cfg.commit_threshold == 4

    def test_config_high_signal_events(self):
        cfg = BIPConfig()
        assert "test_green" in cfg.high_signal_events
        assert "crux_switch" in cfg.high_signal_events
        assert "correction_detected" in cfg.high_signal_events

    def test_config_voice_rules(self):
        cfg = BIPConfig()
        assert len(cfg.never_words) > 0
        assert "Revolutionary" in cfg.never_words

    def test_config_typefully_fields(self):
        cfg = BIPConfig(social_set_id=12345, api_key_path="/tmp/key")
        save_config(cfg, self._make_dir(cfg))
        assert cfg.social_set_id == 12345
        assert cfg.api_key_path == "/tmp/key"

    def _make_dir(self, cfg):
        """Helper — not a real test."""
        import tempfile
        d = tempfile.mkdtemp()
        return d


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class TestBIPState:
    def test_default_state(self):
        state = BIPState()
        assert state.commits_since_last_post == 0
        assert state.tokens_since_last_post == 0
        assert state.interactions_since_last_post == 0
        assert state.posts_today == 0
        assert state.posts_this_hour == 0
        assert state.last_queued_at is None

    def test_save_and_load_state(self, bip_dir):
        now = datetime.now(timezone.utc).isoformat()
        state = BIPState(
            commits_since_last_post=5,
            tokens_since_last_post=12000,
            interactions_since_last_post=8,
            posts_today=3,
            last_queued_at=now,
        )
        save_state(state, bip_dir)

        loaded = load_state(bip_dir)
        assert loaded.commits_since_last_post == 5
        assert loaded.tokens_since_last_post == 12000
        assert loaded.posts_today == 3
        assert loaded.last_queued_at == now

    def test_load_missing_state_returns_defaults(self, bip_dir):
        state = load_state(bip_dir)
        assert state.commits_since_last_post == 0

    def test_load_corrupt_state_returns_defaults(self, bip_dir):
        Path(bip_dir, "state.json").write_text("{bad json")
        state = load_state(bip_dir)
        assert state.commits_since_last_post == 0

    def test_reset_counters(self, bip_dir):
        state = BIPState(
            commits_since_last_post=10,
            tokens_since_last_post=50000,
            interactions_since_last_post=30,
        )
        save_state(state, bip_dir)

        reset_counters(bip_dir)
        loaded = load_state(bip_dir)
        assert loaded.commits_since_last_post == 0
        assert loaded.tokens_since_last_post == 0
        assert loaded.interactions_since_last_post == 0

    def test_increment_commits(self, bip_dir):
        save_state(BIPState(commits_since_last_post=3), bip_dir)
        increment_counter(bip_dir, "commits_since_last_post", 1)
        loaded = load_state(bip_dir)
        assert loaded.commits_since_last_post == 4

    def test_increment_interactions(self, bip_dir):
        save_state(BIPState(), bip_dir)
        increment_counter(bip_dir, "interactions_since_last_post", 5)
        loaded = load_state(bip_dir)
        assert loaded.interactions_since_last_post == 5

    def test_increment_tokens(self, bip_dir):
        save_state(BIPState(), bip_dir)
        increment_counter(bip_dir, "tokens_since_last_post", 1500)
        loaded = load_state(bip_dir)
        assert loaded.tokens_since_last_post == 1500

    def test_increment_missing_state_file(self, bip_dir):
        increment_counter(bip_dir, "commits_since_last_post", 1)
        loaded = load_state(bip_dir)
        assert loaded.commits_since_last_post == 1


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

class TestCooldown:
    def test_cooldown_not_elapsed(self, bip_dir):
        now = datetime.now(timezone.utc)
        state = BIPState(last_queued_at=now.isoformat())
        save_state(state, bip_dir)
        assert check_cooldown(bip_dir, cooldown_minutes=15) is False

    def test_cooldown_elapsed(self, bip_dir):
        old = datetime.now(timezone.utc) - timedelta(minutes=20)
        state = BIPState(last_queued_at=old.isoformat())
        save_state(state, bip_dir)
        assert check_cooldown(bip_dir, cooldown_minutes=15) is True

    def test_cooldown_no_previous_post(self, bip_dir):
        save_state(BIPState(), bip_dir)
        assert check_cooldown(bip_dir, cooldown_minutes=15) is True

    def test_cooldown_missing_state(self, bip_dir):
        assert check_cooldown(bip_dir, cooldown_minutes=15) is True


# ---------------------------------------------------------------------------
# History / dedup
# ---------------------------------------------------------------------------

class TestHistory:
    def test_empty_history(self, bip_dir):
        history = load_history(bip_dir)
        assert history == []

    def test_record_and_check_history(self, bip_dir):
        record_history(bip_dir, source_key="git:abc123", draft_preview="shipped thing")
        assert is_in_history(bip_dir, "git:abc123") is True
        assert is_in_history(bip_dir, "git:def456") is False

    def test_multiple_entries(self, bip_dir):
        record_history(bip_dir, source_key="git:abc123", draft_preview="first")
        record_history(bip_dir, source_key="correction:001", draft_preview="second")
        history = load_history(bip_dir)
        assert len(history) == 2

    def test_history_includes_timestamp(self, bip_dir):
        record_history(bip_dir, source_key="git:abc123", draft_preview="test")
        history = load_history(bip_dir)
        assert "timestamp" in history[0]

    def test_corrupt_history_returns_empty(self, bip_dir):
        Path(bip_dir, "history.jsonl").write_text("not json\n")
        history = load_history(bip_dir)
        assert history == []

    def test_history_survives_partial_corruption(self, bip_dir):
        record_history(bip_dir, source_key="git:good", draft_preview="ok")
        # Append a bad line
        with open(os.path.join(bip_dir, "history.jsonl"), "a") as f:
            f.write("bad line\n")
        record_history(bip_dir, source_key="git:also_good", draft_preview="ok2")
        history = load_history(bip_dir)
        # Should get at least the valid entries
        keys = [h["source_key"] for h in history]
        assert "git:good" in keys
        assert "git:also_good" in keys


# ---------------------------------------------------------------------------
# Escalation Rules
# ---------------------------------------------------------------------------

class TestEscalationRules:
    def test_plan_implemented_escalates_to_blog(self):
        cfg = BIPConfig()
        action = get_escalation_action("plan_implemented", cfg)
        assert action == "blog_post"

    def test_should_escalate_to_blog_for_plan(self):
        cfg = BIPConfig()
        assert should_escalate_to_blog("plan_implemented", cfg) is True
        assert should_escalate_to_blog("test_green", cfg) is False

    def test_high_signal_event_escalates_to_x_post(self):
        cfg = BIPConfig()
        action = get_escalation_action("test_green", cfg)
        assert action == "x_post"

    def test_unknown_event_returns_none(self):
        cfg = BIPConfig()
        action = get_escalation_action("random_event", cfg)
        assert action is None

    def test_escalation_cooldown_for_x_post(self):
        cfg = BIPConfig(cooldown_minutes=15)
        cooldown = get_escalation_cooldown("x_post", cfg)
        assert cooldown == 900  # 15 min * 60 sec

    def test_custom_escalation_rules(self):
        cfg = BIPConfig(escalation_rules={
            "custom_event": {"action": "x_thread"},
        })
        action = get_escalation_action("custom_event", cfg)
        assert action == "x_thread"

    def test_default_escalation_rules_present(self):
        cfg = BIPConfig()
        assert "plan_implemented" in cfg.escalation_rules
        assert "x_post" in cfg.escalation_rules
        assert "blog_post" in cfg.escalation_rules
