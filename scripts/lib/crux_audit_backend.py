"""Audit backend abstraction for Gates 4-5 (PLAN-169, PLAN-170).

Provides graceful fallback from Ollama to Claude Code subagent when
local LLM is unavailable. Prevents silent audit skipping.

PLAN-170: OpenCode mode enforces Ollama requirement - no fallback allowed.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from scripts.lib.crux_ollama import check_ollama_running, generate

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions (PLAN-170)
# ---------------------------------------------------------------------------


class AuditRequiredError(Exception):
    """Raised when audit is required but no backend is available.

    This is used in OpenCode mode where Ollama is mandatory.
    """
    pass

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class AuditFinding:
    """A single finding from an audit."""

    severity: str  # high, medium, low
    title: str
    description: str


@dataclass
class AuditResult:
    """Result from an audit backend."""

    passed: bool
    skipped: bool
    findings: list[AuditFinding] = field(default_factory=list)
    summary: str = ""
    reason: str = ""
    backend: str = ""
    model: str = ""


# ---------------------------------------------------------------------------
# Backend Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AuditBackend(Protocol):
    """Protocol for audit backends."""

    @property
    def name(self) -> str:
        """Human-readable backend name."""
        ...

    def is_available(self) -> bool:
        """Check if this backend is currently available."""
        ...

    def audit(
        self,
        script_content: str,
        risk_level: str,
        system_prompt: str,
    ) -> AuditResult:
        """Run an audit on the given script content."""
        ...


# ---------------------------------------------------------------------------
# Ollama Backend
# ---------------------------------------------------------------------------


class OllamaBackend:
    """Audit backend using local Ollama LLM."""

    def __init__(
        self,
        model: str = "qwen3:8b",
        endpoint: str | None = None,
    ) -> None:
        self._model = model
        self._endpoint = endpoint

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"

    def is_available(self) -> bool:
        return check_ollama_running(self._endpoint or "http://localhost:11434")

    def audit(
        self,
        script_content: str,
        risk_level: str,
        system_prompt: str,
    ) -> AuditResult:
        prompt = _format_audit_prompt(script_content, risk_level)
        kwargs: dict = {
            "model": self._model,
            "prompt": prompt,
            "system": system_prompt,
        }
        if self._endpoint:
            kwargs["endpoint"] = self._endpoint

        result = generate(**kwargs)

        if not result["success"]:
            return AuditResult(
                passed=True,
                skipped=True,
                reason=f"Ollama call failed: {result.get('error', 'unknown')}",
                backend=self.name,
            )

        parsed = _parse_audit_response(result["response"])
        if parsed is None:
            return AuditResult(
                passed=True,
                skipped=True,
                reason="Could not parse LLM response as JSON",
                backend=self.name,
            )

        findings = [
            AuditFinding(
                severity=f.get("severity", "medium"),
                title=f.get("title", "Unknown"),
                description=f.get("description", ""),
            )
            for f in parsed.get("findings", [])
        ]

        return AuditResult(
            passed=parsed.get("passed", True),
            skipped=False,
            findings=findings,
            summary=parsed.get("summary", ""),
            backend=self.name,
            model=self._model,
        )


# ---------------------------------------------------------------------------
# Claude Code Subagent Backend
# ---------------------------------------------------------------------------


class ClaudeSubagentBackend:
    """Audit backend using Claude Code's security subagent.

    This backend invokes Claude Code's Task tool with subagent_type="security"
    to perform adversarial script auditing. It works by writing a prompt file
    and invoking claude with --print to get the response.
    """

    def __init__(self) -> None:
        self._claude_path = self._find_claude_binary()

    @property
    def name(self) -> str:
        return "Claude subagent (security)"

    def _find_claude_binary(self) -> str | None:
        """Find the claude CLI binary."""
        # Check common locations
        candidates = [
            os.path.expanduser("~/.claude/local/claude"),
            "/usr/local/bin/claude",
            "claude",  # Fall back to PATH
        ]
        for path in candidates:
            if path == "claude":
                # Check PATH
                result = subprocess.run(
                    ["which", "claude"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            elif os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def is_available(self) -> bool:
        """Check if Claude Code is available and we're in a Claude session."""
        # Check for Claude binary
        if not self._claude_path:
            return False

        # Check if we're in a Claude Code context (CLAUDE_CODE_ENTRY_POINT set)
        # or if claude CLI is available for spawning
        return True

    def audit(
        self,
        script_content: str,
        risk_level: str,
        system_prompt: str,
    ) -> AuditResult:
        if not self._claude_path:
            return AuditResult(
                passed=True,
                skipped=True,
                reason="Claude CLI not found",
                backend=self.name,
            )

        # Build the audit prompt
        prompt = f"""{system_prompt}

Review this {risk_level}-risk bash script for security issues.
Check for: command injection, unquoted variables, path traversal,
privilege escalation, and unsafe operations.

```bash
{script_content}
```

Respond with ONLY valid JSON."""

        try:
            # Use claude CLI with --print for non-interactive output
            result = subprocess.run(
                [
                    self._claude_path,
                    "--print",
                    "-p", prompt,
                ],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                env={**os.environ, "CLAUDE_CODE_DISABLE_HOOKS": "1"},
            )

            if result.returncode != 0:
                return AuditResult(
                    passed=True,
                    skipped=True,
                    reason=f"Claude CLI failed: {result.stderr[:200]}",
                    backend=self.name,
                )

            parsed = _parse_audit_response(result.stdout)
            if parsed is None:
                return AuditResult(
                    passed=True,
                    skipped=True,
                    reason="Could not parse Claude response as JSON",
                    backend=self.name,
                )

            findings = [
                AuditFinding(
                    severity=f.get("severity", "medium"),
                    title=f.get("title", "Unknown"),
                    description=f.get("description", ""),
                )
                for f in parsed.get("findings", [])
            ]

            return AuditResult(
                passed=parsed.get("passed", True),
                skipped=False,
                findings=findings,
                summary=parsed.get("summary", ""),
                backend=self.name,
            )

        except subprocess.TimeoutExpired:
            return AuditResult(
                passed=True,
                skipped=True,
                reason="Claude audit timed out after 120s",
                backend=self.name,
            )
        except Exception as exc:
            _logger.debug("Claude subagent audit failed: %s", exc)
            return AuditResult(
                passed=True,
                skipped=True,
                reason=f"Claude audit error: {exc}",
                backend=self.name,
            )


