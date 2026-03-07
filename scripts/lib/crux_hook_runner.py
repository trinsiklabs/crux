"""Shell entry point for Crux Claude Code hooks.

Claude Code hooks invoke this via:
    python -m scripts.lib.crux_hook_runner <EventName>

Reads event JSON from stdin, dispatches to crux_hooks handlers,
writes any context output to stdout (for SessionStart/UserPromptSubmit).

Security: PLAN-166 audit - added JSON validation and size limits.
"""

from __future__ import annotations

import json
import os
import sys

# PLAN-166: Maximum allowed JSON input size (1MB)
_MAX_INPUT_SIZE = 1024 * 1024


def _validate_event_data(data: dict) -> bool:
    """Validate event data structure. Returns True if valid."""
    # Must be a dict
    if not isinstance(data, dict):
        return False
    # Must have hook_event_name as string
    event_name = data.get("hook_event_name")
    if not isinstance(event_name, str):
        return False
    # Allowed event types
    if event_name not in ("SessionStart", "PostToolUse", "UserPromptSubmit", "Stop"):
        return False
    return True


def main() -> None:
    project_dir = os.environ.get("CRUX_PROJECT", os.getcwd())
    home = os.environ.get("CRUX_HOME", os.environ.get("HOME", ""))

    # PLAN-166: Limit input size to prevent DoS
    event_json = sys.stdin.read(_MAX_INPUT_SIZE)
    if len(event_json) >= _MAX_INPUT_SIZE:
        print(json.dumps({"status": "error", "error": "Input too large"}), file=sys.stderr)
        sys.exit(1)

    from scripts.lib.crux_hooks import run_hook

    result = run_hook(
        event_json=event_json,
        project_dir=project_dir,
        home=home,
    )

    # For SessionStart, output context so Claude Code adds it to conversation
    if result.get("context"):
        print(result["context"])
    elif result.get("status") == "error":
        print(json.dumps(result), file=sys.stderr)
        sys.exit(1)

    # TDD enforcement: if Stop hook found untested source files, output directive
    if result.get("tdd_compliant") is False and result.get("tdd_warnings"):
        uncovered = result.get("tdd_warnings", [])
        expected = result.get("tdd_expected", [])
        lines = [
            "STOP — TDD VIOLATION DETECTED",
            "",
            "You modified source files without updating their tests.",
            "Write or update the following test files before proceeding:",
            "",
        ]
        for warning in uncovered:
            lines.append(f"  - {warning}")
        if expected:
            lines.append("")
            lines.append("Expected test files:")
            for test_file in expected:
                lines.append(f"  - {test_file}")
        lines.append("")
        lines.append("Do not continue with other work until these tests are written.")
        print("\n".join(lines))


if __name__ == "__main__":  # pragma: no cover
    main()
