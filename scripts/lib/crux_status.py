"""Crux runtime status and health reporting.

Provides insight into the live state of Crux:
- Session state (mode, tool, working context)
- Hook status (active, events registered)
- Interaction logging (today's count, tool breakdown)
- Correction capture (total, by category)
- Knowledge entries (count, names)
- MCP server registration
- Pending tasks

Used by `crux status` CLI command.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.crux_paths import get_project_paths, get_user_paths
from scripts.lib.crux_session import load_session

REQUIRED_HOOKS = {"SessionStart", "PostToolUse", "UserPromptSubmit", "Stop"}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_json_safe(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# get_status — collect all runtime data
# ---------------------------------------------------------------------------

def get_status(project_dir: str, home: str) -> dict:
    """Collect full Crux runtime status."""
    project_paths = get_project_paths(project_dir)
    user_paths = get_user_paths(home)
    crux_dir = str(project_paths.root)

    status: dict = {}

    # Session
    session = load_session(crux_dir)
    status["session"] = {
        "active_mode": session.active_mode,
        "active_tool": session.active_tool,
        "working_on": session.working_on,
        "updated_at": session.updated_at,
        "decisions": len(session.key_decisions),
    }

    # Knowledge
    kb_dir = project_paths.knowledge
    kb_entries: list[str] = []
    if os.path.isdir(kb_dir):
        kb_entries = [p.stem for p in Path(kb_dir).glob("*.md")]
    status["knowledge"] = {
        "project_entries": len(kb_entries),
        "entry_names": sorted(kb_entries),
    }

    # Modes
    modes_dir = user_paths.modes
    mode_names: list[str] = []
    if os.path.isdir(modes_dir):
        mode_names = [p.stem for p in Path(modes_dir).glob("*.md") if p.stem != "_template"]
    status["modes"] = {
        "total": len(mode_names),
        "available": sorted(mode_names),
    }

    # Hooks
    hooks_data = _check_hooks(project_dir)
    status["hooks"] = hooks_data

    # Interactions
    status["interactions"] = _count_today_interactions(project_dir)

    # Corrections
    status["corrections"] = _count_corrections(project_dir)

    # MCP
    status["mcp"] = _check_mcp(project_dir)

    # Pending
    status["pending"] = {
        "count": len(session.pending),
        "items": list(session.pending),
    }

    # Files
    status["files"] = {
        "tracked": len(session.files_touched),
    }

    return status


def _check_hooks(project_dir: str) -> dict:
    """Check if Claude Code hooks are configured."""
    settings_path = os.path.join(project_dir, ".claude", "settings.local.json")
    settings = _load_json_safe(settings_path)

    hooks = settings.get("hooks", {})
    events = [k for k, v in hooks.items() if v]

    return {
        "active": len(events) > 0,
        "events_registered": len(events),
        "events": events,
    }


def _count_today_interactions(project_dir: str) -> dict:
    """Count today's interactions from the log."""
    project_paths = get_project_paths(project_dir)
    log_dir = os.path.join(str(project_paths.root), "analytics", "interactions")
    log_file = os.path.join(log_dir, f"{_today()}.jsonl")

    if not os.path.exists(log_file):
        return {"today": 0, "tool_breakdown": {}}

    tools: Counter = Counter()
    count = 0
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                tools[entry.get("tool_name", "unknown")] += 1
                count += 1
            except json.JSONDecodeError:
                continue

    return {
        "today": count,
        "tool_breakdown": dict(tools.most_common()),
    }


