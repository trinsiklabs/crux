"""Generate tool-specific configs from .crux/ — the adapter layer.

Each tool (OpenCode, Claude Code, Cursor, etc.) has its own config format.
This module reads from .crux/ (source of truth) and generates the right
configs for each tool.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from scripts.lib.crux_paths import get_project_paths, get_user_paths
from scripts.lib.crux_security import (
    atomic_symlink,
    safe_glob_files,
    secure_makedirs,
    secure_write_file,
    validate_safe_filename,
)
from scripts.lib.crux_session import load_session, read_handoff, update_session

SUPPORTED_TOOLS = ("opencode", "claude-code", "cursor", "windsurf")

# Permission presets for OpenCode agent frontmatter
_PERM_FULL = {"read": "allow", "edit": "allow", "bash": "ask"}
_PERM_READONLY = {"read": "allow", "edit": "deny", "bash": "deny"}
_PERM_LIMITED = {"read": "allow", "edit": "deny", "bash": "deny", "webfetch": "deny"}

# Base Ollama model names for each variant
# OpenCode validates model names against the provider, so we must use real model names
# (not custom Modelfile aliases like crux-think). Temperature is set per-agent in frontmatter.
_MODEL_CODE = "ollama/qwen3-coder:30b"
_MODEL_THINK = "ollama/qwen3.5:27b"
_MODEL_CHAT = "ollama/qwen3.5:27b"

# OpenCode per-agent model routing metadata
# Maps mode names to OpenCode agent frontmatter fields (model, temperature, permission)
OPENCODE_AGENT_META: dict[str, dict] = {
    # Code modes — qwen3-coder:30b at temp 0.4
    "build-py":           {"model": _MODEL_CODE, "temperature": 0.4, "description": "Python development specialist", "permission": _PERM_FULL},
    "build-ex":           {"model": _MODEL_CODE, "temperature": 0.4, "description": "Elixir/Phoenix/Ash specialist", "permission": _PERM_FULL},
    "docker":             {"model": _MODEL_CODE, "temperature": 0.4, "description": "Container and Linux operations", "permission": _PERM_FULL},
    "test":               {"model": _MODEL_CODE, "temperature": 0.4, "description": "Test-first development specialist", "permission": _PERM_FULL},
    "design-ui":          {"model": _MODEL_CODE, "temperature": 0.4, "description": "UI component implementation", "permission": _PERM_FULL},
    "design-system":      {"model": _MODEL_CODE, "temperature": 0.4, "description": "Design system asset creation", "permission": _PERM_FULL},
    "design-responsive":  {"model": _MODEL_CODE, "temperature": 0.4, "description": "Responsive layout implementation", "permission": _PERM_FULL},
    # Think modes — qwen3.5:27b at temp 0.6
    "plan":               {"model": _MODEL_THINK, "temperature": 0.6, "description": "Software architecture planning", "permission": _PERM_READONLY},
    "infra-architect":    {"model": _MODEL_THINK, "temperature": 0.6, "description": "Infrastructure and deployment planning", "permission": _PERM_READONLY},
    "review":             {"model": _MODEL_THINK, "temperature": 0.6, "description": "Code review specialist", "permission": _PERM_READONLY},
    "debug":              {"model": _MODEL_THINK, "temperature": 0.6, "description": "Root cause analysis and debugging", "permission": _PERM_FULL},
    "legal":              {"model": _MODEL_THINK, "temperature": 0.6, "description": "Legal research and analysis", "permission": _PERM_LIMITED},
    "strategist":         {"model": _MODEL_THINK, "temperature": 0.6, "description": "First principles strategic analysis", "permission": _PERM_LIMITED},
    "psych":              {"model": _MODEL_THINK, "temperature": 0.6, "description": "ACT/Attachment therapeutic support", "permission": _PERM_READONLY},
    "security":           {"model": _MODEL_THINK, "temperature": 0.6, "description": "Adversarial vulnerability analysis", "permission": _PERM_READONLY},
    "design-review":      {"model": _MODEL_THINK, "temperature": 0.6, "description": "Design quality and accessibility review", "permission": _PERM_READONLY},
    "design-accessibility": {"model": _MODEL_THINK, "temperature": 0.6, "description": "WCAG accessibility specialist", "permission": _PERM_READONLY},
    # Chat modes — qwen3.5:27b at temp 0.7
    "writer":             {"model": _MODEL_CHAT, "temperature": 0.7, "description": "Professional technical writing", "permission": _PERM_LIMITED},
    "analyst":            {"model": _MODEL_CHAT, "temperature": 0.7, "description": "Data analysis specialist", "permission": _PERM_FULL},
    "explain":            {"model": _MODEL_CHAT, "temperature": 0.7, "description": "Teaching and mentoring", "permission": _PERM_READONLY},
    "mac":                {"model": _MODEL_CHAT, "temperature": 0.7, "description": "macOS system operations", "permission": _PERM_LIMITED},
    "ai-infra":           {"model": _MODEL_CHAT, "temperature": 0.7, "description": "AI/LLM infrastructure management", "permission": _PERM_FULL},
    "marketing":          {"model": _MODEL_CHAT, "temperature": 0.7, "description": "Marketing strategy and copywriting", "permission": _PERM_READONLY},
    "build-in-public":    {"model": _MODEL_CHAT, "temperature": 0.7, "description": "Shipping update content for build-in-public", "permission": _PERM_FULL},
}

# Claude Code agent frontmatter metadata (tool list format differs from OpenCode)
_MODE_META = {
    "build-py": {"description": "Python development specialist", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "build-ex": {"description": "Elixir/Phoenix/Ash specialist", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "plan": {"description": "Software architecture planning", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "infra-architect": {"description": "Infrastructure and deployment planning", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "review": {"description": "Code review specialist", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "debug": {"description": "Root cause analysis and debugging", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "explain": {"description": "Teaching and mentoring", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "analyst": {"description": "Data analysis specialist", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "writer": {"description": "Professional technical writing", "tools": "Read, Write, Grep, Glob"},
    "psych": {"description": "ACT/Attachment therapeutic support", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "legal": {"description": "Legal research and analysis", "tools": "Read, Write, Grep, Glob"},
    "strategist": {"description": "First principles strategic analysis", "tools": "Read, Grep, Glob"},
    "ai-infra": {"description": "AI/LLM infrastructure management", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "mac": {"description": "macOS system operations", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "docker": {"description": "Container and Linux operations", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "marketing": {"description": "Marketing strategy and copywriting", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "build-in-public": {"description": "Shipping update content for build-in-public", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "test": {"description": "Test-first development specialist", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "security": {"description": "Adversarial vulnerability analysis", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "design-ui": {"description": "UI component implementation", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "design-review": {"description": "Design quality and accessibility review", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
    "design-system": {"description": "Design system asset creation", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "design-responsive": {"description": "Responsive layout implementation", "tools": "Read, Write, Edit, Bash, Grep, Glob"},
    "design-accessibility": {"description": "WCAG accessibility specialist", "tools": "Read, Grep, Glob", "permissionMode": "plan"},
}


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from markdown content.

    Frontmatter must start at the very beginning of the file with '---'
    and end with a closing '---' line.
    """
    if not content.startswith("---\n"):
        return content
    # Find closing delimiter (skip the opening ---)
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        # Check if it ends with ---\n (no body after)
        if content.endswith("\n---\n") or content.endswith("\n---"):
            end_idx = content.rfind("\n---")
        else:
            return content  # No closing delimiter
    # Skip past the closing --- and any leading whitespace/newlines
    body = content[end_idx + 4 + 1:]  # +4 for \n--- and +1 for \n after ---
    return body.lstrip("\n")


