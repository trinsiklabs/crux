"""LLM-based script auditing for safety pipeline Gates 4-5.

Uses the audit backend abstraction (PLAN-169) for graceful fallback
from Ollama to Claude Code subagent when local LLM is unavailable.
"""

from __future__ import annotations

from scripts.lib.crux_audit_backend import (
    AuditResult,
    get_audit_backend,
    OllamaBackend,
)

DEFAULT_MODEL_8B = "qwen3:8b"
DEFAULT_MODEL_32B = "qwen3:32b"

AUDIT_SYSTEM_PROMPT = (
    "You are a security auditor reviewing bash scripts for vulnerabilities. "
    "Respond with ONLY valid JSON in this format: "
    '{"passed": true/false, "findings": [{"severity": "high|medium|low", '
    '"title": "...", "description": "..."}], "summary": "..."}'
)


def _result_to_dict(result: AuditResult, gate: str) -> dict:
    """Convert AuditResult to legacy dict format for compatibility."""
    return {
        "gate": gate,
        "passed": result.passed,
        "skipped": result.skipped,
        "reason": result.reason if result.skipped else "",
        "findings": [
            {
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
            }
            for f in result.findings
        ],
        "summary": result.summary,
        "model": result.model,
        "backend": result.backend,
    }


def audit_script_8b(
    script_content: str,
    risk_level: str,
    endpoint: str | None = None,
    model: str | None = None,
) -> dict:
    """Gate 4: Adversarial audit using a small (8B) model.

    Uses the best available backend (Ollama preferred, Claude fallback).
    """
    model = model or DEFAULT_MODEL_8B

    # Get the best available backend
    # If Ollama is available with the specified model, use it directly
    # Otherwise, fall back to Claude or disabled
    if endpoint:
        # Explicit endpoint means use Ollama directly
        backend = OllamaBackend(model=model, endpoint=endpoint)
    else:
        backend = get_audit_backend(prefer_ollama_model=model)

    result = backend.audit(
        script_content=script_content,
        risk_level=risk_level,
        system_prompt=AUDIT_SYSTEM_PROMPT,
    )

    return _result_to_dict(result, "audit_8b")


def audit_script_32b(
    script_content: str,
    risk_level: str,
    endpoint: str | None = None,
    model: str | None = None,
) -> dict:
    """Gate 5: Second-opinion audit using a large (32B) model. High-risk only.

    Uses the best available backend (Ollama preferred, Claude fallback).
    """
    if risk_level != "high":
        return {
            "gate": "audit_32b",
            "passed": True,
            "skipped": True,
            "reason": "Not high-risk — 32B audit only runs for high-risk scripts",
            "findings": [],
            "backend": "n/a",
        }

    model = model or DEFAULT_MODEL_32B

    # Get the best available backend
    if endpoint:
        backend = OllamaBackend(model=model, endpoint=endpoint)
    else:
        backend = get_audit_backend(prefer_ollama_model=model)

    result = backend.audit(
        script_content=script_content,
        risk_level=risk_level,
        system_prompt=AUDIT_SYSTEM_PROMPT,
    )

    return _result_to_dict(result, "audit_32b")