def _count_corrections(project_dir: str) -> dict:
    """Count all corrections."""
    project_paths = get_project_paths(project_dir)
    corr_file = project_paths.corrections_file

    if not os.path.exists(corr_file):
        return {"total": 0, "by_category": {}}

    categories: Counter = Counter()
    total = 0
    with open(corr_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                categories[entry.get("category", "unknown")] += 1
                total += 1
            except json.JSONDecodeError:
                continue

    return {
        "total": total,
        "by_category": dict(categories.most_common()),
    }


def _check_mcp(project_dir: str) -> dict:
    """Check MCP server registration."""
    mcp_path = os.path.join(project_dir, ".claude", "mcp.json")
    mcp_config = _load_json_safe(mcp_path)

    registered = "crux" in mcp_config.get("mcpServers", {})

    result: dict = {"registered": registered}
    if registered:
        # Import to count tools
        try:
            from scripts.lib.crux_mcp_server import mcp as mcp_server
            result["tool_count"] = len(mcp_server._tool_manager._tools)
        except Exception:
            result["tool_count"] = 0
    return result


# ---------------------------------------------------------------------------
# format_status — human-readable output
# ---------------------------------------------------------------------------

def format_status(status: dict) -> str:
    """Format status dict into human-readable output."""
    lines: list[str] = []

    # Session
    s = status["session"]
    lines.append("SESSION")
    lines.append(f"  Mode: {s['active_mode']}")
    lines.append(f"  Tool: {s['active_tool']}")
    if s["working_on"]:
        lines.append(f"  Working on: {s['working_on']}")
    lines.append(f"  Decisions: {s['decisions']}")
    lines.append(f"  Updated: {s['updated_at']}")
    lines.append("")

    # Hooks
    h = status["hooks"]
    hook_label = "ACTIVE" if h["active"] else "INACTIVE"
    lines.append(f"HOOKS: {hook_label}")
    if h["active"]:
        lines.append(f"  Events: {', '.join(h['events'])}")
    lines.append("")

    # Interactions
    i = status["interactions"]
    lines.append(f"INTERACTIONS: {i['today']} today")
    if i["tool_breakdown"]:
        for tool, count in sorted(i["tool_breakdown"].items(), key=lambda x: -x[1]):
            lines.append(f"  {tool}: {count}")
    lines.append("")

    # Corrections
    c = status["corrections"]
    lines.append(f"CORRECTIONS: {c['total']} total")
    if c["by_category"]:
        for cat, count in c["by_category"].items():
            lines.append(f"  {cat}: {count}")
    lines.append("")

    # Knowledge
    k = status["knowledge"]
    lines.append(f"KNOWLEDGE: {k['project_entries']} entries")
    if k["entry_names"]:
        for name in k["entry_names"]:
            lines.append(f"  {name}")
    lines.append("")

    # MCP
    m = status["mcp"]
    mcp_label = f"REGISTERED ({m.get('tool_count', 0)} tools)" if m["registered"] else "NOT REGISTERED"
    lines.append(f"MCP: {mcp_label}")
    lines.append("")

    # Modes
    md = status["modes"]
    lines.append(f"MODES: {md['total']} available")
    lines.append("")

    # Files
    lines.append(f"FILES TRACKED: {status['files']['tracked']}")
    lines.append("")

    # Pending
    p = status["pending"]
    if p["count"] > 0:
        lines.append(f"PENDING: {p['count']} items")
        for item in p["items"]:
            lines.append(f"  - {item}")
    else:
        lines.append("PENDING: none")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# check_health — pass/fail checks
# ---------------------------------------------------------------------------

def check_health(project_dir: str, home: str) -> list[dict]:
    """Run health checks and return pass/fail results."""
    status = get_status(project_dir=project_dir, home=home)
    checks: list[dict] = []

    # Session exists
    checks.append({
        "name": "Session state",
        "passed": bool(status["session"]["active_mode"]),
        "message": f"Mode: {status['session']['active_mode']}, Tool: {status['session']['active_tool']}",
    })

    # Hooks active
    h = status["hooks"]
    checks.append({
        "name": "Hooks active",
        "passed": h["active"],
        "message": f"{h['events_registered']} events registered" if h["active"] else "No hooks configured",
    })

    # Interactions logging
    i = status["interactions"]
    checks.append({
        "name": "Interaction logging",
        "passed": i["today"] > 0,
        "message": f"{i['today']} interactions today" if i["today"] > 0 else "No interactions logged today",
    })

    # Corrections
    c = status["corrections"]
    checks.append({
        "name": "Correction capture",
        "passed": True,  # always passes — 0 corrections is fine
        "message": f"{c['total']} corrections captured" if c["total"] > 0 else "No corrections yet (normal for new sessions)",
    })

    # Knowledge
    k = status["knowledge"]
    checks.append({
        "name": "Knowledge base",
        "passed": k["project_entries"] > 0,
        "message": f"{k['project_entries']} entries" if k["project_entries"] > 0 else "No knowledge entries",
    })

    # MCP
    m = status["mcp"]
    checks.append({
        "name": "MCP server",
        "passed": m["registered"],
        "message": f"Registered with {m.get('tool_count', 0)} tools" if m["registered"] else "Not registered",
    })

    # Modes
    md = status["modes"]
    checks.append({
        "name": "Modes available",
        "passed": md["total"] > 0,
        "message": f"{md['total']} modes" if md["total"] > 0 else "No modes found",
    })

    return checks


# ---------------------------------------------------------------------------
# check_liveness — runtime verification that components are actually working
# ---------------------------------------------------------------------------

def check_liveness(project_dir: str, home: str) -> list[dict]:
    """Run liveness checks that verify components are producing data at runtime."""
    project_paths = get_project_paths(project_dir)
    crux_dir = str(project_paths.root)
    checks: list[dict] = []

    # --- Hook completeness ---
    settings_path = os.path.join(project_dir, ".claude", "settings.local.json")
    settings = _load_json_safe(settings_path)
    hooks = settings.get("hooks", {})
    registered_events = {k for k, v in hooks.items() if v}
    missing = REQUIRED_HOOKS - registered_events
    if not registered_events:
        checks.append({
            "name": "Hook completeness",
            "passed": False,
            "message": f"No hooks configured. Required: {', '.join(sorted(REQUIRED_HOOKS))}",
        })
    elif missing:
        checks.append({
            "name": "Hook completeness",
            "passed": False,
            "message": f"Missing hooks: {', '.join(sorted(missing))}",
        })
    else:
        checks.append({
            "name": "Hook completeness",
            "passed": True,
            "message": f"All {len(REQUIRED_HOOKS)} required hooks registered",
        })

    # --- Conversation logging ---
    today = _today()
    conv_dir = os.path.join(crux_dir, "analytics", "conversations")
    conv_file = os.path.join(conv_dir, f"{today}.jsonl")
    has_conversations = os.path.exists(conv_file) and os.path.getsize(conv_file) > 0
    checks.append({
        "name": "Conversation logging",
        "passed": has_conversations,
        "message": "Today's conversation log exists" if has_conversations else "No conversation log for today",
    })

    # --- Log consistency ---
    int_dir = os.path.join(crux_dir, "analytics", "interactions")
    int_file = os.path.join(int_dir, f"{today}.jsonl")
    has_interactions = os.path.exists(int_file) and os.path.getsize(int_file) > 0
    if has_interactions and not has_conversations:
        checks.append({
            "name": "Log consistency",
            "passed": False,
            "message": "Interactions logged but no conversations — UserPromptSubmit hook may be broken",
        })
    else:
        checks.append({
            "name": "Log consistency",
            "passed": True,
            "message": "Interaction and conversation logs are consistent",
        })

    # --- MCP server loadable ---
    # Use venv Python if available, otherwise fall back to system Python
    user_paths = get_user_paths(home)
    crux_home = str(user_paths.root)
    venv_python = Path(crux_home) / ".venv" / "bin" / "python"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"
    mcp_test_code = """
import sys
sys.path.insert(0, '{crux_home}')
from scripts.lib.crux_mcp_server import mcp as mcp_server
print(len(mcp_server._tool_manager._tools))
""".format(crux_home=crux_home)
    try:
        result = subprocess.run(
            [python_cmd, "-c", mcp_test_code],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "PYTHONPATH": crux_home},
        )
        if result.returncode == 0:
            tool_count = int(result.stdout.strip())
            checks.append({
                "name": "MCP loadable",
                "passed": True,
                "message": f"MCP server loaded with {tool_count} tools",
            })
        else:
            error_msg = result.stderr.strip().split('\n')[-1] if result.stderr else "Unknown error"
            checks.append({
                "name": "MCP loadable",
                "passed": False,
                "message": f"MCP server failed to load: {error_msg}",
            })
    except subprocess.TimeoutExpired:
        checks.append({
            "name": "MCP loadable",
            "passed": False,
            "message": "MCP server check timed out",
        })
    except Exception as exc:
        checks.append({
            "name": "MCP loadable",
            "passed": False,
            "message": f"MCP server failed to load: {exc}",
        })

    # --- Session freshness ---
    session = load_session(crux_dir)
    try:
        updated = datetime.strptime(session.updated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
        if age_hours > 24:
            checks.append({
                "name": "Session freshness",
                "passed": False,
                "message": f"Session is stale — last updated {age_hours:.0f} hours ago",
            })
        else:
            checks.append({
                "name": "Session freshness",
                "passed": True,
                "message": f"Session updated {age_hours:.1f} hours ago",
            })
    except (ValueError, AttributeError):
        checks.append({
            "name": "Session freshness",
            "passed": False,
            "message": "Could not parse session updated_at timestamp",
        })

    # --- Hook command valid ---
    if not registered_events:
        checks.append({
            "name": "Hook command valid",
            "passed": True,
            "message": "No hooks configured — skipping command validation",
        })
    else:
        # Check the first command from the first hook event
        all_commands_valid = True
        bad_commands: list[str] = []
        for event, matchers in hooks.items():
            if not matchers:
                continue
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    cmd = hook.get("command", "")
                    if not cmd:
                        continue
                    # Extract the executable, skipping env var assignments (KEY=val)
                    tokens = cmd.split()
                    executable = ""
                    for token in tokens:
                        if "=" in token and not token.startswith("/"):
                            continue  # Skip env var assignments like PYTHONPATH=...
                        executable = token
                        break
                    if executable and not os.path.isfile(executable):
                        all_commands_valid = False
                        bad_commands.append(executable)
        if all_commands_valid:
            checks.append({
                "name": "Hook command valid",
                "passed": True,
                "message": "All hook commands reference valid executables",
            })
        else:
            checks.append({
                "name": "Hook command valid",
                "passed": False,
                "message": f"Command not found: {', '.join(bad_commands)}",
            })

    # --- Audit backend available (PLAN-169) ---
    try:
        from scripts.lib.crux_audit_backend import get_backend_status
        backend_status = get_backend_status()
        active = backend_status["active_backend"]

        # Check passes if any backend is available (not just Ollama)
        is_disabled = "DISABLED" in active
        checks.append({
            "name": "Audit backend",
            "passed": not is_disabled,
            "message": f"Active: {active}",
        })

        # Additional info about fallback availability
        if not backend_status["ollama_available"] and backend_status["claude_available"]:
            checks.append({
                "name": "Audit fallback",
                "passed": True,
                "message": "Ollama down, using Claude subagent fallback",
            })
        elif is_disabled:
            checks.append({
                "name": "Audit fallback",
                "passed": False,
                "message": "No audit backend available (Ollama down, Claude CLI not found)",
            })
    except Exception as exc:
        checks.append({
            "name": "Audit backend",
            "passed": False,
            "message": f"Could not check audit backend: {exc}",
        })

    # --- Background processor status ---
    try:
        from scripts.lib.crux_background_processor import get_processor_status
        proc_status = get_processor_status(project_dir)
        never_run = [k for k, v in proc_status.items() if v == "never"]
        if never_run:
            checks.append({
                "name": "Background processor",
                "passed": True,
                "message": f"Processors not yet run: {', '.join(never_run)} (normal for new projects)",
            })
        else:
            checks.append({
                "name": "Background processor",
                "passed": True,
                "message": "All processors have run at least once",
            })
    except Exception:
        checks.append({
            "name": "Background processor",
            "passed": False,
            "message": "Could not check processor status",
        })

    # --- Cross-project registry ---
    user_paths = get_user_paths(home)
    registry_path = os.path.join(str(user_paths.root), "projects.json")
    if os.path.exists(registry_path):
        reg_data = _load_json_safe(registry_path)
        project_count = len(reg_data.get("projects", []))
        checks.append({
            "name": "Cross-project registry",
            "passed": True,
            "message": f"{project_count} project(s) registered",
        })
    else:
        checks.append({
            "name": "Cross-project registry",
            "passed": True,
            "message": "No projects registered yet (run register_project to enable cross-project analytics)",
        })

    # --- Figma token ---
    figma_token = os.environ.get("FIGMA_TOKEN")
    checks.append({
        "name": "Figma token",
        "passed": True,
        "message": "FIGMA_TOKEN is set" if figma_token else "FIGMA_TOKEN not set (optional — needed for design token imports)",
    })

    return checks


# ---------------------------------------------------------------------------
# verify_health — combined static + liveness report
# ---------------------------------------------------------------------------

def generate_findings(status: dict, health: dict) -> list[dict]:
    """Generate actionable findings and recommendations from status and health data.

    Each finding has: severity (critical|warning|info|positive), title, detail.
    """
    findings: list[dict] = []

    # --- Critical: any failed health checks ---
    failed_checks = [
        c for c in health.get("static", []) + health.get("liveness", [])
        if not c["passed"]
    ]
    for c in failed_checks:
        findings.append({
            "severity": "critical",
            "title": f"{c['name']} failed",
            "detail": c["message"],
        })

    # --- Session staleness ---
    s = status.get("session", {})
    try:
        updated = datetime.strptime(s.get("updated_at", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
        if age_hours > 12:
            findings.append({
                "severity": "warning",
                "title": "Session is stale",
                "detail": f"Last updated {age_hours:.1f}h ago. Consider updating working_on to reflect current task.",
            })
    except (ValueError, AttributeError):
        pass

    # --- Correction patterns ---
    c = status.get("corrections", {})
    if c.get("total", 0) >= 5:
        top_cat = max(c.get("by_category", {}).items(), key=lambda x: x[1], default=None)
        if top_cat:
            findings.append({
                "severity": "warning",
                "title": f"{c['total']} corrections accumulated",
                "detail": f"Top category: {top_cat[0]} ({top_cat[1]}). Run background processors to extract knowledge.",
            })
    elif c.get("total", 0) == 0:
        findings.append({
            "severity": "info",
            "title": "No corrections captured yet",
            "detail": "Corrections are auto-detected from user prompts. The system learns from these over time.",
        })

    # --- Interaction volume ---
    i = status.get("interactions", {})
    today_count = i.get("today", 0)
    if today_count > 500:
        findings.append({
            "severity": "info",
            "title": f"High activity: {today_count} interactions today",
            "detail": "Background processors will trigger automatically when thresholds are met.",
        })
    elif today_count == 0:
        findings.append({
            "severity": "warning",
            "title": "No interactions logged today",
            "detail": "Hook-based logging may not be active. Check PostToolUse hook configuration.",
        })

    # --- Knowledge base ---
    k = status.get("knowledge", {})
    if k.get("project_entries", 0) == 0:
        findings.append({
            "severity": "warning",
            "title": "Empty knowledge base",
            "detail": "Add knowledge entries to .crux/knowledge/ or use promote_knowledge to promote from corrections.",
        })
    elif k.get("project_entries", 0) >= 10:
        findings.append({
            "severity": "positive",
            "title": f"Rich knowledge base: {k['project_entries']} entries",
            "detail": "Consider promoting top entries to user scope (~/.crux/knowledge/) for cross-project use.",
        })

    # --- Pending tasks ---
    p = status.get("pending", {})
    if p.get("count", 0) > 10:
        findings.append({
            "severity": "warning",
            "title": f"{p['count']} pending tasks",
            "detail": "Consider triaging — archive completed items, prioritize the rest.",
        })

    # --- MCP tool count ---
    m = status.get("mcp", {})
    if m.get("registered") and m.get("tool_count", 0) > 0:
        findings.append({
            "severity": "positive",
            "title": f"MCP server active with {m['tool_count']} tools",
            "detail": "All Crux capabilities are available via MCP protocol.",
        })

    # --- Modes ---
    md = status.get("modes", {})
    if md.get("total", 0) > 0:
        findings.append({
            "severity": "positive",
            "title": f"{md['total']} modes available",
            "detail": f"Active: {s.get('active_mode', 'unknown')}. Switch modes to optimize for different task types.",
        })

    # --- Files tracked ---
    ft = status.get("files", {}).get("tracked", 0)
    if ft > 200:
        findings.append({
            "severity": "info",
            "title": f"{ft} files tracked this session",
            "detail": "Large file footprint. Review session scope if context is getting noisy.",
        })

    # --- Sort: critical first, then warning, info, positive ---
    severity_order = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 99))

    return findings


def format_findings(findings: list[dict]) -> str:
    """Format findings into human-readable output."""
    if not findings:
        return "FINDINGS\n  No findings to report."

    severity_icons = {
        "critical": "\033[0;31m✗\033[0m",
        "warning": "\033[1;33m!\033[0m",
        "info": "\033[0;36m·\033[0m",
        "positive": "\033[0;32m✓\033[0m",
    }

    lines: list[str] = ["FINDINGS"]
    for f in findings:
        icon = severity_icons.get(f["severity"], "·")
        lines.append(f"  {icon} {f['title']}")
        lines.append(f"    {f['detail']}")
    return "\n".join(lines)


def verify_health(project_dir: str, home: str) -> dict:
    """Run all health checks (static + liveness) and return a combined report."""
    static = check_health(project_dir=project_dir, home=home)
    liveness = check_liveness(project_dir=project_dir, home=home)

    all_checks = static + liveness
    total = len(all_checks)
    passed = sum(1 for c in all_checks if c["passed"])
    failed = total - passed

    return {
        "static": static,
        "liveness": liveness,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
        },
    }