@dataclass
class SyncResult:
    success: bool
    tool: str
    items_synced: list[str] = field(default_factory=list)
    error: str | None = None


def _safe_symlink(source: str, target: str) -> None:
    """Create a symlink atomically, removing any existing link/file at target.

    Uses atomic temp file + rename pattern to prevent TOCTOU race conditions.
    """
    # Use atomic_symlink which handles the temp+rename pattern
    # First, clean up any existing target atomically by renaming to temp then deleting
    if os.path.islink(target) or os.path.exists(target):
        target_dir = os.path.dirname(target)
        fd, temp_del = tempfile.mkstemp(dir=target_dir, prefix='.crux_del_')
        os.close(fd)
        os.unlink(temp_del)
        try:
            os.rename(target, temp_del)  # Atomic move existing out of the way
            if os.path.isdir(temp_del) and not os.path.islink(temp_del):
                shutil.rmtree(temp_del)
            else:
                os.unlink(temp_del)
        except OSError:
            pass
    atomic_symlink(source, target)


def _safe_write(path: str, content: str) -> None:
    """Write content to a file with secure permissions, creating parent directories."""
    secure_write_file(path, content, mode=0o600)


def _crux_repo_root() -> str:
    """Resolve the Crux repo root (where scripts/, templates/ live)."""
    from scripts.lib.crux_paths import get_crux_repo
    return get_crux_repo()


