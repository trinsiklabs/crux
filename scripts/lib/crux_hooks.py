"""Claude Code hook handlers for Crux integration.

Handles events from Claude Code's hooks system:
- SessionStart: inject Crux context (mode prompt, session state, pending tasks)
- PostToolUse: track files touched, log all tool interactions
- UserPromptSubmit: detect corrections in user messages
- Stop: update session timestamps and interaction counts

Each handler receives parsed event data and returns a result dict.
The run_hook() function dispatches stdin JSON to the correct handler.

Security: PLAN-166 audit - fixes for path traversal, injection, and error handling.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path

# Security: Configure logging for audit trail (PLAN-166)
_logger = logging.getLogger("crux.hooks")


# ---------------------------------------------------------------------------
# Security validation functions (PLAN-166)
# ---------------------------------------------------------------------------

# Allowed characters for mode names, filenames, etc.
_SAFE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')


def _is_safe_name(name: str) -> bool:
    """Validate name contains only safe characters (no path traversal)."""
    if not name or len(name) > 128:
        return False
    if '..' in name or '/' in name or '\\' in name:
        return False
    return bool(_SAFE_NAME_PATTERN.match(name))


def _is_safe_path(path: str, allowed_base: str) -> bool:
    """Validate path stays within allowed_base directory."""
    try:
        # Resolve to absolute, canonical path
        resolved = Path(path).resolve()
        base_resolved = Path(allowed_base).resolve()
        # Check path is under base
        return str(resolved).startswith(str(base_resolved) + os.sep) or resolved == base_resolved
    except (ValueError, OSError):
        return False


# ---------------------------------------------------------------------------
# Input length limits (PLAN-166 - prevent DoS via oversized inputs)
# ---------------------------------------------------------------------------

_MAX_PROMPT_LENGTH = 100 * 1024  # 100KB
_MAX_PATH_LENGTH = 1024  # 1KB
_MAX_TOOL_INPUT_SIZE = 100 * 1024  # 100KB for serialized tool_input


def _truncate_for_safety(value: str, max_length: int) -> str:
    """Truncate a string if it exceeds max_length."""
    if len(value) > max_length:
        return value[:max_length] + "...[TRUNCATED]"
    return value


# ---------------------------------------------------------------------------
# Sensitive data sanitization (PLAN-166)
# ---------------------------------------------------------------------------

_SENSITIVE_KEYS = frozenset({
    'password', 'passwd', 'pwd',
    'token', 'access_token', 'refresh_token', 'bearer',
    'secret', 'client_secret',
    'api_key', 'apikey', 'api-key',
    'credential', 'credentials',
    'auth', 'authorization',
    'private_key', 'privatekey',
    'ssh_key', 'sshkey',
})

# Patterns for detecting secrets in string values
_SECRET_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Long alphanumeric strings (API keys)
    re.compile(r'sk-[A-Za-z0-9]{20,}'),  # OpenAI-style keys
    re.compile(r'ghp_[A-Za-z0-9]{36,}'),  # GitHub personal access tokens
    re.compile(r'github_pat_[A-Za-z0-9_]{20,}'),  # GitHub fine-grained PAT
    re.compile(r'xox[baprs]-[A-Za-z0-9\-]{10,}'),  # Slack tokens
    re.compile(r'-----BEGIN [A-Z ]+ KEY-----'),  # PEM keys
]


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates sensitive data."""
    key_lower = key.lower().replace('-', '_')
    return any(sensitive in key_lower for sensitive in _SENSITIVE_KEYS)


def _sanitize_value(value: str) -> str:
    """Redact potential secrets from a string value."""
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub('[REDACTED]', value)
    return value


