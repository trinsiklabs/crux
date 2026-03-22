"""Tests for model quality tracking and adaptive routing."""

import json
import os
import time

import pytest

from scripts.lib.crux_model_quality import (
    ADAPTIVE_THRESHOLD,
    EscalationEvent,
    TaskOutcome,
    get_escalations,
    get_outcomes,
    get_quality_stats,
    get_success_rate,
    log_escalation,
    log_outcome,
    recommend_tier,
)


@pytest.fixture
def log_dir(tmp_path):
    return str(tmp_path / "quality")


# --- Logging ---


def test_log_escalation(log_dir):
    event = EscalationEvent(
        timestamp=time.time(),
        task_type="code_audit",
        from_tier="fast",
        to_tier="standard",
        reason="validation_failure",
        from_model="ollama/qwen3:8b",
        to_model="anthropic/claude-haiku-4-5",
    )
    log_escalation(event, log_dir)

    path = os.path.join(log_dir, "escalations.jsonl")
    assert os.path.exists(path)
    with open(path) as f:
        data = json.loads(f.readline())
    assert data["task_type"] == "code_audit"
    assert data["from_tier"] == "fast"


def test_log_outcome(log_dir):
    outcome = TaskOutcome(
        timestamp=time.time(),
        task_type="code_audit",
        tier="standard",
        model="anthropic/claude-sonnet-4-5",
        success=True,
    )
    log_outcome(outcome, log_dir)

    path = os.path.join(log_dir, "outcomes.jsonl")
    assert os.path.exists(path)


def test_log_multiple(log_dir):
    for i in range(5):
        log_outcome(TaskOutcome(
            timestamp=time.time(),
            task_type="code_audit",
            tier="standard",
            model="m",
            success=i % 2 == 0,
        ), log_dir)

    outcomes = get_outcomes(log_dir)
    assert len(outcomes) == 5


# --- Retrieval ---


def test_get_outcomes_empty(log_dir):
    assert get_outcomes(log_dir) == []


def test_get_escalations_empty(log_dir):
    assert get_escalations(log_dir) == []


def test_get_outcomes_filters_old(log_dir):
    old = TaskOutcome(
        timestamp=time.time() - 86400 * 60,  # 60 days ago
        task_type="t", tier="fast", model="m", success=True,
    )
    recent = TaskOutcome(
        timestamp=time.time(),
        task_type="t", tier="fast", model="m", success=True,
    )
    log_outcome(old, log_dir)
    log_outcome(recent, log_dir)

    results = get_outcomes(log_dir, max_age_days=30)
    assert len(results) == 1


def test_get_escalations_filters_old(log_dir):
    old = EscalationEvent(
        timestamp=time.time() - 86400 * 60,
        task_type="t", from_tier="a", to_tier="b", reason="r",
    )
    recent = EscalationEvent(
        timestamp=time.time(),
        task_type="t", from_tier="a", to_tier="b", reason="r",
    )
    log_escalation(old, log_dir)
    log_escalation(recent, log_dir)

    results = get_escalations(log_dir, max_age_days=30)
    assert len(results) == 1


def test_get_outcomes_handles_corrupt_lines(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "outcomes.jsonl")
    with open(path, "w") as f:
        f.write("not json\n")
        f.write(json.dumps({
            "timestamp": time.time(),
            "task_type": "t", "tier": "fast", "model": "m", "success": True,
        }) + "\n")
        f.write("\n")  # empty line

    results = get_outcomes(log_dir)
    assert len(results) == 1


def test_get_escalations_handles_corrupt(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "escalations.jsonl")
    with open(path, "w") as f:
        f.write("bad\n")
        f.write(json.dumps({
            "timestamp": time.time(),
            "task_type": "t", "from_tier": "a", "to_tier": "b", "reason": "r",
        }) + "\n")

    results = get_escalations(log_dir)
    assert len(results) == 1


# --- Success rate ---


def test_success_rate_no_data(log_dir):
    assert get_success_rate("code_audit", "standard", log_dir) is None


def test_success_rate_all_success(log_dir):
    for _ in range(10):
        log_outcome(TaskOutcome(
            timestamp=time.time(), task_type="code_audit",
            tier="standard", model="m", success=True,
        ), log_dir)

    rate = get_success_rate("code_audit", "standard", log_dir)
    assert rate == 1.0


def test_success_rate_mixed(log_dir):
    for i in range(10):
        log_outcome(TaskOutcome(
            timestamp=time.time(), task_type="code_audit",
            tier="standard", model="m", success=i < 7,
        ), log_dir)

    rate = get_success_rate("code_audit", "standard", log_dir)
    assert rate == 0.7


def test_success_rate_different_task(log_dir):
    log_outcome(TaskOutcome(
        timestamp=time.time(), task_type="doc_audit",
        tier="fast", model="m", success=True,
    ), log_dir)

    assert get_success_rate("code_audit", "fast", log_dir) is None
    assert get_success_rate("doc_audit", "fast", log_dir) == 1.0


# --- Adaptive routing ---


def test_recommend_tier_cold_start(log_dir):
    assert recommend_tier("code_audit", "standard", log_dir) == "standard"


def test_recommend_tier_good_rate(log_dir):
    for _ in range(10):
        log_outcome(TaskOutcome(
            timestamp=time.time(), task_type="code_audit",
            tier="standard", model="m", success=True,
        ), log_dir)

    assert recommend_tier("code_audit", "standard", log_dir) == "standard"


def test_recommend_tier_bad_rate_escalates(log_dir):
    for i in range(10):
        log_outcome(TaskOutcome(
            timestamp=time.time(), task_type="code_audit",
            tier="fast", model="m", success=i < 5,  # 50% rate
        ), log_dir)

    result = recommend_tier("code_audit", "fast", log_dir)
    assert result != "fast"  # Should escalate


def test_recommend_tier_at_frontier(log_dir):
    for i in range(10):
        log_outcome(TaskOutcome(
            timestamp=time.time(), task_type="code_audit",
            tier="frontier", model="m", success=i < 5,
        ), log_dir)

    # Already at frontier, can't go higher
    assert recommend_tier("code_audit", "frontier", log_dir) == "frontier"


# --- Quality stats ---


def test_quality_stats_empty(log_dir):
    stats = get_quality_stats(log_dir)
    assert stats["total_outcomes"] == 0
    assert stats["total_escalations"] == 0


def test_quality_stats_with_data(log_dir):
    for i in range(5):
        log_outcome(TaskOutcome(
            timestamp=time.time(), task_type="code_audit",
            tier="standard", model="m", success=i < 4,
        ), log_dir)
    log_escalation(EscalationEvent(
        timestamp=time.time(), task_type="code_audit",
        from_tier="fast", to_tier="standard", reason="validation",
    ), log_dir)

    stats = get_quality_stats(log_dir)
    assert stats["total_outcomes"] == 5
    assert stats["total_escalations"] == 1
    assert stats["stats"]["code_audit"]["standard"]["total"] == 5
    assert stats["stats"]["code_audit"]["standard"]["rate"] == 0.8
