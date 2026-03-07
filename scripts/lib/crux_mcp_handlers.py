"""Handler functions for Crux MCP server tools.

Each handle_* function contains pure logic — no MCP decorators.
The MCP server module wraps these with @mcp.tool().
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

# PLAN-166: Security constants and validation functions
MAX_DRAFT_SIZE = 50000  # Maximum draft text size in bytes
MAX_LIST_RESULTS = 1000  # Maximum results to return from list operations
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD format
SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")  # Safe characters for path components
KNOWN_MODES = frozenset([
    "code", "architect", "ask", "debug", "review", "test",
    "docs", "design", "security", "build-in-public", "default"
])

logger = logging.getLogger(__name__)


def _validate_path_param(value: str, param_name: str = "parameter") -> None:
    """PLAN-166: Validate a path parameter contains only safe characters.

    Raises ValueError if validation fails.
    """
    if not value:
        raise ValueError(f"{param_name} cannot be empty")
    if not SAFE_NAME_PATTERN.match(value):
        raise ValueError(f"{param_name} contains invalid characters")
    # Prevent path traversal attempts
    if ".." in value or value.startswith("/") or value.startswith("\\"):
        raise ValueError(f"{param_name} contains path traversal attempt")


def _validate_date_format(date_str: str) -> None:
    """PLAN-166: Validate date string matches YYYY-MM-DD format.

    Raises ValueError if validation fails.
    """
    if not DATE_PATTERN.match(date_str):
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def _validate_mode(mode: str) -> None:
    """PLAN-166: Validate mode against known modes list.

    Raises ValueError if mode is not recognized.
    """
    if mode not in KNOWN_MODES:
        raise ValueError(f"Unknown mode: {mode}. Must be one of: {', '.join(sorted(KNOWN_MODES))}")


def _safe_path_join(base_dir: str, *parts: str) -> str:
    """PLAN-166: Safely join path components and validate result stays within base.

    Returns the normalized path. Raises ValueError if path escapes base directory.
    """
    result = os.path.normpath(os.path.join(base_dir, *parts))
    base_normalized = os.path.normpath(base_dir)
    if not result.startswith(base_normalized + os.sep) and result != base_normalized:
        raise ValueError("Path traversal attempt detected")
    return result


def _sanitize_error_message(error: Exception) -> str:
    """PLAN-166: Return a generic error message without exposing internals."""
    return "An error occurred while processing the request"

from scripts.lib.crux_paths import get_project_paths, get_user_paths, CruxPaths
from scripts.lib.crux_session import (
    load_session,
    save_session,
    update_session,
    write_handoff as _write_handoff,
    read_handoff as _read_handoff,
)
from scripts.lib.crux_switch import switch_tool
from scripts.lib.crux_pipeline_config import (
    PipelineConfig,
    load_pipeline_config,
    save_pipeline_config,
    gates_for_mode,
)
from scripts.lib.crux_tdd_gate import (
    start_tdd_gate,
    record_red_phase,
    record_green_phase,
    check_tdd_gate_status,
)
from scripts.lib.crux_security_audit import (
    SecurityFinding,
    start_audit,
    record_findings,
    check_convergence,
    get_blocking_findings,
    resolve_finding,
    audit_summary,
)
from scripts.lib.crux_design_validation import (
    check_contrast_ratio,
    validate_touch_targets,
    start_validation,
    record_validation_findings,
    validation_summary,
    ValidationFinding,
)


# ---------------------------------------------------------------------------
# lookup_knowledge
# ---------------------------------------------------------------------------

def handle_lookup_knowledge(
    query: str,
    project_dir: str,
    home: str,
    mode: str | None = None,
) -> dict:
    """Search knowledge entries across project and user scopes."""
    crux = CruxPaths(project_dir=project_dir, home=home)
    search_dirs = crux.knowledge_search_dirs(mode)

    results: list[dict] = []
    query_lower = query.lower()

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for md_file in Path(d).glob("*.md"):
            # PLAN-166: Wrap file read in try/except for unhandled exceptions
            try:
                content = md_file.read_text()
            except (OSError, IOError) as e:
                logger.warning(f"Could not read knowledge file {md_file}: {e}")
                continue

            name = md_file.stem
            if query_lower in content.lower() or query_lower in name.lower():
                excerpt = content[:300].strip()
                results.append({
                    "name": name,
                    "excerpt": excerpt,
                    "source": _classify_source(str(md_file), project_dir, home),
                    "path": str(md_file),
                })

    # Deduplicate by name (first occurrence wins — most specific scope)
    seen: set[str] = set()
    unique: list[dict] = []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    # PLAN-166: Apply size limit to prevent memory issues with large result sets
    if len(unique) > MAX_LIST_RESULTS:
        unique = unique[:MAX_LIST_RESULTS]

    return {
        "total_found": len(unique),
        "results": unique,
    }


def _classify_source(path: str, project_dir: str, home: str) -> str:
    """Classify a knowledge file as 'project' or 'user'."""
    project_crux = os.path.join(project_dir, ".crux")
    if path.startswith(project_crux):
        return "project"
    return "user"


# ---------------------------------------------------------------------------
# get_session_state / update_session
# ---------------------------------------------------------------------------

def handle_get_session_state(project_dir: str) -> dict:
    """Return current session state as a dict."""
    project_paths = get_project_paths(project_dir)
    state = load_session(str(project_paths.root))
    return state.to_dict()


def handle_update_session(
    project_dir: str,
    active_mode: str | None = None,
    active_tool: str | None = None,
    working_on: str | None = None,
    add_decision: str | None = None,
    add_file: str | None = None,
    add_pending: str | None = None,
) -> dict:
    """Update session state and return the new state."""
    project_paths = get_project_paths(project_dir)
    state = update_session(
        project_crux_dir=str(project_paths.root),
        active_mode=active_mode,
        active_tool=active_tool,
        working_on=working_on,
        add_decision=add_decision,
        add_file=add_file,
        add_pending=add_pending,
    )
    return state.to_dict()


# ---------------------------------------------------------------------------
# Handoff
# ---------------------------------------------------------------------------

def handle_write_handoff(content: str, project_dir: str) -> dict:
    """Write handoff context for the next mode/tool."""
    project_paths = get_project_paths(project_dir)
    _write_handoff(content, project_crux_dir=str(project_paths.root))
    return {"written": True}


def handle_read_handoff(project_dir: str) -> dict:
    """Read handoff context."""
    project_paths = get_project_paths(project_dir)
    content = _read_handoff(project_crux_dir=str(project_paths.root))
    return {
        "exists": content is not None,
        "content": content,
    }


# ---------------------------------------------------------------------------
# get_digest
# ---------------------------------------------------------------------------

def handle_get_digest(home: str, date: str | None = None) -> dict:
    """Retrieve a daily digest by date, or the latest one."""
    user_paths = get_user_paths(home)
    digest_dir = user_paths.analytics_digests

    if not os.path.isdir(digest_dir):
        return {"found": False, "content": None}

    if date:
        # PLAN-166: Validate date format to prevent path traversal
        try:
            _validate_date_format(date)
        except ValueError as e:
            return {"found": False, "content": None, "error": str(e)}

        # PLAN-166: Use safe path join to prevent traversal
        try:
            digest_file = _safe_path_join(digest_dir, f"{date}.md")
        except ValueError:
            return {"found": False, "content": None, "error": "Invalid date parameter"}

        # PLAN-166: Wrap file read in try/except for unhandled exceptions
        try:
            if os.path.exists(digest_file):
                return {"found": True, "content": Path(digest_file).read_text()}
        except (OSError, IOError) as e:
            logger.error(f"Error reading digest file: {e}")
            return {"found": False, "content": None, "error": "Failed to read digest"}

        return {"found": False, "content": None}

    # Find latest digest
    # PLAN-166: Wrap file operations in try/except
    try:
        files = sorted(Path(digest_dir).glob("*.md"))
        if not files:
            return {"found": False, "content": None}

        latest = files[-1]
        return {"found": True, "content": latest.read_text()}
    except (OSError, IOError) as e:
        logger.error(f"Error reading digest directory: {e}")
        return {"found": False, "content": None, "error": "Failed to read digests"}


# ---------------------------------------------------------------------------
# get_mode_prompt / list_modes
# ---------------------------------------------------------------------------

def handle_get_mode_prompt(mode: str, home: str) -> dict:
    """Get the prompt for a specific mode."""
    # PLAN-166: Validate mode parameter to prevent path traversal
    try:
        _validate_path_param(mode, "mode")
    except ValueError as e:
        return {"found": False, "mode": mode, "prompt": None, "error": str(e)}

    user_paths = get_user_paths(home)

    # PLAN-166: Use safe path join
    try:
        mode_file = _safe_path_join(user_paths.modes, f"{mode}.md")
    except ValueError:
        return {"found": False, "mode": mode, "prompt": None, "error": "Invalid mode parameter"}

    # PLAN-166: Wrap file read in try/except
    try:
        if not os.path.exists(mode_file):
            return {"found": False, "mode": mode, "prompt": None}

        return {
            "found": True,
            "mode": mode,
            "prompt": Path(mode_file).read_text(),
        }
    except (OSError, IOError) as e:
        logger.error(f"Error reading mode file: {e}")
        return {"found": False, "mode": mode, "prompt": None, "error": "Failed to read mode"}


def handle_list_modes(home: str) -> dict:
    """List all available modes with excerpts."""
    user_paths = get_user_paths(home)
    modes_dir = user_paths.modes

    if not os.path.isdir(modes_dir):
        return {"modes": []}

    modes: list[dict] = []
    for md_file in sorted(Path(modes_dir).glob("*.md")):
        # PLAN-166: Wrap file read in try/except for unhandled exceptions
        try:
            content = md_file.read_text().strip()
        except (OSError, IOError) as e:
            logger.warning(f"Could not read mode file {md_file}: {e}")
            continue

        modes.append({
            "name": md_file.stem,
            "excerpt": content[:200],
        })

    return {"modes": modes}


# ---------------------------------------------------------------------------
# validate_script
# ---------------------------------------------------------------------------

_REQUIRED_HEADER_FIELDS = {"Name", "Risk", "Created", "Status", "Description"}


def handle_validate_script(content: str) -> dict:
    """Validate a script against Crux conventions."""
    errors: list[str] = []

    # Shebang
    if not content.startswith("#!/"):
        errors.append("Missing shebang line (e.g., #!/bin/bash)")

    # Header block
    if "################################" not in content:
        errors.append("Missing header block")
    else:
        for field_name in _REQUIRED_HEADER_FIELDS:
            pattern = rf"#\s*{field_name}:"
            if not re.search(pattern, content):
                errors.append(f"Missing header field: {field_name}")

    # set -euo pipefail
    if "set -euo pipefail" not in content:
        errors.append("Missing 'set -euo pipefail'")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# promote_knowledge
# ---------------------------------------------------------------------------

def handle_promote_knowledge(
    entry_name: str,
    project_dir: str,
    home: str,
) -> dict:
    """Promote a knowledge entry from project scope to user scope."""
    # PLAN-166: Validate entry_name to prevent path traversal
    try:
        _validate_path_param(entry_name, "entry_name")
    except ValueError as e:
        return {"promoted": False, "error": str(e)}

    project_paths = get_project_paths(project_dir)
    user_paths = get_user_paths(home)

    # PLAN-166: Use safe path join to prevent traversal
    try:
        source = _safe_path_join(project_paths.knowledge, f"{entry_name}.md")
        dest = _safe_path_join(user_paths.knowledge, f"{entry_name}.md")
    except ValueError:
        return {"promoted": False, "error": "Invalid entry name"}

    # PLAN-166: Check for symlinks before copy to prevent symlink attacks
    if os.path.islink(source):
        return {"promoted": False, "error": "Cannot promote symlinked entries"}

    # PLAN-166: Fix TOCTOU - use try/except around copy instead of check-then-copy
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # Use follow_symlinks=False to prevent symlink following during copy
        shutil.copy2(source, dest, follow_symlinks=False)
    except FileNotFoundError:
        return {"promoted": False, "error": "Entry not found in project knowledge"}
    except (OSError, IOError) as e:
        logger.error(f"Error promoting knowledge entry: {e}")
        return {"promoted": False, "error": "Failed to promote entry"}

    # PLAN-166: Don't leak internal paths in response
    return {"promoted": True, "entry": entry_name}


# ---------------------------------------------------------------------------
# get_project_context
# ---------------------------------------------------------------------------

def handle_get_project_context(project_dir: str) -> dict:
    """Read PROJECT.md from the project context directory."""
    project_paths = get_project_paths(project_dir)
    project_md = project_paths.project_md

    if not os.path.exists(project_md):
        return {"found": False, "content": None}

    return {"found": True, "content": Path(project_md).read_text()}


# ---------------------------------------------------------------------------
# switch_tool
# ---------------------------------------------------------------------------

def handle_switch_tool(
    target_tool: str,
    project_dir: str,
    home: str,
) -> dict:
    """Switch to a different AI coding tool."""
    result = switch_tool(
        target_tool=target_tool,
        project_dir=project_dir,
        home=home,
    )
    resp: dict = {
        "success": result.success,
        "from_tool": result.from_tool,
        "to_tool": result.to_tool,
    }
    if result.error:
        resp["error"] = result.error
    if result.items_synced:
        resp["items_synced"] = result.items_synced
    return resp


# ---------------------------------------------------------------------------
# log_correction
# ---------------------------------------------------------------------------

def handle_log_correction(
    original: str,
    corrected: str,
    category: str,
    mode: str,
    project_dir: str,
) -> dict:
    """Log a correction to the project corrections JSONL file."""
    project_paths = get_project_paths(project_dir)
    corrections_dir = project_paths.corrections
    os.makedirs(corrections_dir, exist_ok=True)

    corrections_file = project_paths.corrections_file
    entry = {
        "original": original,
        "corrected": corrected,
        "category": category,
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with open(corrections_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"logged": True}


# ---------------------------------------------------------------------------
# Pipeline config
# ---------------------------------------------------------------------------

def handle_get_pipeline_config(project_dir: str) -> dict:
    """Load and return the pipeline configuration."""
    config_path = os.path.join(project_dir, ".crux", "pipeline.json")
    cfg = load_pipeline_config(config_path)
    return cfg.to_dict()


def handle_get_active_gates(mode: str, risk_level: str, project_dir: str) -> dict:
    """Get the active gates for a mode at a given risk level."""
    config_path = os.path.join(project_dir, ".crux", "pipeline.json")
    cfg = load_pipeline_config(config_path)
    gates = gates_for_mode(mode, risk_level, cfg)
    return {"mode": mode, "risk_level": risk_level, "active_gates": gates}


# ---------------------------------------------------------------------------
# TDD gate
# ---------------------------------------------------------------------------

def handle_start_tdd_gate(
    mode: str,
    feature: str,
    components: list[str],
    edge_cases: list[str],
    project_dir: str,
) -> dict:
    """Start the TDD enforcement gate for a feature."""
    config_path = os.path.join(project_dir, ".crux", "pipeline.json")
    cfg = load_pipeline_config(config_path)
    gate_file = os.path.join(project_dir, ".crux", "gates", "tdd.json")
    os.makedirs(os.path.dirname(gate_file), exist_ok=True)

    state = start_tdd_gate(
        mode=mode,
        enforcement_level=cfg.tdd.level,
        feature=feature,
        components=components,
        edge_cases=edge_cases,
        gate_file=gate_file,
    )
    return state.to_dict()


def handle_check_tdd_status(project_dir: str) -> dict:
    """Check the current status of the TDD gate."""
    gate_file = os.path.join(project_dir, ".crux", "gates", "tdd.json")
    return check_tdd_gate_status(gate_file)


# ---------------------------------------------------------------------------
# Security audit
# ---------------------------------------------------------------------------

def handle_start_security_audit(project_dir: str) -> dict:
    """Start a security audit loop."""
    config_path = os.path.join(project_dir, ".crux", "pipeline.json")
    cfg = load_pipeline_config(config_path)
    audit_file = os.path.join(project_dir, ".crux", "gates", "security.json")
    os.makedirs(os.path.dirname(audit_file), exist_ok=True)

    state = start_audit(
        max_iterations=cfg.security_audit.max_iterations,
        categories=cfg.security_audit.categories,
        audit_file=audit_file,
    )
    return state.to_dict()


def handle_security_audit_summary(project_dir: str) -> dict:
    """Get the security audit summary."""
    audit_file = os.path.join(project_dir, ".crux", "gates", "security.json")
    return audit_summary(audit_file)


# ---------------------------------------------------------------------------
# Design validation
# ---------------------------------------------------------------------------

def handle_start_design_validation(project_dir: str) -> dict:
    """Start the design validation gate."""
    config_path = os.path.join(project_dir, ".crux", "pipeline.json")
    cfg = load_pipeline_config(config_path)
    val_file = os.path.join(project_dir, ".crux", "gates", "design.json")
    os.makedirs(os.path.dirname(val_file), exist_ok=True)

    state = start_validation(
        wcag_level=cfg.design_validation.wcag_level,
        check_brand=cfg.design_validation.check_brand_consistency,
        check_handoff=cfg.design_validation.check_handoff_completeness,
        validation_file=val_file,
    )
    return state.to_dict()


def handle_design_validation_summary(project_dir: str) -> dict:
    """Get the design validation summary."""
    val_file = os.path.join(project_dir, ".crux", "gates", "design.json")
    return validation_summary(val_file)


def handle_check_contrast(foreground: str, background: str) -> dict:
    """Check contrast ratio between two colors."""
    result = check_contrast_ratio(foreground, background)
    return result.to_dict()


# ---------------------------------------------------------------------------
# log_interaction — full-text conversation logging for MCP clients
# ---------------------------------------------------------------------------

def handle_log_interaction(
    role: str,
    content: str,
    project_dir: str,
    metadata: dict | None = None,
) -> dict:
    """Log a conversation message to the conversations JSONL file.

    Used by OpenCode (and other MCP clients) to log full-text messages
    for analysis and continuous improvement.
    """
    if not content.strip():
        return {"logged": False, "error": "Empty content"}
    if role not in ("user", "assistant"):
        return {"logged": False, "error": f"Invalid role: '{role}'. Must be 'user' or 'assistant'"}

    project_paths = get_project_paths(project_dir)
    state = load_session(str(project_paths.root))

    log_dir = os.path.join(str(project_paths.root), "analytics", "conversations")
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{today}.jsonl")

    # PLAN-166: Validate mode from session state against known modes
    active_mode = state.active_mode
    if active_mode and active_mode not in KNOWN_MODES:
        # Sanitize unknown modes to prevent injection
        active_mode = "unknown"

    entry: dict = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "role": role,
        "content": content,
        "mode": active_mode,
        "tool": state.active_tool,
    }
    if metadata:
        entry["metadata"] = metadata

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except (OSError, IOError) as e:
        logger.error(f"Error writing interaction log: {e}")
        return {"logged": False, "error": "Failed to write log"}

    return {"logged": True}


# ---------------------------------------------------------------------------
# restore_context — rebuild full session context after restart
# ---------------------------------------------------------------------------

def handle_restore_context(project_dir: str, home: str) -> dict:
    """Rebuild full session context for injection after a restart.

    Returns a formatted context string containing:
    - Active mode and its prompt
    - Working on description
    - Key decisions
    - Pending tasks
    - Files touched
    - Handoff context
    - Context summary
    """
    project_paths = get_project_paths(project_dir)
    user_paths = get_user_paths(home)
    state = load_session(str(project_paths.root))
    handoff = _read_handoff(str(project_paths.root))

    parts: list[str] = []

    # PLAN-166: Validate active_mode before using in path
    active_mode = state.active_mode
    mode_prompt = None

    # Only attempt to read mode file if mode is valid
    try:
        _validate_path_param(active_mode, "active_mode")
        mode_file = _safe_path_join(user_paths.modes, f"{active_mode}.md")
        if os.path.exists(mode_file) and not os.path.islink(mode_file):
            mode_prompt = Path(mode_file).read_text().strip()
    except (ValueError, OSError, IOError) as e:
        logger.warning(f"Could not load mode prompt for {active_mode}: {e}")

    # Mode prompt
    if mode_prompt:
        parts.append(f"## Active Mode: {active_mode}\n{mode_prompt}")
    else:
        parts.append(f"## Active Mode: {active_mode}")

    # Session state
    parts.append(f"\n## Session State")
    parts.append(f"- Mode: {state.active_mode}")
    parts.append(f"- Tool: {state.active_tool or 'not set'}")
    if state.working_on:
        parts.append(f"- Working on: {state.working_on}")

    # Context summary
    if state.context_summary:
        parts.append(f"\n## Context Summary\n{state.context_summary}")

    # Key decisions
    if state.key_decisions:
        parts.append(f"\n## Key Decisions ({len(state.key_decisions)} total)")
        for d in state.key_decisions:
            parts.append(f"- {d}")

    # Pending tasks
    if state.pending:
        parts.append(f"\n## Pending Tasks")
        for task in state.pending:
            parts.append(f"- {task}")

    # Files touched
    if state.files_touched:
        parts.append(f"\n## Files Touched ({len(state.files_touched)} files)")
        for f in state.files_touched:
            parts.append(f"- {f}")

    # Handoff
    if handoff:
        parts.append(f"\n## Handoff Context\n{handoff}")

    return {"context": "\n".join(parts)}


def handle_verify_health(project_dir: str, home: str) -> dict:
    """Run combined static + liveness health checks and return a full report."""
    from scripts.lib.crux_status import verify_health
    return verify_health(project_dir=project_dir, home=home)


def handle_audit_script_8b(script_content: str, risk_level: str) -> dict:
    """Gate 4: Run 8B adversarial audit on a script."""
    from scripts.lib.crux_llm_audit import audit_script_8b
    return audit_script_8b(script_content, risk_level)


def handle_audit_script_32b(script_content: str, risk_level: str) -> dict:
    """Gate 5: Run 32B second-opinion audit on a script (high-risk only)."""
    from scripts.lib.crux_llm_audit import audit_script_32b
    return audit_script_32b(script_content, risk_level)


# ---------------------------------------------------------------------------
# Background processor
# ---------------------------------------------------------------------------

def handle_check_processor_thresholds(project_dir: str, home: str) -> dict:
    """Check which background processing thresholds are exceeded."""
    from scripts.lib.crux_background_processor import check_thresholds
    return check_thresholds(project_dir, home)


def handle_run_background_processors(project_dir: str, home: str) -> dict:
    """Run all due background processors (corrections, digest, mode audit)."""
    from scripts.lib.crux_background_processor import run_processors
    return run_processors(project_dir, home)


def handle_get_processor_status(project_dir: str) -> dict:
    """Get when each background processor last ran."""
    from scripts.lib.crux_background_processor import get_processor_status
    return get_processor_status(project_dir)


# ---------------------------------------------------------------------------
# Cross-project aggregation
# ---------------------------------------------------------------------------

def handle_register_project(project_dir: str, home: str) -> dict:
    """Register a project for cross-project aggregation."""
    from scripts.lib.crux_cross_project import register_project
    return register_project(project_dir, home)


def handle_get_cross_project_digest(home: str, date: str | None = None) -> dict:
    """Generate a cross-project digest for the given date."""
    from scripts.lib.crux_cross_project import generate_user_digest
    return generate_user_digest(home, date)


# ---------------------------------------------------------------------------
# Figma
# ---------------------------------------------------------------------------

def handle_figma_get_tokens(file_key: str, token: str) -> dict:
    """Fetch a Figma file and extract design tokens."""
    from scripts.lib.crux_figma import get_file, extract_design_tokens, generate_token_css, generate_token_tailwind
    result = get_file(file_key, token)
    if not result["success"]:
        return result
    tokens = extract_design_tokens(result["data"])
    return {
        "success": True,
        "tokens": tokens,
        "css": generate_token_css(tokens),
        "tailwind": generate_token_tailwind(tokens),
    }


def handle_figma_get_components(file_key: str, token: str) -> dict:
    """Fetch Figma components from a file."""
    from scripts.lib.crux_figma import get_file_components
    return get_file_components(file_key, token)


# ---------------------------------------------------------------------------
# Build-in-public
# ---------------------------------------------------------------------------

def handle_bip_generate(
    project_dir: str,
    home: str,
    platform: str = "x",
    force: bool = False,
    event: str | None = None,
) -> dict:
    """Check triggers and gather content for a BIP draft.

    Returns gathered context and trigger result so the LLM can generate
    the actual draft text using the build-in-public mode voice.
    """
    import os
    from scripts.lib.crux_bip_gather import gather_content
    from scripts.lib.crux_bip_triggers import evaluate_triggers
    from scripts.lib.crux_bip import load_state, load_config

    crux_dir = os.path.join(project_dir, ".crux")
    bip_dir = os.path.join(crux_dir, "bip")

    # Check triggers
    trigger = evaluate_triggers(bip_dir, event=event, force=force)

    config = load_config(bip_dir)
    state = load_state(bip_dir)

    if not trigger.should_trigger:
        return {
            "status": "skipped",
            "reason": trigger.reason,
            "state": {
                "commits": state.commits_since_last_post,
                "interactions": state.interactions_since_last_post,
                "tokens": state.tokens_since_last_post,
                "last_queued_at": state.last_queued_at,
                "cooldown_minutes": config.cooldown_minutes,
            },
        }

    # Gather content
    since = state.last_queued_at
    ctx = gather_content(project_dir=project_dir, home=home, since=since)

    # PLAN-166: Apply explicit size limits before slicing to prevent memory issues
    # Limit source lists first, then slice for response
    unposted_commits = (ctx.unposted_commits or [])[:MAX_LIST_RESULTS][:20]
    commit_messages = (ctx.commit_messages or [])[:MAX_LIST_RESULTS][:20]
    files_changed = (ctx.files_changed or [])[:MAX_LIST_RESULTS][:30]
    corrections = (ctx.corrections or [])[:MAX_LIST_RESULTS][:10]
    knowledge_entries = (ctx.knowledge_entries or [])[:MAX_LIST_RESULTS]
    key_decisions = (ctx.key_decisions or [])[:MAX_LIST_RESULTS][:10]

    return {
        "status": "ready",
        "trigger_reason": trigger.reason,
        "platform": platform,
        "context": {
            "unposted_commits": unposted_commits,
            "commit_messages": commit_messages,
            "files_changed": files_changed,
            "corrections": [c.get("pattern", "") for c in corrections],
            "knowledge_entries": [k["name"] for k in knowledge_entries],
            "session_mode": ctx.session_mode,
            "session_tool": ctx.session_tool,
            "working_on": ctx.working_on,
            "key_decisions": key_decisions,
        },
        "voice": {
            "style": config.voice_style,
            "tone": config.voice_tone,
            "never_words": config.never_words,
            "hashtags": ["buildinpublic", "opensource", "aitools", "localllm", "vibecoding"],
        },
    }


def handle_bip_approve(
    project_dir: str,
    draft_text: str,
    source_keys: list[str] | None = None,
    publish_at: str | None = None,
) -> dict:
    """Approve a BIP draft and queue it to Typefully.

    Args:
        project_dir: Project directory path.
        draft_text: The approved draft text (single tweet or \\n\\n-separated thread).
        source_keys: List of source keys for history dedup (e.g. ["git:abc123"]).
        publish_at: Optional ISO 8601 timestamp for scheduled publishing.
    """
    import os
    from datetime import datetime, timezone
    from scripts.lib.crux_bip import (
        load_state, save_state, record_history, reset_counters,
    )

    # PLAN-166: Enforce size limit on draft_text to prevent resource exhaustion
    if len(draft_text) > MAX_DRAFT_SIZE:
        return {
            "status": "error",
            "error": f"Draft text exceeds maximum size of {MAX_DRAFT_SIZE} bytes",
        }

    crux_dir = os.path.join(project_dir, ".crux")
    bip_dir = os.path.join(crux_dir, "bip")

    # Save draft to file
    now = datetime.now(timezone.utc)
    draft_filename = now.strftime("%Y%m%d-%H%M%S") + ".md"
    drafts_dir = os.path.join(bip_dir, "drafts")
    os.makedirs(drafts_dir, exist_ok=True)
    draft_path = os.path.join(drafts_dir, draft_filename)
    with open(draft_path, "w") as f:
        f.write(draft_text)

    # Try to queue to Typefully
    queued = False
    queue_error = None
    draft_id = None
    try:
        from scripts.lib.crux_typefully import TypefullyClient, create_draft, create_thread

        client = TypefullyClient(bip_dir=bip_dir)
        tweets = [t.strip() for t in draft_text.split("\n\n") if t.strip()]
        if len(tweets) > 1:
            result = create_thread(client, tweets, publish_at=publish_at)
        else:
            result = create_draft(client, draft_text.strip(), publish_at=publish_at)
        draft_id = result.get("id")
        queued = True
    except Exception as e:
        # PLAN-166: Log full error but return generic message to prevent info disclosure
        logger.error(f"Error queueing to Typefully: {e}")
        queue_error = "Failed to queue draft to publishing service"

    # Record history
    for key in (source_keys or []):
        record_history(bip_dir, source_key=key, draft_preview=draft_text[:200])

    # Update state
    state = load_state(bip_dir)
    state.last_queued_at = now.isoformat()
    if draft_id:
        state.last_queued_id = draft_id
    state.posts_today += 1
    state.posts_this_hour += 1
    state.commits_since_last_post = 0
    state.tokens_since_last_post = 0
    state.interactions_since_last_post = 0
    save_state(state, bip_dir)

    # PLAN-166: Don't leak internal paths in response
    return {
        "status": "queued" if queued else "saved",
        "draft_id": draft_id,
        "queue_error": queue_error,
    }


def handle_bip_status(project_dir: str) -> dict:
    """Get current BIP state — counters, cooldown, recent history."""
    import os
    from scripts.lib.crux_bip import load_state, load_config, load_history, check_cooldown

    crux_dir = os.path.join(project_dir, ".crux")
    bip_dir = os.path.join(crux_dir, "bip")
    config = load_config(bip_dir)
    state = load_state(bip_dir)
    history = load_history(bip_dir)
    cooldown_ok = check_cooldown(bip_dir, cooldown_minutes=config.cooldown_minutes)

    return {
        "commits_since_last_post": state.commits_since_last_post,
        "interactions_since_last_post": state.interactions_since_last_post,
        "tokens_since_last_post": state.tokens_since_last_post,
        "posts_today": state.posts_today,
        "last_queued_at": state.last_queued_at,
        "cooldown_ok": cooldown_ok,
        "cooldown_minutes": config.cooldown_minutes,
        "thresholds": {
            "commits": config.commit_threshold,
            "interactions": config.interaction_threshold,
            "tokens": config.token_threshold,
        },
        "total_posts": len(history),
        "recent_posts": [
            {"source": h.get("source_key", ""), "preview": h.get("draft_preview", "")[:80]}
            for h in history[-5:]
        ],
    }
