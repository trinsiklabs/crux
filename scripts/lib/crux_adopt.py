"""Mid-session adoption of Crux into an existing project.

Captures as much context as possible from the current session (git history,
project structure, CLAUDE.md, LLM-provided context) and writes it into .crux/
so the next session starts with full Crux support.

Usage from a live session:
    from scripts.lib.crux_adopt import adopt_project
    adopt_project(
        project_dir=".",
        home=os.environ["HOME"],
        working_on="Building OAuth2 flow",
        key_decisions=["Use python-jose", "Redis for sessions"],
        pending=["Add refresh tokens", "Integration tests"],
        context_summary="Detailed brain dump of current state...",
        knowledge_entries={"auth-patterns": "# Auth\\nUse JWT with httponly..."},
    )
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from scripts.lib.crux_hooks import build_hook_settings
from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_paths import get_project_paths, get_user_paths
from scripts.lib.crux_security import (
    git_env_disable_hooks,
    secure_makedirs,
    secure_write_file,
    validate_and_canonicalize_dir,
    validate_safe_filename,
)
from scripts.lib.crux_session import SessionState, save_session, write_handoff


@dataclass
class AdoptResult:
    success: bool
    files_discovered: list[str] = field(default_factory=list)
    decisions_discovered: list[str] = field(default_factory=list)
    items_setup: list[str] = field(default_factory=list)
    error: str | None = None


def _parse_git_history(project_dir: str) -> tuple[list[str], list[str]]:
    """Extract files touched and commit messages from git history.

    Returns (files_touched, commit_messages).
    Uses -C flag and disables hooks to prevent arbitrary code execution.
    """
    files: list[str] = []
    messages: list[str] = []

    # Validate and canonicalize the project directory
    canonical_dir = validate_and_canonicalize_dir(project_dir)
    if canonical_dir is None:
        return files, messages

    # Get env that disables git hooks
    safe_env = git_env_disable_hooks()

    try:
        # Get files changed in recent commits (last 50)
        # Use -C flag instead of cwd to avoid running in untrusted directory
        result = subprocess.run(
            ["git", "-C", canonical_dir, "log", "--pretty=format:", "--name-only", "-50"],
            capture_output=True,
            text=True,
            timeout=10,
            env=safe_env,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and line not in files:
                    files.append(line)

        # Get commit messages
        result = subprocess.run(
            ["git", "-C", canonical_dir, "log", "--pretty=format:%s", "-50"],
            capture_output=True,
            text=True,
            timeout=10,
            env=safe_env,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    messages.append(line)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return files, messages


def _detect_project_context(project_dir: str) -> str:
    """Generate a basic PROJECT.md from directory structure."""
    # Validate and canonicalize the project directory
    canonical_dir = validate_and_canonicalize_dir(project_dir)
    if canonical_dir is None:
        return "# Project Context\n\nUnable to detect project structure.\n"

    lines = ["# Project Context\n", "## Directory Structure\n", "```"]

    for root, dirs, filenames in os.walk(canonical_dir, followlinks=False):
        # Skip hidden dirs and common non-source dirs
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".venv", "venv")
            and not os.path.islink(os.path.join(root, d))  # Skip symlinks
        ]
        rel = os.path.relpath(root, canonical_dir)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > 3:
            continue
        indent = "  " * depth
        dirname = os.path.basename(root) + "/" if rel != "." else ""
        if dirname:
            lines.append(f"{indent}{dirname}")
        for f in sorted(filenames)[:20]:  # Cap files per dir
            if not f.startswith("."):
                lines.append(f"{indent}  {f}")

    lines.append("```\n")

    # Detect tech stack from common files
    stack: list[str] = []
    p = Path(canonical_dir)
    if (p / "pyproject.toml").exists() or (p / "setup.py").exists() or (p / "requirements.txt").exists():
        stack.append("Python")
    if (p / "package.json").exists():
        stack.append("Node.js/JavaScript")
    if (p / "mix.exs").exists():
        stack.append("Elixir")
    if (p / "Cargo.toml").exists():
        stack.append("Rust")
    if (p / "go.mod").exists():
        stack.append("Go")
    if (p / "Dockerfile").exists() or (p / "docker-compose.yml").exists():
        stack.append("Docker")

    if stack:
        lines.append("## Tech Stack\n")
        for s in stack:
            lines.append(f"- {s}")
        lines.append("")

    return "\n".join(lines) + "\n"


def adopt_project(
    project_dir: str,
    home: str,
    working_on: str | None = None,
    key_decisions: list[str] | None = None,
    pending: list[str] | None = None,
    context_summary: str | None = None,
    active_mode: str = "build-py",
    active_tool: str = "claude-code",
    knowledge_entries: dict[str, str] | None = None,
) -> AdoptResult:
    """Adopt an existing project into Crux, capturing maximum context.

    Phase 1 (automatic): git history, project structure, CLAUDE.md import
    Phase 2 (LLM-provided): working_on, decisions, pending, context, knowledge
    """
    items_setup: list[str] = []

    # 1. Initialize .crux/ directories
    init_user(home=home)
    init_project(project_dir=project_dir)
    items_setup.append("Initialized .crux/ directories")

    project_paths = get_project_paths(project_dir)

    # 2. Parse git history
    git_files, git_messages = _parse_git_history(project_dir)
    items_setup.append(f"Discovered {len(git_files)} files from git history")

    # 3. Build session state
    all_decisions = list(key_decisions or [])
    # Add git commit messages as discovered decisions (deduplicate)
    for msg in git_messages:
        if msg not in all_decisions:
            all_decisions.append(msg)

    all_files = list(set(git_files))

    state = SessionState(
        active_mode=active_mode,
        active_tool=active_tool,
        working_on=working_on or "",
        key_decisions=list(key_decisions or []),  # Only user-provided as key_decisions
        files_touched=all_files,
        pending=list(pending or []),
        context_summary=context_summary or "",
    )
    save_session(state, project_crux_dir=str(project_paths.root))
    items_setup.append("Created session state")

    # 4. Write handoff if context summary provided
    if context_summary:
        write_handoff(context_summary, project_crux_dir=str(project_paths.root))
        items_setup.append("Wrote handoff context")

    # 5. Import CLAUDE.md if it exists
    claude_md = os.path.join(project_dir, "CLAUDE.md")
    if os.path.exists(claude_md):
        dest = os.path.join(str(project_paths.context), "CLAUDE.md.imported")
        shutil.copy2(claude_md, dest)
        items_setup.append("Imported CLAUDE.md")

    # 6. Generate PROJECT.md
    project_md_path = project_paths.project_md
    project_context = _detect_project_context(project_dir)
    secure_makedirs(os.path.dirname(project_md_path), mode=0o700)
    secure_write_file(project_md_path, project_context, mode=0o600)
    items_setup.append("Generated PROJECT.md")

    # 7. Write knowledge entries (don't overwrite existing)
    if knowledge_entries:
        k_dir = project_paths.knowledge
        secure_makedirs(k_dir, mode=0o700)
        written = 0
        for name, content in knowledge_entries.items():
            # Validate knowledge entry name contains only safe characters
            if not validate_safe_filename(name):
                continue  # Skip entries with unsafe names
            k_file = os.path.join(k_dir, f"{name}.md")
            if not os.path.exists(k_file):
                secure_write_file(k_file, content, mode=0o600)
                written += 1
        if written:
            items_setup.append(f"Created {written} knowledge entries")

    # 8. Set up Claude Code integration (MCP server + hooks)
    claude_dir = os.path.join(project_dir, ".claude")
    secure_makedirs(claude_dir, mode=0o700)

    # 8a. MCP server config
    from scripts.lib.crux_paths import get_crux_python, get_crux_repo
    python_path = get_crux_python()
    crux_repo = get_crux_repo()
    mcp_json_path = os.path.join(claude_dir, "mcp.json")
    mcp_config = {
        "mcpServers": {
            "crux": {
                "command": python_path,
                "args": ["-m", "scripts.lib.crux_mcp_server"],
                "env": {
                    "CRUX_PROJECT": project_dir,
                    "CRUX_HOME": home,
                    "PYTHONPATH": crux_repo,
                },
            }
        }
    }
    secure_write_file(mcp_json_path, json.dumps(mcp_config, indent=2), mode=0o600)
    items_setup.append("Created .claude/mcp.json")

    # 8b. Hooks config in settings.local.json
    settings_path = os.path.join(claude_dir, "settings.local.json")
    existing_settings: dict = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path) as f:
                existing_settings = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing_settings = {}

    hook_settings = build_hook_settings(project_dir=project_dir, home=home)
    existing_settings["hooks"] = hook_settings["hooks"]

    secure_write_file(settings_path, json.dumps(existing_settings, indent=2), mode=0o600)
    items_setup.append("Created .claude/settings.local.json (hooks)")

    return AdoptResult(
        success=True,
        files_discovered=git_files,
        decisions_discovered=git_messages,
        items_setup=items_setup,
    )