CRUX_AGENTS_START = "<!-- CRUX:START -->"
CRUX_AGENTS_END = "<!-- CRUX:END -->"


def _merge_agents_md(source: str, target: str) -> None:
    """Merge Crux content into AGENTS.md without destroying existing content.

    Uses delimiters to identify the Crux-managed section. If the target file
    exists with user content, the Crux section is appended (or replaced if
    already present). If the target is a symlink (from older Crux installs),
    it's converted to a regular file with the symlink's content.
    """
    crux_content = Path(source).read_text()
    crux_section = f"{CRUX_AGENTS_START}\n{crux_content}\n{CRUX_AGENTS_END}\n"

    # If target is a symlink (legacy Crux install), resolve it first
    if os.path.islink(target):
        existing = Path(target).read_text()
        os.remove(target)
        # If the symlink pointed to our own template, just write the delimited version
        if existing.strip() == crux_content.strip():
            existing = ""
        Path(target).write_text(existing + "\n" + crux_section if existing.strip() else crux_section)
        return

    # If target doesn't exist, just write the Crux section
    if not os.path.exists(target):
        Path(target).write_text(crux_section)
        return

    # Target exists as a regular file — merge
    existing = Path(target).read_text()

    if CRUX_AGENTS_START in existing and CRUX_AGENTS_END in existing:
        # Replace existing Crux section
        start_idx = existing.index(CRUX_AGENTS_START)
        end_idx = existing.index(CRUX_AGENTS_END) + len(CRUX_AGENTS_END)
        # Consume trailing newline if present
        if end_idx < len(existing) and existing[end_idx] == "\n":
            end_idx += 1
        updated = existing[:start_idx] + crux_section + existing[end_idx:]
    else:
        # Append Crux section
        separator = "\n" if existing.strip() else ""
        updated = existing.rstrip() + separator + "\n" + crux_section

    Path(target).write_text(updated)


