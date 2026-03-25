"""Tool-agnostic session state management for Crux.

Stores session state in .crux/sessions/state.json so any tool
(Claude Code, OpenCode, Cursor, etc.) can pick up where another left off.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone

from scripts.lib.crux_security import secure_write_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class SessionState:
    active_mode: str = "build-py"
    active_tool: str = ""
    started_at: str = ""
    updated_at: str = ""
    working_on: str = ""
    key_decisions: list[str] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    context_summary: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = _now_iso()
        if not self.updated_at:
            self.updated_at = _now_iso()

    def to_dict(self) -> dict:
        return {
            "active_mode": self.active_mode,
            "active_tool": self.active_tool,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "working_on": self.working_on,
            "key_decisions": list(self.key_decisions),
            "files_touched": list(self.files_touched),
            "pending": list(self.pending),
            "context_summary": self.context_summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SessionState:
        return cls(
            active_mode=d.get("active_mode", "build-py"),
            active_tool=d.get("active_tool", ""),
            started_at=d.get("started_at", ""),
            updated_at=d.get("updated_at", ""),
            working_on=d.get("working_on", ""),
            key_decisions=list(d.get("key_decisions", [])),
            files_touched=list(d.get("files_touched", [])),
            pending=list(d.get("pending", [])),
            context_summary=d.get("context_summary", ""),
        )


def _state_path(project_crux_dir: str) -> str:
    return os.path.join(project_crux_dir, "sessions", "state.json")


def _handoff_path(project_crux_dir: str) -> str:
    return os.path.join(project_crux_dir, "sessions", "handoff.md")


def save_session(state: SessionState, project_crux_dir: str) -> None:
    """Persist session state to disk."""
    state.updated_at = _now_iso()
    path = _state_path(project_crux_dir)
    secure_write_file(path, json.dumps(state.to_dict(), indent=2))


def load_session(project_crux_dir: str) -> SessionState:
    """Load session state from disk, or return defaults if missing/corrupt."""
    path = _state_path(project_crux_dir)
    try:
        with open(path) as f:
            return SessionState.from_dict(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return SessionState()


def update_session(
    project_crux_dir: str,
    active_mode: str | None = None,
    active_tool: str | None = None,
    working_on: str | None = None,
    add_decision: str | None = None,
    add_file: str | None = None,
    add_pending: str | None = None,
    context_summary: str | None = None,
) -> SessionState:
    """Load, modify, and save session state in one operation."""
    state = load_session(project_crux_dir)

    if active_mode is not None:
        state.active_mode = active_mode
    if active_tool is not None:
        state.active_tool = active_tool
    if working_on is not None:
        state.working_on = working_on
    if add_decision is not None:
        state.key_decisions.append(add_decision)
    if add_file is not None and add_file not in state.files_touched:
        state.files_touched.append(add_file)
    if add_pending is not None:
        state.pending.append(add_pending)
    if context_summary is not None:
        state.context_summary = context_summary

    save_session(state, project_crux_dir)
    return state


MAX_HANDOFF_ITEMS = 50


def auto_handoff(project_crux_dir: str) -> str:
    """Generate and write handoff content from accumulated session state.

    Reads the current session state and produces a structured handoff
    document. Writes it to the handoff file automatically. Returns the
    handoff content string.
    """
    state = load_session(project_crux_dir)
    lines: list[str] = ["# Session Handoff (auto-generated)", ""]

    if state.active_mode:
        lines.append(f"**Mode:** {state.active_mode}")
    if state.active_tool:
        lines.append(f"**Tool:** {state.active_tool}")
    if state.working_on:
        lines.append(f"**Working on:** {state.working_on}")
    lines.append("")

    # Filter garbage decisions (heredoc captures, too-long entries)
    clean_decisions = [
        d for d in state.key_decisions
        if d and not d.startswith("$(") and len(d) < 300
    ]
    if clean_decisions:
        lines.append("## Key Decisions")
        for d in clean_decisions[-MAX_HANDOFF_ITEMS:]:
            lines.append(f"- {d}")
        if len(clean_decisions) > MAX_HANDOFF_ITEMS:
            lines.append(f"- ... and {len(clean_decisions) - MAX_HANDOFF_ITEMS} more")
        lines.append("")

    if state.files_touched:
        lines.append("## Files Touched")
        for f in state.files_touched[:MAX_HANDOFF_ITEMS]:
            lines.append(f"- {f}")
        if len(state.files_touched) > MAX_HANDOFF_ITEMS:
            lines.append(f"- ... and {len(state.files_touched) - MAX_HANDOFF_ITEMS} more")
        lines.append("")

    if state.pending:
        lines.append("## Pending Tasks")
        for p in state.pending:
            lines.append(f"- {p}")
        lines.append("")

    if state.context_summary:
        lines.append("## Context")
        lines.append(state.context_summary)
        lines.append("")

    content = "\n".join(lines)
    write_handoff(content, project_crux_dir)
    return content


def write_handoff(content: str, project_crux_dir: str) -> None:
    """Write handoff context for the next mode or tool."""
    path = _handoff_path(project_crux_dir)
    secure_write_file(path, content)


def read_handoff(project_crux_dir: str) -> str | None:
    """Read handoff context, or None if no handoff exists."""
    path = _handoff_path(project_crux_dir)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def archive_session(project_crux_dir: str) -> str | None:
    """Move current session state to history/ and clean up handoff."""
    state_file = _state_path(project_crux_dir)
    if not os.path.exists(state_file):
        return None

    history_dir = os.path.join(project_crux_dir, "sessions", "history")
    os.makedirs(history_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    archive_path = os.path.join(history_dir, f"{timestamp}.json")
    shutil.move(state_file, archive_path)

    # Clean up handoff
    handoff = _handoff_path(project_crux_dir)
    if os.path.exists(handoff):
        os.remove(handoff)

    return archive_path