def _sanitize_dict(data: dict, depth: int = 0) -> dict:
    """Recursively sanitize a dictionary, redacting sensitive values.

    PLAN-166: Prevents logging of passwords, tokens, API keys, etc.
    """
    if depth > 10:  # Prevent infinite recursion
        return {"[TRUNCATED]": "max depth exceeded"}

    sanitized = {}
    for key, value in data.items():
        if _is_sensitive_key(str(key)):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value, depth + 1)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_dict(v, depth + 1) if isinstance(v, dict)
                else _sanitize_value(str(v)) if isinstance(v, str)
                else v
                for v in value
            ]
        elif isinstance(value, str):
            sanitized[key] = _sanitize_value(value)
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_prompt(prompt: str) -> str:
    """Sanitize a user prompt, redacting potential secrets.

    PLAN-166: Prevents logging of API keys, passwords in prompts.
    """
    # Apply length limit first to prevent ReDoS
    if len(prompt) > _MAX_PROMPT_LENGTH:
        prompt = prompt[:_MAX_PROMPT_LENGTH] + "...[TRUNCATED]"

    # Redact detected secret patterns
    return _sanitize_value(prompt)

from scripts.lib.crux_paths import get_project_paths, get_user_paths
from scripts.lib.crux_session import load_session, save_session, update_session


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Correction detection patterns
# ---------------------------------------------------------------------------

_CORRECTION_PATTERNS = [
    re.compile(r"\bno[,.]?\s+(that'?s?\s+)?(wrong|not right|incorrect)", re.IGNORECASE),
    re.compile(r"\bno[,.]?\s+(use|do|try|make)\b", re.IGNORECASE),
    re.compile(r"\bactually[,.]?\s+(do|use|try|make)", re.IGNORECASE),
    re.compile(r"\bwrong[,.]?\s+(use|do|try)", re.IGNORECASE),
    re.compile(r"\bI said\b", re.IGNORECASE),
    re.compile(r"\bthat'?s\s+incorrect\b", re.IGNORECASE),
    re.compile(r"\bstop[,.]?\s+you'?re\s+(doing it\s+)?wrong\b", re.IGNORECASE),
    re.compile(r"\bnot like that\b", re.IGNORECASE),
    re.compile(r"\binstead\s*$", re.IGNORECASE),
    re.compile(r"\bdo it this way\b", re.IGNORECASE),
]


_MAX_REGEX_INPUT_LENGTH = 10 * 1024  # 10KB max for regex matching (ReDoS prevention)


def _is_correction(text: str) -> bool:
    """Check if a user prompt contains a correction.

    PLAN-166: Limits input length to prevent ReDoS attacks.
    """
    if not text.strip():
        return False
    # Limit input length to prevent ReDoS (PLAN-166)
    search_text = text[:_MAX_REGEX_INPUT_LENGTH] if len(text) > _MAX_REGEX_INPUT_LENGTH else text
    return any(p.search(search_text) for p in _CORRECTION_PATTERNS)


# ---------------------------------------------------------------------------
# Interaction logging
# ---------------------------------------------------------------------------

def _log_interaction(tool_name: str, tool_input: dict, project_dir: str) -> None:
    """Append a tool interaction to today's JSONL log.

    PLAN-166: Sanitizes tool_input to redact sensitive data.
    """
    paths = get_project_paths(project_dir)
    log_dir = os.path.join(str(paths.root), "analytics", "interactions")
    # PLAN-166: Create directories with restricted permissions
    os.makedirs(log_dir, mode=0o700, exist_ok=True)

    log_file = os.path.join(log_dir, f"{_today()}.jsonl")

    # PLAN-166: Sanitize tool_input to redact sensitive data
    sanitized_input = _sanitize_dict(tool_input) if isinstance(tool_input, dict) else {}

    entry = {
        "timestamp": _now_iso(),
        "tool_name": tool_name,
        "tool_input": sanitized_input,
    }

    # PLAN-166: Write with restricted permissions (mode 0o600)
    # Use os.open to set file permissions atomically on creation
    fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, (json.dumps(entry) + "\n").encode('utf-8'))
    finally:
        os.close(fd)