def sync_opencode(project_dir: str, home: str) -> SyncResult:
    """Generate ~/.config/opencode/ configs from .crux/."""
    user_paths = get_user_paths(home)
    config_dir = os.path.join(home, ".config", "opencode")
    secure_makedirs(config_dir, mode=0o700)
    items: list[str] = []

    # Symlink modes (legacy) and agents (current OpenCode convention)
    modes_source = user_paths.modes
    if os.path.isdir(modes_source):
        _safe_symlink(modes_source, os.path.join(config_dir, "modes"))
        items.append("modes")
        _safe_symlink(modes_source, os.path.join(config_dir, "agents"))
        items.append("agents")

    # Symlink user-level knowledge
    know_source = user_paths.knowledge
    if os.path.isdir(know_source):
        _safe_symlink(know_source, os.path.join(config_dir, "knowledge"))
        items.append("knowledge")

    # Merge Crux section into AGENTS.md (preserves existing user content)
    agents_md_source = os.path.join(_crux_repo_root(), "templates", "AGENTS.md")
    if os.path.isfile(agents_md_source):
        _merge_agents_md(agents_md_source, os.path.join(config_dir, "AGENTS.md"))
        items.append("AGENTS.md")

    # Write MCP config into opencode.json
    _write_opencode_mcp_config(config_dir, project_dir, home)
    items.append("mcp-config")

    return SyncResult(success=True, tool="opencode", items_synced=items)


def _write_opencode_mcp_config(config_dir: str, project_dir: str, home: str) -> None:
    """Write or merge Crux MCP server config into opencode.json."""
    from scripts.lib.crux_paths import get_crux_python

    config_file = os.path.join(config_dir, "opencode.json")

    # Load existing config or start fresh
    existing: dict = {}
    if os.path.exists(config_file):
        try:
            with open(config_file) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    # Build the Crux MCP entry in OpenCode format
    python_path = get_crux_python()
    crux_repo = _crux_repo_root()
    crux_mcp: dict = {
        "type": "local",
        "command": [python_path, "-m", "scripts.lib.crux_mcp_server"],
        "environment": {
            "CRUX_HOME": home,
            "PYTHONPATH": crux_repo,
        },
        "enabled": True,
    }

    # Merge into existing config
    if "mcp" not in existing:
        existing["mcp"] = {}
    existing["mcp"]["crux"] = crux_mcp

    with open(config_file, "w") as f:
        json.dump(existing, f, indent=2)


def sync_claude_code(project_dir: str, home: str) -> SyncResult:
    """Generate .claude/ directory from .crux/ data."""
    user_paths = get_user_paths(home)
    project_paths = get_project_paths(project_dir)
    claude_dir = os.path.join(project_dir, ".claude")
    items: list[str] = []

    # Create agents from mode definitions
    agents_dir = os.path.join(claude_dir, "agents")
    secure_makedirs(agents_dir, mode=0o700)
    modes_dir = user_paths.modes
    if os.path.isdir(modes_dir):
        # Use safe_glob_files to prevent symlink traversal
        for mode_file in safe_glob_files(Path(modes_dir), "*.md"):
            mode_name = mode_file.stem
            # Validate mode_name contains only safe characters
            if not validate_safe_filename(mode_name):
                continue  # Skip files with unsafe names
            body = strip_frontmatter(mode_file.read_text()).strip()
            meta = _MODE_META.get(mode_name, {"description": f"{mode_name} specialist", "tools": "Read, Grep, Glob"})

            # Build frontmatter — values come from _MODE_META (controlled internal data)
            # and mode_name is already validated by validate_safe_filename above
            frontmatter = f"---\nname: {mode_name}\ndescription: {meta['description']}\ntools: {meta['tools']}\n"
            if "permissionMode" in meta:
                frontmatter += f"permissionMode: {meta['permissionMode']}\n"
            frontmatter += "---\n\n"

            agent_path = os.path.join(agents_dir, f"{mode_name}.md")
            _safe_write(agent_path, frontmatter + body)
            items.append(f"agent:{mode_name}")

    # Create rules from knowledge entries
    rules_dir = os.path.join(claude_dir, "rules")
    secure_makedirs(rules_dir, mode=0o700)

    for knowledge_dir in [project_paths.knowledge, user_paths.knowledge_shared]:
        if os.path.isdir(knowledge_dir):
            # Use safe_glob_files to prevent symlink traversal
            for md_file in safe_glob_files(Path(knowledge_dir), "*.md"):
                # Validate filename contains only safe characters
                if not validate_safe_filename(md_file.stem):
                    continue  # Skip files with unsafe names
                rule_path = os.path.join(rules_dir, md_file.name)
                _safe_write(rule_path, md_file.read_text())
                items.append(f"rule:{md_file.stem}")

    # Create crux-context.md with session state and handoff
    session = load_session(str(project_paths.root))
    handoff = read_handoff(str(project_paths.root))

    context_lines = ["# Crux Session Context\n"]
    context_lines.append(f"**Active mode:** {session.active_mode}")
    if session.working_on:
        context_lines.append(f"**Working on:** {session.working_on}")
    if session.key_decisions:
        context_lines.append("\n**Key decisions:**")
        for d in session.key_decisions:
            context_lines.append(f"- {d}")
    if session.files_touched:
        context_lines.append("\n**Files touched:**")
        for f in session.files_touched:
            context_lines.append(f"- {f}")
    if session.pending:
        context_lines.append("\n**Pending:**")
        for p in session.pending:
            context_lines.append(f"- {p}")
    if handoff:
        context_lines.append(f"\n**Handoff context:**\n{handoff}")

    context_path = os.path.join(claude_dir, "crux-context.md")
    _safe_write(context_path, "\n".join(context_lines) + "\n")
    items.append("crux-context")

    return SyncResult(success=True, tool="claude-code", items_synced=items)