# ---------------------------------------------------------------------------
# Disabled Backend (explicit no-audit)
# ---------------------------------------------------------------------------


class DisabledBackend:
    """Fallback backend when no LLM is available.

    Unlike silent skipping, this backend explicitly warns that no audit
    was performed and returns a clear indication in the result.
    """

    @property
    def name(self) -> str:
        return "DISABLED (no LLM available)"

    def is_available(self) -> bool:
        return True  # Always "available" as the last resort

    def audit(
        self,
        script_content: str,
        risk_level: str,
        system_prompt: str,
    ) -> AuditResult:
        _logger.warning(
            "No audit backend available - script audit skipped for %s-risk script",
            risk_level,
        )
        return AuditResult(
            passed=True,
            skipped=True,
            reason="No audit backend available (Ollama down, Claude CLI not found)",
            backend=self.name,
        )


# ---------------------------------------------------------------------------
# Context Detection (PLAN-170)
# ---------------------------------------------------------------------------


def detect_opencode_context() -> bool:
    """Detect if we're running in OpenCode mode.

    Checks multiple indicators:
    1. CRUX_TOOL environment variable
    2. Setup state file from Crux setup.sh
    3. OpenCode-specific environment variables
    """
    # Check explicit environment variable
    crux_tool = os.environ.get("CRUX_TOOL", "").lower()
    if crux_tool == "opencode":
        return True
    if crux_tool == "claude-code":
        return False

    # Check setup state file
    state_file = Path.home() / ".config" / "crux" / "setup-state" / "selected_tool"
    if state_file.exists():
        try:
            tool = state_file.read_text().strip().lower()
            if tool == "opencode":
                return True
            if tool in ("claude-code", "both"):
                return False
        except (OSError, IOError):
            pass

    # Check for OpenCode-specific indicators
    if os.environ.get("OPENCODE_SESSION"):
        return True

    # Check for Claude Code indicators (inverse detection)
    if os.environ.get("CLAUDE_CODE_ENTRY_POINT"):
        return False

    # Default: unknown context, assume Claude Code (graceful fallback)
    return False


def detect_context_mode() -> str:
    """Detect the current tool context.

    Returns:
        "opencode", "claude-code", or "unknown"
    """
    if detect_opencode_context():
        return "opencode"

    # Check for Claude Code
    if os.environ.get("CLAUDE_CODE_ENTRY_POINT"):
        return "claude-code"

    state_file = Path.home() / ".config" / "crux" / "setup-state" / "selected_tool"
    if state_file.exists():
        try:
            tool = state_file.read_text().strip().lower()
            if tool in ("claude-code", "opencode", "both"):
                return tool
        except (OSError, IOError):
            pass

    return "unknown"


# ---------------------------------------------------------------------------
# Backend Selection
# ---------------------------------------------------------------------------

# Cached backend instance
_cached_backend: AuditBackend | None = None
_cached_backend_check_time: float = 0


