"""Crux MCP Server — universal integration layer for AI coding tools.

Exposes Crux capabilities (knowledge, sessions, modes, corrections, etc.)
via the Model Context Protocol. Any MCP-compatible tool (Claude Code, OpenCode,
Cursor, etc.) can connect to this server.

Run: python -m scripts.lib.crux_mcp_server
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from scripts.lib.crux_mcp_handlers import (
    handle_lookup_knowledge,
    handle_get_session_state,
    handle_update_session,
    handle_write_handoff,
    handle_read_handoff,
    handle_get_digest,
    handle_get_mode_prompt,
    handle_validate_script,
    handle_promote_knowledge,
    handle_get_project_context,
    handle_switch_tool,
    handle_list_modes,
    handle_log_correction,
    handle_log_interaction,
    handle_restore_context,
    handle_get_pipeline_config,
    handle_get_active_gates,
    handle_start_tdd_gate,
    handle_check_tdd_status,
    handle_start_security_audit,
    handle_security_audit_summary,
    handle_start_design_validation,
    handle_design_validation_summary,
    handle_check_contrast,
    handle_verify_health,
    handle_audit_script_8b,
    handle_audit_script_32b,
    handle_check_processor_thresholds,
    handle_run_background_processors,
    handle_get_processor_status,
    handle_register_project,
    handle_get_cross_project_digest,
    handle_figma_get_tokens,
    handle_figma_get_components,
    handle_bip_generate,
    handle_bip_approve,
    handle_bip_status,
    handle_bip_get_analytics,
)

mcp = FastMCP("crux", instructions=(
    "Crux AI operating system — knowledge, sessions, modes, and tool switching.\n\n"
    "IMPORTANT: After every significant action (file edit, decision, task completion), "
    "call update_session() with working_on, add_decision, or add_file as appropriate. "
    "Session state must be continuously maintained so context can be restored at any time "
    "without advance notice. This is NOT optional.\n\n"
    "When switching tools, call switch_tool_to(tool_id). It auto-writes handoff from "
    "accumulated session state and generates the target tool's MCP config.\n\n"
    "On session start, call restore_context() to load previous session state. "
    "If the response includes session_adoption.available=true, inform the user "
    "that previous session logs were detected and ask if they'd like to adopt "
    "them into Crux for portability."
))


# Cache cwd at import time — MCP server is spawned per-project by the tool,
# so cwd at startup IS the project directory. os.getcwd() can drift if
# subprocesses change directory.
_STARTUP_CWD = os.getcwd()


def _home() -> str:
    return os.environ.get("CRUX_HOME", os.environ.get("HOME", ""))


def _project() -> str:
    return os.environ.get("CRUX_PROJECT", _STARTUP_CWD)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def lookup_knowledge(query: str, mode: str | None = None) -> dict:
    """Search knowledge entries across project and user scopes.

    Args:
        query: Search term to match against knowledge entry names and content.
        mode: Optional mode name to include mode-scoped knowledge.
    """
    return handle_lookup_knowledge(query=query, mode=mode, project_dir=_project(), home=_home())


@mcp.tool()
def get_session_state() -> dict:
    """Get the current Crux session state (active mode, tool, working context)."""
    return handle_get_session_state(project_dir=_project())


@mcp.tool()
def update_session(
    active_mode: str | None = None,
    active_tool: str | None = None,
    working_on: str | None = None,
    add_decision: str | None = None,
    add_file: str | None = None,
    add_pending: str | None = None,
) -> dict:
    """Update the current session state.

    Args:
        active_mode: Switch to a different mode.
        active_tool: Update the active tool name.
        working_on: Describe what you're currently working on.
        add_decision: Add a key decision to the session log.
        add_file: Add a file to the list of touched files.
        add_pending: Add a pending task.
    """
    return handle_update_session(
        project_dir=_project(),
        active_mode=active_mode,
        active_tool=active_tool,
        working_on=working_on,
        add_decision=add_decision,
        add_file=add_file,
        add_pending=add_pending,
    )


@mcp.tool()
def write_handoff(content: str) -> dict:
    """Write handoff context for the next mode or tool switch.

    Args:
        content: The handoff context to persist.
    """
    return handle_write_handoff(content=content, project_dir=_project())


@mcp.tool()
def read_handoff() -> dict:
    """Read handoff context left by a previous mode or tool."""
    return handle_read_handoff(project_dir=_project())


@mcp.tool()
def get_digest(date: str | None = None) -> dict:
    """Retrieve a daily digest.

    Args:
        date: Date in YYYY-MM-DD format. Omit for the latest digest.
    """
    return handle_get_digest(home=_home(), date=date)


@mcp.tool()
def get_mode_prompt(mode: str) -> dict:
    """Get the full prompt text for a specific mode.

    Args:
        mode: The mode name (e.g., 'build-py', 'debug', 'plan').
    """
    return handle_get_mode_prompt(mode=mode, home=_home())


@mcp.tool()
def list_modes() -> dict:
    """List all available Crux modes with descriptions."""
    return handle_list_modes(home=_home())


@mcp.tool()
def validate_script(content: str) -> dict:
    """Validate a script against Crux safety conventions.

    Args:
        content: The full script content to validate.
    """
    return handle_validate_script(content=content)


@mcp.tool()
def promote_knowledge(entry_name: str) -> dict:
    """Promote a knowledge entry from project scope to user scope.

    Args:
        entry_name: The knowledge entry name (without .md extension).
    """
    return handle_promote_knowledge(entry_name=entry_name, project_dir=_project(), home=_home())


@mcp.tool()
def get_project_context() -> dict:
    """Read the PROJECT.md context file for the current project."""
    return handle_get_project_context(project_dir=_project())


@mcp.tool()
def switch_tool_to(target_tool: str) -> dict:
    """Switch to a different AI coding tool, syncing all configs.

    Args:
        target_tool: The tool to switch to (e.g., 'opencode', 'claude-code').
    """
    return handle_switch_tool(target_tool=target_tool, project_dir=_project(), home=_home())


@mcp.tool()
def log_correction(
    original: str,
    corrected: str,
    category: str,
    mode: str,
) -> dict:
    """Log a correction for continuous learning.

    Args:
        original: What the AI originally did/said.
        corrected: What the correct action/response should have been.
        category: Correction category (e.g., 'code-pattern', 'style', 'logic').
        mode: The mode that was active when the correction occurred.
    """
    return handle_log_correction(
        original=original,
        corrected=corrected,
        category=category,
        mode=mode,
        project_dir=_project(),
    )


@mcp.tool()
def log_interaction(
    role: str,
    content: str,
    metadata: dict | None = None,
) -> dict:
    """Log a conversation message for continuous learning analysis.

    Call this to log user messages and assistant responses so Crux can
    analyze interaction patterns and improve over time.

    Args:
        role: Message role — 'user' or 'assistant'.
        content: The full message text.
        metadata: Optional metadata dict (e.g., source tool, context).
    """
    return handle_log_interaction(
        role=role,
        content=content,
        project_dir=_project(),
        metadata=metadata,
    )


@mcp.tool()
def restore_context() -> dict:
    """Restore full session context after a restart or tool switch.

    Call this at the start of a new session to recover: active mode and prompt,
    what you were working on, key decisions, pending tasks, files touched,
    and any handoff context from the previous session.
    """
    return handle_restore_context(project_dir=_project(), home=_home())


# ---------------------------------------------------------------------------
# Pipeline & Gate Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_pipeline_config() -> dict:
    """Get the current pipeline configuration (gates, TDD level, security settings)."""
    return handle_get_pipeline_config(project_dir=_project())


@mcp.tool()
def get_active_gates(mode: str, risk_level: str) -> dict:
    """Get active safety gates for a mode at a given risk level.

    Args:
        mode: The active mode (e.g., 'build-py', 'design-ui').
        risk_level: Risk level ('low', 'medium', 'high', 'critical').
    """
    return handle_get_active_gates(mode=mode, risk_level=risk_level, project_dir=_project())


@mcp.tool()
def start_tdd_gate(mode: str, feature: str, components: list[str], edge_cases: list[str]) -> dict:
    """Start the TDD enforcement gate for a feature build.

    Args:
        mode: The build mode (e.g., 'build-py').
        feature: Feature name being built.
        components: Components under test.
        edge_cases: Edge cases to test.
    """
    return handle_start_tdd_gate(
        mode=mode, feature=feature, components=components,
        edge_cases=edge_cases, project_dir=_project(),
    )


@mcp.tool()
def check_tdd_status() -> dict:
    """Check the current status of the TDD enforcement gate."""
    return handle_check_tdd_status(project_dir=_project())


@mcp.tool()
def start_security_audit() -> dict:
    """Start a recursive security audit loop."""
    return handle_start_security_audit(project_dir=_project())


@mcp.tool()
def security_audit_summary() -> dict:
    """Get a summary of the security audit (findings, convergence, severity breakdown)."""
    return handle_security_audit_summary(project_dir=_project())


@mcp.tool()
def start_design_validation() -> dict:
    """Start the design validation gate (WCAG, brand, handoff checks)."""
    return handle_start_design_validation(project_dir=_project())


@mcp.tool()
def design_validation_summary() -> dict:
    """Get a summary of design validation results."""
    return handle_design_validation_summary(project_dir=_project())


@mcp.tool()
def check_contrast(foreground: str, background: str) -> dict:
    """Check contrast ratio between two hex colors for WCAG compliance.

    Args:
        foreground: Foreground hex color (e.g., '#000000').
        background: Background hex color (e.g., '#FFFFFF').
    """
    return handle_check_contrast(foreground=foreground, background=background)


@mcp.tool()
def verify_health() -> dict:
    """Run all health checks (static + liveness) and return a combined report.

    Returns static checks (session, hooks, MCP, modes, etc.) and liveness checks
    (hook completeness, conversation logging, log consistency, MCP loadable,
    session freshness, hook command validity) with a pass/fail summary.
    """
    return handle_verify_health(project_dir=_project(), home=_home())


@mcp.tool()
def audit_script_8b(script_content: str, risk_level: str) -> dict:
    """Gate 4: Run an adversarial security audit on a script using a small (8B) model.

    Sends the script to an 8B LLM for independent security review.
    Returns findings with severity levels. Skips gracefully if Ollama is unavailable.
    """
    return handle_audit_script_8b(script_content=script_content, risk_level=risk_level)


@mcp.tool()
def audit_script_32b(script_content: str, risk_level: str) -> dict:
    """Gate 5: Run a second-opinion security audit using a large (32B) model.

    Only runs for high-risk scripts. Provides structural review from a larger model.
    Skips gracefully if Ollama is unavailable or script is not high-risk.
    """
    return handle_audit_script_32b(script_content=script_content, risk_level=risk_level)


@mcp.tool()
def check_processor_thresholds() -> dict:
    """Check which background processing thresholds are exceeded.

    Returns which processors are due to run based on correction queue size,
    interaction count, and digest age.
    """
    return handle_check_processor_thresholds(project_dir=_project(), home=_home())


@mcp.tool()
def run_background_processors() -> dict:
    """Run all due background processors (correction extraction, digest generation, mode audit).

    Only runs processors whose thresholds are exceeded. Safe to call frequently —
    processors are idempotent and update state after running.
    """
    return handle_run_background_processors(project_dir=_project(), home=_home())


@mcp.tool()
def get_processor_status() -> dict:
    """Get when each background processor last ran (corrections, digest, mode audit)."""
    return handle_get_processor_status(project_dir=_project())


@mcp.tool()
def register_project() -> dict:
    """Register the current project for cross-project aggregation and analytics."""
    return handle_register_project(project_dir=_project(), home=_home())


@mcp.tool()
def get_cross_project_digest(date: str | None = None) -> dict:
    """Generate a digest spanning all registered projects.

    Args:
        date: Date in YYYY-MM-DD format. Omit for today.
    """
    return handle_get_cross_project_digest(home=_home(), date=date)


@mcp.tool()
def figma_get_tokens(file_key: str, token: str) -> dict:
    """Extract design tokens (colors, typography, spacing) from a Figma file.

    Args:
        file_key: The Figma file key (from the URL).
        token: Figma personal access token.
    """
    return handle_figma_get_tokens(file_key=file_key, token=token)


@mcp.tool()
def figma_get_components(file_key: str, token: str) -> dict:
    """Get the component library from a Figma file.

    Args:
        file_key: The Figma file key (from the URL).
        token: Figma personal access token.
    """
    return handle_figma_get_components(file_key=file_key, token=token)


# ---------------------------------------------------------------------------
# Build-in-public
# ---------------------------------------------------------------------------

@mcp.tool()
def bip_generate(
    platform: str = "x",
    force: bool = False,
    event: str | None = None,
) -> dict:
    """Check triggers and gather content for a build-in-public draft.

    Returns gathered context (commits, corrections, knowledge) and voice rules.
    Use the returned context to write a draft, then call bip_approve to queue it.

    Args:
        platform: Target platform (x, reddit, blog). Default: x.
        force: Bypass cooldown and threshold checks.
        event: High-signal event name (test_green, crux_switch, etc.) to trigger immediately.
    """
    return handle_bip_generate(
        project_dir=_project(), home=_home(),
        platform=platform, force=force, event=event,
    )


@mcp.tool()
def bip_approve(
    draft_text: str,
    source_keys: list[str] | None = None,
    publish_at: str | None = None,
) -> dict:
    """Approve a BIP draft — save it and queue to Typefully.

    Args:
        draft_text: The approved draft text. For threads, separate tweets with blank lines.
        source_keys: Source keys for dedup (e.g. ["git:abc123", "correction:001"]).
        publish_at: Optional ISO 8601 UTC timestamp for scheduled publishing.
    """
    return handle_bip_approve(
        project_dir=_project(),
        draft_text=draft_text,
        source_keys=source_keys,
        publish_at=publish_at,
    )


@mcp.tool()
def bip_status() -> dict:
    """Get current build-in-public state — counters, cooldown, recent posts."""
    return handle_bip_status(project_dir=_project())


@mcp.tool()
def bip_get_analytics(
    github_repo: str | None = None,
    github_token: str | None = None,
    refresh: bool = False,
) -> dict:
    """Get BIP engagement analytics — Typefully stats, GitHub stars/forks, blog traffic.

    Args:
        github_repo: Optional repo in "owner/repo" format for GitHub stats.
        github_token: Optional GitHub personal access token for higher rate limits.
        refresh: If True, fetch fresh data from APIs. Otherwise returns cached analytics.
    """
    return handle_bip_get_analytics(
        project_dir=_project(),
        github_repo=github_repo,
        github_token=github_token,
        refresh=refresh,
    )


@mcp.tool()
def get_model_for_task(task_type: str) -> dict:
    """Get the recommended model for a task type.

    Task types: plan_audit, code_audit, security_audit, doc_audit,
    fix_generation, independence, title, compaction, write, e2e_test.

    Returns the best available model for the task's tier, considering
    which providers have credentials configured.

    Args:
        task_type: The type of task to get a model for.
    """
    from scripts.lib.crux_model_tiers import (
        TASK_ROUTING,
        get_task_model,
        resolve_tier,
    )
    tier = TASK_ROUTING.get(task_type, "standard")
    model = get_task_model(task_type)
    return {
        "task_type": task_type,
        "tier": tier,
        "model": model,
        "available": model is not None,
    }


@mcp.tool()
def get_available_tiers() -> dict:
    """Show what model is available at each tier.

    Tiers (low to high): micro, fast, local, standard, frontier.
    Each tier resolves to the best available model based on provider credentials.
    """
    from scripts.lib.crux_model_tiers import get_available_tiers as _get_tiers
    return _get_tiers()


@mcp.tool()
def get_mode_model(mode: str, role: str = "primary") -> dict:
    """Get the recommended model for a Crux mode.

    Each mode has a preferred tier for its primary task and optionally
    for auditing. For example, build-py uses 'local' for coding but
    'fast' for audit checks.

    Args:
        mode: The Crux mode name (e.g., "build-py", "plan", "review").
        role: "primary" for the main task, "audit" for audit checks.
    """
    from scripts.lib.crux_model_tiers import (
        MODE_TIERS,
        get_mode_model as _get_mode_model,
    )
    mode_config = MODE_TIERS.get(mode, {})
    tier = mode_config.get(role, "standard")
    model = _get_mode_model(mode, role)
    return {
        "mode": mode,
        "role": role,
        "tier": tier,
        "model": model,
        "available": model is not None,
    }


@mcp.tool()
def get_model_quality_stats() -> dict:
    """Get model quality statistics — success rates per task type and tier.

    Shows how often each model tier succeeds without escalation.
    Use this to understand which tasks need better models.
    """
    from scripts.lib.crux_model_quality import get_quality_stats
    return get_quality_stats()


# ---------------------------------------------------------------------------
# Impact analysis
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_impact(
    prompt: str,
    top_n: int = 20,
    include_reasons: bool = True,
) -> dict:
    """Rank files by relevance to a prompt using git history, keywords, and LSP.

    Returns the top N files most likely to be relevant to the described task,
    scored by keyword match, git churn, LSP symbols, and proximity.

    Args:
        prompt: Natural language description of the task (e.g. "add OAuth2 login flow").
        top_n: Maximum number of files to return (default 20).
        include_reasons: Include per-dimension score breakdown (default True).
    """
    from scripts.lib.impact.scorer import rank_files
    results = rank_files(
        root=_project(),
        prompt=prompt,
        top_n=top_n,
        include_reasons=include_reasons,
    )
    return {
        "files": [
            {"path": r.path, "score": r.score, "reasons": r.reasons}
            for r in results
        ],
        "total": len(results),
        "prompt": prompt,
    }


# ---------------------------------------------------------------------------
# Memory system
# ---------------------------------------------------------------------------

@mcp.tool()
def remember_fact(fact: str, scope: str = "project") -> dict:
    """Remember a fact for future sessions.

    Facts persist across sessions and tool switches. They are stored in
    .crux/memory/ (project scope) or ~/.crux/memory/ (user scope).

    Args:
        fact: The fact to remember (e.g., "this project uses PostgreSQL 15").
        scope: 'project' (default) or 'user' (cross-project).
    """
    from scripts.lib.crux_memory import remember
    crux_dir = os.path.join(_project(), ".crux") if scope == "project" else os.path.join(_home(), ".crux")
    return remember(fact, scope, crux_dir)


@mcp.tool()
def recall_memories(query: str, scope: str = "project") -> dict:
    """Search memories by keyword.

    Args:
        query: Search term to match against stored facts.
        scope: 'project' or 'user'.
    """
    from scripts.lib.crux_memory import recall
    crux_dir = os.path.join(_project(), ".crux") if scope == "project" else os.path.join(_home(), ".crux")
    return recall(query, scope, crux_dir)


@mcp.tool()
def forget_fact(memory_id: str, scope: str = "project") -> dict:
    """Forget a memory by its ID.

    Args:
        memory_id: ID of the memory to remove.
        scope: 'project' or 'user'.
    """
    from scripts.lib.crux_memory import forget_memory
    crux_dir = os.path.join(_project(), ".crux") if scope == "project" else os.path.join(_home(), ".crux")
    return forget_memory(memory_id, scope, crux_dir)


@mcp.tool()
def list_all_memories(scope: str = "project") -> dict:
    """List all stored memories.

    Args:
        scope: 'project' or 'user'.
    """
    from scripts.lib.crux_memory import load_memories
    crux_dir = os.path.join(_project(), ".crux") if scope == "project" else os.path.join(_home(), ".crux")
    entries = load_memories(scope, crux_dir)
    return {
        "memories": [
            {"id": e.id, "fact": e.fact, "confidence": e.confidence,
             "use_count": e.use_count, "source": e.source}
            for e in entries
        ],
        "total": len(entries),
        "scope": scope,
    }


# ---------------------------------------------------------------------------
# Git context
# ---------------------------------------------------------------------------

@mcp.tool()
def git_context(filepath: str) -> dict:
    """Get git context for a file — recent history, risk score.

    Helps the AI make better edits by understanding version history.

    Args:
        filepath: Path to the file (relative to project root).
    """
    from scripts.lib.crux_git_context import get_file_history, get_risky_files
    history = get_file_history(_project(), filepath, n=5)
    risky = get_risky_files(_project(), top_n=20)
    risk = next((r for r in risky if r["file"] == filepath), None)
    return {
        "file": filepath,
        "recent_commits": history,
        "risk": risk,
    }


@mcp.tool()
def git_diff() -> dict:
    """Get current uncommitted changes (staged + unstaged)."""
    from scripts.lib.crux_git_context import get_current_diff, get_branch_context
    diff = get_current_diff(_project())
    branch = get_branch_context(_project())
    return {"diff": diff, "branch": branch}


@mcp.tool()
def git_risky_files(top_n: int = 10) -> dict:
    """Find files with highest churn — most likely to cause issues if edited.

    Args:
        top_n: Number of files to return (default 10).
    """
    from scripts.lib.crux_git_context import get_risky_files
    return {"files": get_risky_files(_project(), top_n=top_n)}


@mcp.tool()
def git_suggest_commit() -> dict:
    """Suggest a commit message from currently staged changes."""
    from scripts.lib.crux_git_context import suggest_commit_message
    msg = suggest_commit_message(_project())
    return {"message": msg, "has_staged": bool(msg)}


# ---------------------------------------------------------------------------
# Codebase indexing
# ---------------------------------------------------------------------------

@mcp.tool()
def search_code(query: str) -> dict:
    """Search the codebase for files and symbols matching a query.

    Searches file paths, function/class/constant names, and module names.
    Returns ranked results with file, symbol, and line number.

    Args:
        query: Search term (e.g., 'AuthService', 'login', 'database').
    """
    from scripts.lib.crux_index import search_index
    results = search_index(query, _project())
    return {"results": results[:20], "total": len(results), "query": query}


@mcp.tool()
def index_codebase() -> dict:
    """Build or refresh the codebase index.

    Scans all source files, extracts symbols (functions, classes, constants),
    and persists the index for fast search.
    """
    from scripts.lib.crux_index import build_catalog, save_index, index_stats
    catalog = build_catalog(_project())
    crux_dir = os.path.join(_project(), ".crux")
    save_index(catalog, crux_dir)
    return index_stats(_project())


# ---------------------------------------------------------------------------
# External MCP server registry
# ---------------------------------------------------------------------------

@mcp.tool()
def register_mcp_server(
    name: str,
    command: str,
    env: str = "{}",
    allowed_tools: str = "",
    timeout: int = 30,
) -> dict:
    """Register an external MCP server for aggregation.

    Configure external MCP servers once in Crux, and every connected tool
    gets access to them. Servers require explicit registration (no auto-discovery).

    Args:
        name: Server identifier (e.g., 'github', 'postgres').
        command: JSON array of command + args (e.g., '["github-mcp-server"]').
        env: JSON object of environment variables (e.g., '{"TOKEN": "xxx"}').
        allowed_tools: Comma-separated tool allowlist (empty = all tools).
        timeout: Timeout in seconds (default 30).
    """
    import json as _json
    from scripts.lib.crux_mcp_registry import register_server
    cmd = _json.loads(command) if command.startswith("[") else [command]
    env_dict = _json.loads(env) if env.startswith("{") else {}
    tools_list = [t.strip() for t in allowed_tools.split(",") if t.strip()] or None
    return register_server(
        os.path.join(_project(), ".crux"),
        name=name, command=cmd, env=env_dict,
        allowed_tools=tools_list, timeout=timeout,
    )


@mcp.tool()
def remove_mcp_server(name: str) -> dict:
    """Remove an external MCP server from the registry.

    Args:
        name: Server identifier to remove.
    """
    from scripts.lib.crux_mcp_registry import remove_server
    return remove_server(os.path.join(_project(), ".crux"), name)


@mcp.tool()
def list_mcp_servers() -> dict:
    """List all registered external MCP servers with their status."""
    from scripts.lib.crux_mcp_registry import list_servers
    return list_servers(os.path.join(_project(), ".crux"))


async def run():  # pragma: no cover — starts blocking stdio server
    """Run the MCP server on stdio transport."""
    await mcp.run_stdio_async()


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    asyncio.run(run())