def _build_context_md(project_dir: str) -> str:
    """Build a markdown context document from session state."""
    project_paths = get_project_paths(project_dir)
    session = load_session(str(project_paths.root))
    handoff = read_handoff(str(project_paths.root))

    lines = ["# Crux Session Context\n"]
    lines.append(f"**Active mode:** {session.active_mode}")
    if session.working_on:
        lines.append(f"**Working on:** {session.working_on}")
    if session.key_decisions:
        lines.append("\n**Key decisions:**")
        for d in session.key_decisions:
            lines.append(f"- {d}")
    if session.files_touched:
        lines.append("\n**Files touched:**")
        for f in session.files_touched:
            lines.append(f"- {f}")
    if session.pending:
        lines.append("\n**Pending:**")
        for p in session.pending:
            lines.append(f"- {p}")
    if handoff:
        lines.append(f"\n**Handoff context:**\n{handoff}")
    return "\n".join(lines) + "\n"


def _write_mcp_config(config_path: str, project_dir: str, home: str) -> None:
    """Write or merge Crux MCP server entry into a JSON config file."""
    from scripts.lib.crux_paths import get_crux_python

    existing: dict = {}
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    python_path = get_crux_python()
    crux_repo = _crux_repo_root()
    crux_mcp: dict = {
        "command": python_path,
        "args": ["-m", "scripts.lib.crux_mcp_server"],
        "env": {
            "CRUX_PROJECT": project_dir,
            "CRUX_HOME": home,
            "PYTHONPATH": crux_repo,
        },
    }

    if "mcpServers" not in existing:
        existing["mcpServers"] = {}
    existing["mcpServers"]["crux"] = crux_mcp

    secure_makedirs(os.path.dirname(config_path), mode=0o700)
    secure_write_file(config_path, json.dumps(existing, indent=2), mode=0o600)