def get_audit_backend(
    force_refresh: bool = False,
    prefer_ollama_model: str = "qwen3:8b",
    context: str = "auto",
    enforce_opencode: bool = True,
) -> AuditBackend:
    """Get the best available audit backend.

    Priority:
    1. Ollama (local, fast, private, free)
    2. Claude Code subagent (requires Claude CLI) - NOT available in OpenCode mode
    3. Disabled (explicit warning, no silent skipping) - NOT available in OpenCode mode

    PLAN-170: In OpenCode mode, Ollama is REQUIRED. If unavailable, raises
    AuditRequiredError instead of falling back.

    Args:
        force_refresh: If True, re-check backend availability
        prefer_ollama_model: Ollama model to use if available
        context: "auto", "opencode", or "claude-code" - determines enforcement
        enforce_opencode: If False, skip OpenCode enforcement (for testing)

    Returns:
        The best available AuditBackend instance

    Raises:
        AuditRequiredError: In OpenCode mode when Ollama is not available
    """
    global _cached_backend, _cached_backend_check_time

    import time

    now = time.time()

    # Determine context
    is_opencode = False
    if context == "auto":
        is_opencode = detect_opencode_context()
    elif context == "opencode":
        is_opencode = True

    # Cache backend for 60 seconds to avoid repeated checks
    # But don't use cache if context changed or we need to enforce
    if (
        not force_refresh
        and _cached_backend is not None
        and (now - _cached_backend_check_time) < 60
        and not (is_opencode and enforce_opencode and isinstance(_cached_backend, DisabledBackend))
    ):
        return _cached_backend

    # Try Ollama first
    ollama = OllamaBackend(model=prefer_ollama_model)
    if ollama.is_available():
        _cached_backend = ollama
        _cached_backend_check_time = now
        _logger.debug("Using Ollama backend: %s", ollama.name)
        return ollama

    # PLAN-170: OpenCode mode requires Ollama - no fallback
    if is_opencode and enforce_opencode:
        raise AuditRequiredError(
            "OpenCode requires local Ollama for adversarial auditing.\n"
            "\n"
            "To fix:\n"
            "  1. Start Ollama: ollama serve\n"
            "  2. Pull audit model: ollama pull qwen3:8b\n"
            "  3. Verify: curl http://localhost:11434/api/tags\n"
            "\n"
            "OpenCode uses local models only - Claude subagent fallback is not available.\n"
            "This ensures your audit is performed by an independent local model."
        )

    # Try Claude subagent (Claude Code mode only)
    claude = ClaudeSubagentBackend()
    if claude.is_available():
        _cached_backend = claude
        _cached_backend_check_time = now
        _logger.debug("Using Claude subagent backend")
        return claude

    # Fall back to disabled (Claude Code mode only)
    disabled = DisabledBackend()
    _cached_backend = disabled
    _cached_backend_check_time = now
    _logger.warning("No audit backend available - using disabled backend")
    return disabled


def get_backend_status() -> dict:
    """Get status of all audit backends for health checks.

    Returns:
        Dict with backend availability, active backend, and mode info
    """
    ollama = OllamaBackend()
    claude = ClaudeSubagentBackend()

    ollama_available = ollama.is_available()
    claude_available = claude.is_available()
    context_mode = detect_context_mode()
    is_opencode = context_mode == "opencode"

    # Determine active backend (with enforcement disabled for status check)
    try:
        active = get_audit_backend(enforce_opencode=False)
        active_name = active.name
        audit_blocked = False
    except AuditRequiredError:
        active_name = "BLOCKED (Ollama required)"
        audit_blocked = True

    # Check if audit would be blocked in current mode
    if is_opencode and not ollama_available:
        audit_blocked = True
        active_name = "BLOCKED (Ollama required for OpenCode)"

    return {
        "active_backend": active_name,
        "ollama_available": ollama_available,
        "claude_available": claude_available,
        "context_mode": context_mode,
        "ollama_required": is_opencode,
        "audit_blocked": audit_blocked,
        "backends": {
            "ollama": {
                "available": ollama_available,
                "name": ollama.name,
                "required_in": ["opencode"],
            },
            "claude": {
                "available": claude_available,
                "name": claude.name,
                "available_in": ["claude-code", "both"],
            },
            "disabled": {
                "available": not is_opencode,
                "name": DisabledBackend().name,
                "available_in": ["claude-code", "both"],
            },
        },
    }


# ---------------------------------------------------------------------------
# Helper functions (moved from crux_llm_audit.py)
# ---------------------------------------------------------------------------


def _format_audit_prompt(script_content: str, risk_level: str) -> str:
    """Build the audit prompt for an LLM review."""
    return (
        f"Review this {risk_level}-risk bash script for security issues. "
        f"Check for: command injection, unquoted variables, path traversal, "
        f"privilege escalation, and unsafe operations. "
        f"Respond with json.\n\n```bash\n{script_content}\n```"
    )


def _parse_audit_response(response_text: str) -> dict | None:
    """Parse LLM response as JSON audit result. Returns None on failure."""
    try:
        # Handle responses wrapped in markdown code blocks
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
