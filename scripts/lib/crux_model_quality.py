"""Model quality tracking — learns from escalation events.

Logs every escalation, tracks success rates per task_type×tier,
and recommends starting tiers based on historical performance.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class EscalationEvent:
    timestamp: float
    task_type: str
    from_tier: str
    to_tier: str
    reason: str
    from_model: str = ""
    to_model: str = ""


@dataclass
class TaskOutcome:
    timestamp: float
    task_type: str
    tier: str
    model: str
    success: bool  # True = no escalation needed


DEFAULT_LOG_DIR = os.path.join(
    os.environ.get("HOME", ""),
    ".crux",
    "model_quality",
)

ADAPTIVE_THRESHOLD = 0.70  # Below this success rate → recommend tier up


def _log_path(log_dir: str, filename: str) -> str:
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, filename)


def log_escalation(
    event: EscalationEvent,
    log_dir: str = DEFAULT_LOG_DIR,
) -> None:
    """Append an escalation event to the JSONL log."""
    path = _log_path(log_dir, "escalations.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(asdict(event)) + "\n")


def log_outcome(
    outcome: TaskOutcome,
    log_dir: str = DEFAULT_LOG_DIR,
) -> None:
    """Append a task outcome to the JSONL log."""
    path = _log_path(log_dir, "outcomes.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(asdict(outcome)) + "\n")


def get_outcomes(
    log_dir: str = DEFAULT_LOG_DIR,
    max_age_days: int = 30,
) -> list[TaskOutcome]:
    """Read recent task outcomes from the log."""
    path = os.path.join(log_dir, "outcomes.jsonl")
    if not os.path.exists(path):
        return []

    cutoff = time.time() - (max_age_days * 86400)
    outcomes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("timestamp", 0) >= cutoff:
                    outcomes.append(TaskOutcome(**data))
            except (json.JSONDecodeError, TypeError):
                continue
    return outcomes


def get_escalations(
    log_dir: str = DEFAULT_LOG_DIR,
    max_age_days: int = 30,
) -> list[EscalationEvent]:
    """Read recent escalation events from the log."""
    path = os.path.join(log_dir, "escalations.jsonl")
    if not os.path.exists(path):
        return []

    cutoff = time.time() - (max_age_days * 86400)
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("timestamp", 0) >= cutoff:
                    events.append(EscalationEvent(**data))
            except (json.JSONDecodeError, TypeError):
                continue
    return events


def get_success_rate(
    task_type: str,
    tier: str,
    log_dir: str = DEFAULT_LOG_DIR,
) -> float | None:
    """What percentage of tasks at this tier succeed without escalation?

    Returns None if no data available (cold start).
    """
    outcomes = get_outcomes(log_dir)
    matching = [o for o in outcomes if o.task_type == task_type and o.tier == tier]
    if not matching:
        return None
    successes = sum(1 for o in matching if o.success)
    return successes / len(matching)


def recommend_tier(
    task_type: str,
    default_tier: str,
    log_dir: str = DEFAULT_LOG_DIR,
) -> str:
    """Based on historical success rates, what tier should this task start at?

    If success rate at default_tier is below ADAPTIVE_THRESHOLD,
    recommends the next tier up.
    """
    from .crux_model_tiers import tier_up

    rate = get_success_rate(task_type, default_tier, log_dir)

    # Cold start — use default
    if rate is None:
        return default_tier

    # Good enough — use default
    if rate >= ADAPTIVE_THRESHOLD:
        return default_tier

    # Below threshold — recommend tier up
    next_tier = tier_up(default_tier)
    if next_tier is None:
        return default_tier  # Already at frontier

    return next_tier


def get_quality_stats(
    log_dir: str = DEFAULT_LOG_DIR,
) -> dict:
    """Get quality statistics for all task_type×tier combinations."""
    outcomes = get_outcomes(log_dir)
    escalations = get_escalations(log_dir)

    # Group outcomes by task_type×tier
    groups: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for o in outcomes:
        groups[o.task_type][o.tier].append(o.success)

    stats: dict[str, dict] = {}
    for task_type, tiers in groups.items():
        stats[task_type] = {}
        for tier, successes in tiers.items():
            total = len(successes)
            success_count = sum(successes)
            stats[task_type][tier] = {
                "total": total,
                "successes": success_count,
                "rate": round(success_count / total, 3) if total > 0 else 0,
            }

    return {
        "stats": stats,
        "total_outcomes": len(outcomes),
        "total_escalations": len(escalations),
    }
