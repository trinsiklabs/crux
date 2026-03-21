"""Model tier system — shared vocabulary for model routing across the Crux ecosystem.

Defines tiers (frontier, standard, fast, local, micro), task→tier mapping,
mode→model mapping, and resolution logic for finding the best available model.

Used by: Crux audit backend, CruxCLI mode integration, CruxDev task router.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Tier definitions — ordered by capability (first = preferred)
# ---------------------------------------------------------------------------

TIERS: dict[str, list[str]] = {
    "frontier": [
        "anthropic/claude-opus-4-5",
        "openai/gpt-5",
        "anthropic/claude-sonnet-4-5",
    ],
    "standard": [
        "anthropic/claude-sonnet-4-5",
        "openai/gpt-5-mini",
        "ollama/qwen3-coder:30b",
        "ollama/qwen3.5:27b",
    ],
    "fast": [
        "anthropic/claude-haiku-4-5",
        "openai/gpt-5-nano",
        "ollama/qwen3.5:27b",
        "ollama/qwen3:8b",
    ],
    "local": [
        "ollama/qwen3-coder:30b",
        "ollama/qwen3.5:27b",
    ],
    "micro": [
        "ollama/qwen3:8b",
        "ollama/qwen3:4b",
    ],
}

TIER_ORDER = ["micro", "fast", "local", "standard", "frontier"]


# ---------------------------------------------------------------------------
# Task→tier routing
# ---------------------------------------------------------------------------

TASK_ROUTING: dict[str, str] = {
    "plan_audit": "fast",
    "code_audit": "standard",
    "security_audit": "frontier",
    "doc_audit": "fast",
    "fix_generation": "standard",
    "independence": "fast",
    "title": "micro",
    "compaction": "fast",
    "write": "standard",
    "e2e_test": "fast",
}


# ---------------------------------------------------------------------------
# Mode→tier mapping
# ---------------------------------------------------------------------------

MODE_TIERS: dict[str, dict[str, str]] = {
    # Code modes — local for primary, fast for audit
    "build-py": {"primary": "local", "audit": "fast"},
    "build-ex": {"primary": "local", "audit": "fast"},
    "docker": {"primary": "local", "audit": "fast"},
    "test": {"primary": "local", "audit": "fast"},
    "design-ui": {"primary": "local", "audit": "fast"},
    "design-system": {"primary": "local", "audit": "fast"},
    "design-responsive": {"primary": "local", "audit": "fast"},
    # Think modes — fast for primary, standard for audit
    "plan": {"primary": "fast", "audit": "standard"},
    "infra-architect": {"primary": "fast", "audit": "standard"},
    "review": {"primary": "standard", "audit": "standard"},
    "debug": {"primary": "standard", "audit": "standard"},
    "security": {"primary": "standard", "audit": "frontier"},
    "design-review": {"primary": "standard", "audit": "standard"},
    "design-accessibility": {"primary": "standard", "audit": "standard"},
    # Chat modes — fast is fine
    "writer": {"primary": "fast"},
    "analyst": {"primary": "fast"},
    "explain": {"primary": "fast"},
    "mac": {"primary": "fast"},
    "ai-infra": {"primary": "fast"},
    "marketing": {"primary": "fast"},
    "build-in-public": {"primary": "fast"},
    # Meta modes
    "legal": {"primary": "standard"},
    "strategist": {"primary": "standard"},
    "psych": {"primary": "fast"},
}


# ---------------------------------------------------------------------------
# Resolution logic
# ---------------------------------------------------------------------------


def _parse_model(model_str: str) -> tuple[str, str]:
    """Split 'provider/model' into (provider, model). If no /, provider is 'ollama'."""
    if "/" in model_str:
        parts = model_str.split("/", 1)
        return parts[0], parts[1]
    return "ollama", model_str


def _provider_available(provider: str) -> bool:
    """Check if a provider's credentials are available."""
    if provider == "ollama":
        return True  # Assume local Ollama is available (health check is separate)
    if provider == "anthropic":
        return bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("CRUX_ANTHROPIC_API_KEY")
        )
    if provider == "openai":
        return bool(
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("CRUX_OPENAI_API_KEY")
        )
    return False


def resolve_tier(
    tier: str,
    available_providers: list[str] | None = None,
) -> str | None:
    """Given a tier name, return the best available model (provider/model format).

    If available_providers is None, auto-detects from environment.
    """
    if tier not in TIERS:
        return None

    if available_providers is None:
        available_providers = [p for p in ["ollama", "anthropic", "openai"] if _provider_available(p)]

    for model in TIERS[tier]:
        provider, _ = _parse_model(model)
        if provider in available_providers:
            return model

    return None


def get_task_model(
    task_type: str,
    available_providers: list[str] | None = None,
) -> str | None:
    """Given a task type, return the recommended model.

    Uses TASK_ROUTING to determine the tier, then resolves to a concrete model.
    """
    tier = TASK_ROUTING.get(task_type)
    if tier is None:
        return None
    return resolve_tier(tier, available_providers)


def get_mode_model(
    mode: str,
    role: str = "primary",
    available_providers: list[str] | None = None,
) -> str | None:
    """Given a mode and role (primary/audit), return the recommended model."""
    mode_config = MODE_TIERS.get(mode)
    if mode_config is None:
        return None
    tier = mode_config.get(role)
    if tier is None:
        return None
    return resolve_tier(tier, available_providers)


def tier_up(current_tier: str) -> str | None:
    """Get the next tier up. Returns None if already at frontier."""
    if current_tier not in TIER_ORDER:
        return None
    idx = TIER_ORDER.index(current_tier)
    if idx + 1 >= len(TIER_ORDER):
        return None
    return TIER_ORDER[idx + 1]


def tier_down(current_tier: str) -> str | None:
    """Get the next tier down. Returns None if already at micro."""
    if current_tier not in TIER_ORDER:
        return None
    idx = TIER_ORDER.index(current_tier)
    if idx <= 0:
        return None
    return TIER_ORDER[idx - 1]


def get_tier_for_model(model: str) -> str | None:
    """Find which tier a model belongs to (returns highest tier)."""
    for tier_name in reversed(TIER_ORDER):
        if model in TIERS[tier_name]:
            return tier_name
    return None


def get_available_tiers(
    available_providers: list[str] | None = None,
) -> dict[str, str | None]:
    """Show what's available at each tier."""
    return {
        tier: resolve_tier(tier, available_providers)
        for tier in TIER_ORDER
    }
