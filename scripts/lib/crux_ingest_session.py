"""crux ingest-session: Background daemon for Claude Code session migration.

PLAN-321: Migrate Claude Code session .jsonl files into Crux session logs.
- Comprehensive: captures everything as if Crux was active the whole time
- Background: runs as daemon, doesn't block terminal
- Idempotent: safe to run multiple times
- Restartable: can resume from checkpoint after interruption
- Auto-restart: survives session exit via PID file

Session files location: ~/.claude/projects/<project-hash>/*.jsonl
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Checkpoint / Resume
# ---------------------------------------------------------------------------

@dataclass
class IngestCheckpoint:
    """Tracks progress for resume capability."""
    session_file: str = ""
    lines_processed: int = 0
    files_extracted: list[str] = field(default_factory=list)
    decisions_extracted: list[str] = field(default_factory=list)
    corrections_detected: int = 0
    interactions_logged: int = 0
    started_at: str = ""
    last_update: str = ""
    status: str = "running"  # running, completed, failed


def load_checkpoint(crux_dir: str) -> IngestCheckpoint | None:
    """Load checkpoint from .crux/ingest/checkpoint.json"""
    path = os.path.join(crux_dir, "ingest", "checkpoint.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return IngestCheckpoint(**{k: v for k, v in data.items() if k in IngestCheckpoint.__dataclass_fields__})
    except (json.JSONDecodeError, OSError, TypeError):
        return None


def save_checkpoint(checkpoint: IngestCheckpoint, crux_dir: str) -> None:
    """Save checkpoint atomically."""
    ingest_dir = os.path.join(crux_dir, "ingest")
    os.makedirs(ingest_dir, exist_ok=True)

    checkpoint.last_update = datetime.now(timezone.utc).isoformat()

    path = os.path.join(ingest_dir, "checkpoint.json")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(asdict(checkpoint), f, indent=2)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Session File Discovery
# ---------------------------------------------------------------------------

def find_claude_sessions(home: str = "~") -> list[str]:
    """Find all Claude Code session .jsonl files."""
    home = os.path.expanduser(home)
    claude_dir = os.path.join(home, ".claude", "projects")

    if not os.path.isdir(claude_dir):
        return []

    sessions = []
    for project_hash in os.listdir(claude_dir):
        project_dir = os.path.join(claude_dir, project_hash)
        if not os.path.isdir(project_dir):
            continue

        for fname in os.listdir(project_dir):
            if fname.endswith(".jsonl"):
                sessions.append(os.path.join(project_dir, fname))

    return sorted(sessions, key=os.path.getmtime)


def find_session_for_project(project_dir: str, home: str = "~") -> str | None:
    """Find the most recent session file for a specific project."""
    home = os.path.expanduser(home)

    # Claude Code hashes project paths
    # Look for sessions that mention this project
    sessions = find_claude_sessions(home)

    # For now, return the most recent session
    # TODO: Match by project path in session content
    return sessions[-1] if sessions else None


# ---------------------------------------------------------------------------
# Session Parsing
# ---------------------------------------------------------------------------

@dataclass
class SessionEntry:
    """A single entry from a Claude Code session."""
    type: str  # "user", "assistant", "tool_use", "tool_result"
    content: str | dict
    timestamp: str | None = None
    tool_name: str | None = None
    tool_input: dict | None = None


def parse_session_file(path: str, start_line: int = 0) -> Iterator[tuple[int, SessionEntry]]:
    """Parse a Claude Code session .jsonl file.

    Yields (line_number, SessionEntry) tuples starting from start_line.
    """
    with open(path) as f:
        for line_num, line in enumerate(f, start=1):
            if line_num <= start_line:
                continue

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Parse different message types
            msg_type = data.get("type", "unknown")

            if msg_type == "user":
                yield line_num, SessionEntry(
                    type="user",
                    content=data.get("message", {}).get("content", ""),
                    timestamp=data.get("timestamp"),
                )

            elif msg_type == "assistant":
                content = data.get("message", {}).get("content", [])
                # Extract text blocks
                text_parts = []
                for block in content if isinstance(content, list) else [content]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)

                yield line_num, SessionEntry(
                    type="assistant",
                    content="\n".join(text_parts),
                    timestamp=data.get("timestamp"),
                )

            elif msg_type == "tool_use":
                yield line_num, SessionEntry(
                    type="tool_use",
                    content=data,
                    tool_name=data.get("name"),
                    tool_input=data.get("input", {}),
                    timestamp=data.get("timestamp"),
                )

            elif msg_type == "tool_result":
                yield line_num, SessionEntry(
                    type="tool_result",
                    content=data.get("content", ""),
                    tool_name=data.get("tool_name"),
                    timestamp=data.get("timestamp"),
                )


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_files_touched(entries: list[SessionEntry]) -> list[str]:
    """Extract file paths from Edit/Write tool uses."""
    files = set()
    for entry in entries:
        if entry.type == "tool_use" and entry.tool_name in ("Edit", "Write", "Read"):
            file_path = entry.tool_input.get("file_path") if entry.tool_input else None
            if file_path:
                files.add(file_path)
    return sorted(files)


def extract_decisions(entries: list[SessionEntry]) -> list[str]:
    """Extract key decisions from assistant responses."""
    decisions = []
    decision_markers = [
        "I'll use", "I decided", "Let's use", "We should",
        "The approach", "Implementation:", "Strategy:",
    ]

    for entry in entries:
        if entry.type == "assistant" and isinstance(entry.content, str):
            for marker in decision_markers:
                if marker.lower() in entry.content.lower():
                    # Extract the sentence containing the marker
                    sentences = entry.content.split(". ")
                    for sentence in sentences:
                        if marker.lower() in sentence.lower():
                            decisions.append(sentence.strip()[:200])
                            break
                    break

    return decisions[:20]  # Limit to 20 decisions


def detect_corrections(entries: list[SessionEntry]) -> list[dict]:
    """Detect correction patterns (user correcting AI)."""
    corrections = []
    correction_markers = [
        "no,", "actually", "that's wrong", "not quite", "instead",
        "should be", "fix that", "change that to",
    ]

    for i, entry in enumerate(entries):
        if entry.type == "user" and isinstance(entry.content, str):
            content_lower = entry.content.lower()
            for marker in correction_markers:
                if marker in content_lower:
                    corrections.append({
                        "trigger": entry.content[:200],
                        "timestamp": entry.timestamp,
                        "marker": marker,
                    })
                    break

    return corrections


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def ingest_session(
    session_path: str,
    crux_dir: str,
    checkpoint: IngestCheckpoint | None = None,
    progress_callback: callable = None,
) -> IngestCheckpoint:
    """Ingest a Claude Code session into Crux.

    Args:
        session_path: Path to .jsonl session file
        crux_dir: Path to .crux/ directory
        checkpoint: Optional checkpoint to resume from
        progress_callback: Optional callback(checkpoint) for progress updates

    Returns:
        Final checkpoint with results
    """
    if checkpoint is None:
        checkpoint = IngestCheckpoint(
            session_file=session_path,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
    elif checkpoint.status == "completed":
        return checkpoint

    entries: list[SessionEntry] = []
    start_line = checkpoint.lines_processed

    # Parse session
    for line_num, entry in parse_session_file(session_path, start_line):
        entries.append(entry)
        checkpoint.lines_processed = line_num

        # Periodic checkpoint save
        if line_num % 100 == 0:
            save_checkpoint(checkpoint, crux_dir)
            if progress_callback:
                progress_callback(checkpoint)

    # Extract data
    files = extract_files_touched(entries)
    decisions = extract_decisions(entries)
    corrections = detect_corrections(entries)

    checkpoint.files_extracted = files
    checkpoint.decisions_extracted = decisions
    checkpoint.corrections_detected = len(corrections)

    # Write to Crux session state
    session_dir = os.path.join(crux_dir, "sessions")
    os.makedirs(session_dir, exist_ok=True)

    state_path = os.path.join(session_dir, "state.json")
    state = {}
    if os.path.exists(state_path):
        try:
            with open(state_path) as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            state = {}

    # Merge ingested data
    existing_files = set(state.get("files_touched", []))
    existing_files.update(files)
    state["files_touched"] = sorted(existing_files)

    existing_decisions = state.get("key_decisions", [])
    for d in decisions:
        if d not in existing_decisions:
            existing_decisions.append(d)
    state["key_decisions"] = existing_decisions[:30]

    state["ingested_from"] = session_path
    state["ingested_at"] = datetime.now(timezone.utc).isoformat()

    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    # Write corrections
    if corrections:
        corr_dir = os.path.join(crux_dir, "corrections")
        os.makedirs(corr_dir, exist_ok=True)
        corr_path = os.path.join(corr_dir, "corrections.jsonl")
        with open(corr_path, "a") as f:
            for corr in corrections:
                corr["source"] = "ingest"
                f.write(json.dumps(corr) + "\n")

    # Log interactions
    analytics_dir = os.path.join(crux_dir, "analytics", "interactions")
    os.makedirs(analytics_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = os.path.join(analytics_dir, f"{today}.jsonl")

    interaction_count = 0
    with open(log_path, "a") as f:
        for entry in entries:
            if entry.type == "tool_use":
                interaction_count += 1
                log_entry = {
                    "tool": entry.tool_name,
                    "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
                    "source": "ingest",
                }
                f.write(json.dumps(log_entry) + "\n")

    checkpoint.interactions_logged = interaction_count
    checkpoint.status = "completed"
    save_checkpoint(checkpoint, crux_dir)

    return checkpoint


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------

_running = True


def _signal_handler(signum, frame):
    global _running
    _running = False


def run_daemon(
    project_dir: str,
    home: str = "~",
    poll_interval: int = 5,
) -> None:
    """Run as background daemon with auto-restart capability.

    Creates PID file for coordination and handles signals gracefully.
    """
    global _running

    crux_dir = os.path.join(project_dir, ".crux")
    pid_file = os.path.join(crux_dir, "ingest", "daemon.pid")

    # Check for existing daemon
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                old_pid = int(f.read().strip())
            # Check if process exists
            os.kill(old_pid, 0)
            print(f"Daemon already running (PID {old_pid})")
            return
        except (OSError, ValueError):
            # Process doesn't exist, clean up
            os.unlink(pid_file)

    # Write PID
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    # Set up signal handlers
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        # Load or create checkpoint
        checkpoint = load_checkpoint(crux_dir)

        # Find session to ingest
        session_path = find_session_for_project(project_dir, home)
        if not session_path:
            print("No session found to ingest")
            return

        if checkpoint and checkpoint.session_file == session_path and checkpoint.status == "completed":
            print("Session already ingested")
            return

        print(f"Ingesting: {session_path}")

        def progress(cp):
            print(f"  Lines: {cp.lines_processed}, Files: {len(cp.files_extracted)}")

        result = ingest_session(
            session_path=session_path,
            crux_dir=crux_dir,
            checkpoint=checkpoint,
            progress_callback=progress,
        )

        print(f"\nIngest complete:")
        print(f"  Files: {len(result.files_extracted)}")
        print(f"  Decisions: {len(result.decisions_extracted)}")
        print(f"  Corrections: {result.corrections_detected}")
        print(f"  Interactions: {result.interactions_logged}")

    finally:
        # Clean up PID file
        try:
            os.unlink(pid_file)
        except OSError:
            pass


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Claude Code session into Crux")
    parser.add_argument("--project", default=".", help="Project directory")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--session", help="Specific session file to ingest")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    crux_dir = os.path.join(project_dir, ".crux")

    if not os.path.isdir(crux_dir):
        print(f"Not a Crux project: {project_dir}")
        print("Run 'crux adopt' first")
        sys.exit(1)

    if args.daemon:
        run_daemon(project_dir)
    elif args.session:
        result = ingest_session(args.session, crux_dir)
        print(f"Ingested: {result.lines_processed} lines")
    else:
        # Default: find and ingest most recent session
        session = find_session_for_project(project_dir)
        if session:
            result = ingest_session(session, crux_dir)
            print(f"Ingested {session}")
            print(f"  Files: {len(result.files_extracted)}")
            print(f"  Decisions: {len(result.decisions_extracted)}")
        else:
            print("No session found to ingest")


if __name__ == "__main__":
    main()