def _log_conversation(
    role: str,
    content: str,
    project_dir: str,
    mode: str | None = None,
    tool: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Append a conversation message to today's conversations JSONL log.

    PLAN-166: Sanitizes content to redact sensitive data.
    """
    paths = get_project_paths(project_dir)
    log_dir = os.path.join(str(paths.root), "analytics", "conversations")
    # PLAN-166: Create directories with restricted permissions
    os.makedirs(log_dir, mode=0o700, exist_ok=True)

    log_file = os.path.join(log_dir, f"{_today()}.jsonl")

    # PLAN-166: Sanitize content to redact potential secrets
    sanitized_content = _sanitize_prompt(content)

    entry: dict = {
        "timestamp": _now_iso(),
        "role": role,
        "content": sanitized_content,
        "mode": mode,
        "tool": tool,
    }
    if metadata:
        # PLAN-166: Sanitize metadata as well
        entry["metadata"] = _sanitize_dict(metadata) if isinstance(metadata, dict) else metadata

    # PLAN-166: Write with restricted permissions (mode 0o600)
    fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, (json.dumps(entry) + "\n").encode('utf-8'))
    finally:
        os.close(fd)


def _count_interactions(project_dir: str) -> int:
    """Count total interactions logged today."""
    paths = get_project_paths(project_dir)
    log_dir = os.path.join(str(paths.root), "analytics", "interactions")
    log_file = os.path.join(log_dir, f"{_today()}.jsonl")
    if not os.path.exists(log_file):
        return 0
    with open(log_file) as f:
        return sum(1 for _ in f)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TDD compliance checker
# ---------------------------------------------------------------------------

# Maps source file patterns to their expected test file pattern templates.
# Templates use \1, \2 etc. for backreferences from the source match.
# A source file is "covered" if ANY of its test patterns match a touched file.
# Files that match source patterns but don't need tests
_SOURCE_EXCLUDES: list[re.Pattern[str]] = [
    re.compile(r"__init__\.py$"),
]

_SOURCE_TEST_MAP: list[tuple[re.Pattern[str], list[str]]] = [
    # Python with crux_ prefix: also match test files without the prefix
    # e.g. crux_mcp_handlers.py → test_crux_mcp_handlers.py OR test_mcp_handlers*.py
    (
        re.compile(r"^scripts/lib/crux_(\w+)\.py$"),
        [r"^tests/test_crux_\1\.py$", r"^tests/test_\1\w*\.py$"],
    ),
    # Python without crux_ prefix: exact match or partial
    (
        re.compile(r"^scripts/lib/(\w+)\.py$"),
        [r"^tests/test_\1\.py$", r"^tests/test_\1\w*\.py$"],
    ),
    # setup.sh → any tests/setup_*.bats
    (
        re.compile(r"^setup\.sh$"),
        [r"^tests/setup_\w+\.bats$"],
    ),
    # bin/crux → tests/crux_cli.bats
    (
        re.compile(r"^bin/crux$"),
        [r"^tests/crux_cli\.bats$"],
    ),
    # JS plugins: plugins/*.js → tests/plugins*.test.js
    (
        re.compile(r"^plugins/[\w.-]+\.js$"),
        [r"^tests/plugins[\w_]*\.test\.js$"],
    ),
    # JS tools: tools/*.js → tests/tools*.test.js
    (
        re.compile(r"^tools/[\w.-]+\.js$"),
        [r"^tests/tools[\w_]*\.test\.js$"],
    ),
]


def _normalize_path(file_path: str) -> str:
    """Strip common project root prefixes to get a repo-relative path."""
    # Handle absolute paths by finding known repo markers
    for marker in ("scripts/lib/", "tests/", "plugins/", "tools/", "bin/", "setup.sh"):
        idx = file_path.find(marker)
        if idx > 0:
            return file_path[idx:]
    # If it's already relative or doesn't match, return basename-stripped
    return file_path.lstrip("/")


def _expected_test_path(source_path: str, match: re.Match, templates: list[str]) -> str:
    """Build a human-readable expected test file path from the first template."""
    concrete = templates[0]
    for i, group in enumerate(match.groups(), 1):
        concrete = concrete.replace(f"\\{i}", group if group else "")
    # Strip regex anchors and convert regex patterns to readable paths
    readable = concrete.lstrip("^").rstrip("$")
    # Remove optional groups like (crux_)?
    readable = re.sub(r"\([^)]*\)\?", "", readable)
    # Convert character classes and quantifiers to glob-like hints
    readable = re.sub(r"\\w[*+]", "*", readable)
    readable = re.sub(r"\[[^\]]*\][*+?]?", "*", readable)
    readable = readable.replace(r"\.", ".")
    # Clean up double-stars or trailing stars before extension
    readable = re.sub(r"\*+", "*", readable)
    return readable


def check_tdd_compliance(files_touched: list[str]) -> dict:
    """Check whether source files have corresponding test files in the list.

    Returns a dict with:
      - compliant: bool — True if all source files have test coverage
      - warnings: list[str] — human-readable warnings for uncovered files
      - uncovered_sources: list[str] — source files without test coverage
      - expected_tests: list[str] — test files that should have been modified
    """
    if not files_touched:
        return {
            "compliant": True,
            "warnings": [],
            "uncovered_sources": [],
            "expected_tests": [],
        }

    normalized = [_normalize_path(f) for f in files_touched]
    test_files = [f for f in normalized if f.startswith("tests/")]
    uncovered: list[str] = []
    expected_tests: list[str] = []

    for norm_path in normalized:
        if any(exc.search(norm_path) for exc in _SOURCE_EXCLUDES):
            continue
        for source_pattern, test_templates in _SOURCE_TEST_MAP:
            m = source_pattern.match(norm_path)
            if m:
                # This is a source file — check if any test pattern matches
                covered = False
                for template in test_templates:
                    # Substitute backreferences from the source match
                    concrete = template
                    for i, group in enumerate(m.groups(), 1):
                        concrete = concrete.replace(f"\\{i}", group)
                    concrete_re = re.compile(concrete)
                    if any(concrete_re.match(tf) for tf in test_files):
                        covered = True
                        break
                if not covered:
                    uncovered.append(norm_path)
                    expected_tests.append(
                        _expected_test_path(norm_path, m, test_templates)
                    )
                break  # Only match first source pattern

    warnings = [
        f"TDD: {src} was modified without a corresponding test file"
        for src in uncovered
    ]

    return {
        "compliant": len(uncovered) == 0,
        "warnings": warnings,
        "uncovered_sources": uncovered,
        "expected_tests": expected_tests,
    }


def handle_session_start(
    event_data: dict,
    project_dir: str,
    home: str,
) -> dict:
    """Handle SessionStart event — inject Crux context."""
    crux_dir = os.path.join(project_dir, ".crux")
    # Hooks only fire inside Claude Code — auto-detect the active tool
    update_session(project_crux_dir=crux_dir, active_tool="claude-code")
    state = load_session(crux_dir)
    user_paths = get_user_paths(home)

    parts: list[str] = []

    # Mode prompt (PLAN-166: validate mode name to prevent path traversal)
    if _is_safe_name(state.active_mode):
        mode_file = os.path.join(user_paths.modes, f"{state.active_mode}.md")
        # Additional check: ensure resolved path stays within modes directory
        if _is_safe_path(mode_file, user_paths.modes) and os.path.exists(mode_file):
            with open(mode_file) as f:
                parts.append(f"## Active Mode: {state.active_mode}\n{f.read()}")
    else:
        _logger.warning(f"Unsafe mode name rejected: {state.active_mode!r}")

    # Session state
    parts.append(f"## Session State")
    parts.append(f"- Mode: {state.active_mode}")
    parts.append(f"- Tool: {state.active_tool}")
    if state.working_on:
        parts.append(f"- Working on: {state.working_on}")

    # Pending tasks
    if state.pending:
        parts.append("\n## Pending Tasks")
        for task in state.pending:
            parts.append(f"- {task}")

    # Key decisions
    if state.key_decisions:
        parts.append(f"\n## Key Decisions ({len(state.key_decisions)} total)")
        for d in state.key_decisions[-5:]:  # last 5
            parts.append(f"- {d}")

    context = "\n".join(parts)
    return {"status": "ok", "context": context}


_PROCESSOR_CHECK_INTERVAL = 50


def handle_post_tool_use(
    event_data: dict,
    project_dir: str,
    home: str,
) -> dict:
    """Handle PostToolUse — track files, log interactions, periodic processor check.

    PLAN-166: Validates input lengths and sanitizes logged data.
    """
    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input", {})
    crux_dir = os.path.join(project_dir, ".crux")

    # PLAN-166: Validate input types and lengths
    if not isinstance(tool_name, str) or len(tool_name) > 256:
        return {"status": "error", "message": "Invalid tool_name"}
    if not isinstance(tool_input, dict):
        tool_input = {}

    result: dict = {"status": "ok"}

    # Log every interaction (sanitization happens in _log_interaction)
    _log_interaction(tool_name, tool_input, project_dir)

    # Track file touches for Edit/Write (PLAN-166: validate file paths)
    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path")
        if file_path and isinstance(file_path, str):
            # PLAN-166: Validate path length
            if len(file_path) > _MAX_PATH_LENGTH:
                _logger.warning(f"File path exceeds max length: {len(file_path)}")
            # Security: Validate path doesn't contain traversal sequences
            # and is within the project directory
            elif _is_safe_path(file_path, project_dir):
                update_session(crux_dir, add_file=file_path)
                result["file_tracked"] = file_path
            else:
                _logger.warning(f"Unsafe file path rejected: {file_path!r}")

    # Increment BIP interaction counter
    _increment_bip_counter(project_dir, "interactions_since_last_post", 1)

    # Periodic background processor check
    count = _count_interactions(project_dir)
    if count > 0 and count % _PROCESSOR_CHECK_INTERVAL == 0:
        bg_result = _try_background_processors(project_dir, home)
        if bg_result is not None:
            result["processors_run"] = bg_result.get("processors_run", [])

    return result


def _increment_bip_counter(project_dir: str, field_name: str, amount: int = 1) -> None:
    """Increment a BIP state counter. Never raises."""
    try:
        bip_dir = os.path.join(project_dir, ".crux", "bip")
        if os.path.isdir(bip_dir):
            from scripts.lib.crux_bip import increment_counter
            increment_counter(bip_dir, field_name, amount)
    except Exception:
        pass


def _try_background_processors(project_dir: str, home: str) -> dict | None:
    """Run background processors if thresholds are exceeded. Never raises.

    PLAN-166: Now logs exceptions instead of silently swallowing them.
    """
    try:
        from scripts.lib.crux_background_processor import should_process, run_processors
        if should_process(project_dir, home):
            return run_processors(project_dir, home)
    except ImportError:
        # Expected if background processor not available
        pass
    except Exception as e:
        # PLAN-166: Log unexpected errors for security audit trail
        _logger.error(f"Background processor error: {type(e).__name__}: {e}")
    return None


def handle_stop(
    event_data: dict,
    project_dir: str,
    home: str,
) -> dict:
    """Handle Stop — update session timestamp, record interaction count, check TDD, run processors."""
    crux_dir = os.path.join(project_dir, ".crux")
    state = load_session(crux_dir)
    save_session(state, project_crux_dir=crux_dir)  # updates timestamp

    count = _count_interactions(project_dir)

    # TDD compliance check
    tdd = check_tdd_compliance(state.files_touched)

    # Background processor check
    bg_result = _try_background_processors(project_dir, home)

    result: dict = {
        "status": "ok",
        "interaction_count": count,
        "tdd_compliant": tdd["compliant"],
        "tdd_warnings": tdd["warnings"],
        "tdd_expected": tdd["expected_tests"],
    }
    if bg_result is not None:
        result["processors_run"] = bg_result.get("processors_run", [])

    return result


def handle_user_prompt(
    event_data: dict,
    project_dir: str,
    home: str,
) -> dict:
    """Handle UserPromptSubmit — log conversation and detect corrections.

    PLAN-166: Sanitizes prompts and validates input lengths.
    """
    prompt = event_data.get("prompt", "")

    # PLAN-166: Validate input length
    if not isinstance(prompt, str):
        return {"status": "error", "message": "prompt must be a string"}
    if len(prompt) > _MAX_PROMPT_LENGTH:
        _logger.warning(f"Prompt exceeds max length ({len(prompt)} > {_MAX_PROMPT_LENGTH})")
        prompt = prompt[:_MAX_PROMPT_LENGTH]

    detected = _is_correction(prompt)

    result: dict = {"status": "ok", "correction_detected": detected}

    # Log all non-empty user messages to conversations
    # Note: _log_conversation handles sanitization internally
    if prompt.strip():
        state = load_session(os.path.join(project_dir, ".crux"))
        _log_conversation(
            role="user",
            content=prompt,
            project_dir=project_dir,
            mode=state.active_mode,
            tool=state.active_tool,
        )

    if detected:
        # Log the correction with sanitized content
        paths = get_project_paths(project_dir)
        # PLAN-166: Create directories with restricted permissions
        os.makedirs(paths.corrections, mode=0o700, exist_ok=True)

        # PLAN-166: Sanitize prompt before logging
        sanitized_prompt = _sanitize_prompt(prompt)
        entry = {
            "original": sanitized_prompt,
            "corrected": "",
            "category": "user-correction",
            "mode": load_session(os.path.join(project_dir, ".crux")).active_mode,
            "timestamp": _now_iso(),
        }

        # PLAN-166: Write with restricted permissions
        fd = os.open(paths.corrections_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, (json.dumps(entry) + "\n").encode('utf-8'))
        finally:
            os.close(fd)

    return result


# ---------------------------------------------------------------------------
# Hook runner — dispatches JSON events to handlers
# ---------------------------------------------------------------------------

def run_hook(
    event_json: str,
    project_dir: str,
    home: str,
) -> dict:
    """Parse event JSON and dispatch to the appropriate handler.

    PLAN-166: Added JSON schema validation for security.
    """
    try:
        event_data = json.loads(event_json)
    except (json.JSONDecodeError, TypeError):
        return {"status": "error", "message": "Invalid JSON"}

    # PLAN-166: Validate event data structure
    if not isinstance(event_data, dict):
        return {"status": "error", "message": "Event must be a JSON object"}

    event_name = event_data.get("hook_event_name", "")
    if not isinstance(event_name, str):
        return {"status": "error", "message": "hook_event_name must be a string"}

    handlers = {
        "SessionStart": handle_session_start,
        "PostToolUse": handle_post_tool_use,
        "Stop": handle_stop,
        "UserPromptSubmit": handle_user_prompt,
    }

    handler = handlers.get(event_name)
    if handler is None:
        return {"status": "ok", "event": event_name, "action": "noop"}

    return handler(event_data=event_data, project_dir=project_dir, home=home)


# ---------------------------------------------------------------------------
# Settings builder — generates .claude/settings.local.json hooks config
# ---------------------------------------------------------------------------

def build_hook_settings(project_dir: str, home: str) -> dict:
    """Build the hooks configuration for .claude/settings.local.json.

    PLAN-166: Use shlex.quote to prevent command injection via paths.
    """
    from scripts.lib.crux_paths import get_crux_python, get_crux_repo
    python = get_crux_python()
    crux_repo = get_crux_repo()
    # Security: Quote paths to prevent shell injection (PLAN-166)
    runner = f"PYTHONPATH={shlex.quote(crux_repo)} {shlex.quote(python)} -m scripts.lib.crux_hook_runner"

    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{runner} SessionStart",
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{runner} PostToolUse",
                        }
                    ],
                }
            ],
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{runner} UserPromptSubmit",
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{runner} Stop",
                        }
                    ],
                }
            ],
        }
    }