def sync_cursor(project_dir: str, home: str) -> SyncResult:
    """Generate .cursor/ configs from .crux/ data."""
    user_paths = get_user_paths(home)
    cursor_dir = os.path.join(project_dir, ".cursor")
    rules_dir = os.path.join(cursor_dir, "rules")
    secure_makedirs(rules_dir, mode=0o700)
    items: list[str] = []

    # Mode prompts → Cursor rules (plain markdown, no frontmatter)
    modes_dir = user_paths.modes
    if os.path.isdir(modes_dir):
        # Use safe_glob_files to prevent symlink traversal
        for mode_file in safe_glob_files(Path(modes_dir), "*.md"):
            # Validate filename contains only safe characters
            if not validate_safe_filename(mode_file.stem):
                continue  # Skip files with unsafe names
            body = strip_frontmatter(mode_file.read_text()).strip()
            rule_path = os.path.join(rules_dir, f"{mode_file.stem}.md")
            _safe_write(rule_path, body + "\n")
            items.append(f"rule:{mode_file.stem}")

    # Context rule
    context_md = _build_context_md(project_dir)
    _safe_write(os.path.join(rules_dir, "crux-context.md"), context_md)
    items.append("crux-context")

    # Register MCP server in .cursor/mcp.json
    mcp_config_path = os.path.join(cursor_dir, "mcp.json")
    _write_mcp_config(mcp_config_path, project_dir, home)
    items.append("mcp-config")

    # Merge AGENTS.md into Cursor rules
    agents_md_source = os.path.join(_crux_repo_root(), "templates", "AGENTS.md")
    if os.path.isfile(agents_md_source):
        _merge_agents_md(agents_md_source, os.path.join(rules_dir, "crux-agent.md"))
        items.append("crux-agent")

    return SyncResult(success=True, tool="cursor", items_synced=items)


def sync_windsurf(project_dir: str, home: str) -> SyncResult:
    """Generate .windsurf/ configs from .crux/ data.

    Windsurf uses:
    - .windsurf/rules/ for custom instructions (markdown files)
    - .windsurf/mcp.json for MCP server registration
    """
    user_paths = get_user_paths(home)
    windsurf_dir = os.path.join(project_dir, ".windsurf")
    rules_dir = os.path.join(windsurf_dir, "rules")
    secure_makedirs(rules_dir, mode=0o700)
    items: list[str] = []

    # Mode prompts → Windsurf rules (plain markdown)
    modes_dir = user_paths.modes
    if os.path.isdir(modes_dir):
        # Use safe_glob_files to prevent symlink traversal
        for mode_file in safe_glob_files(Path(modes_dir), "*.md"):
            # Validate filename contains only safe characters
            if not validate_safe_filename(mode_file.stem):
                continue  # Skip files with unsafe names
            body = strip_frontmatter(mode_file.read_text()).strip()
            rule_path = os.path.join(rules_dir, f"{mode_file.stem}.md")
            _safe_write(rule_path, body + "\n")
            items.append(f"rule:{mode_file.stem}")

    # Context rule
    context_md = _build_context_md(project_dir)
    _safe_write(os.path.join(rules_dir, "crux-context.md"), context_md)
    items.append("crux-context")

    # MCP config
    mcp_config_path = os.path.join(windsurf_dir, "mcp.json")
    _write_mcp_config(mcp_config_path, project_dir, home)
    items.append("mcp-config")

    # Merge AGENTS.md
    agents_md_source = os.path.join(_crux_repo_root(), "templates", "AGENTS.md")
    if os.path.isfile(agents_md_source):
        _merge_agents_md(agents_md_source, os.path.join(rules_dir, "crux-agent.md"))
        items.append("crux-agent")

    return SyncResult(success=True, tool="windsurf", items_synced=items)


def sync_tool(
    tool_name: str,
    project_dir: str,
    home: str,
) -> SyncResult:
    """Dispatch sync to the appropriate adapter and update session state."""
    if tool_name not in SUPPORTED_TOOLS:
        return SyncResult(
            success=False,
            tool=tool_name,
            error=f"Unsupported tool: '{tool_name}'. Supported: {', '.join(SUPPORTED_TOOLS)}",
        )

    project_paths = get_project_paths(project_dir)

    dispatchers = {
        "opencode": sync_opencode,
        "claude-code": sync_claude_code,
        "cursor": sync_cursor,
        "windsurf": sync_windsurf,
    }

    result = dispatchers[tool_name](project_dir=project_dir, home=home)

    # Update session to reflect the active tool
    if result.success:
        update_session(project_crux_dir=str(project_paths.root), active_tool=tool_name)

    return result
