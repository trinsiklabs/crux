"""Git-aware editing context — version history for better AI edits.

Provides git context (diffs, history, blame, risk) to any connected
tool via MCP, so the AI makes better edits informed by version history.
"""

from __future__ import annotations

import os
import subprocess


def _git(root: str, *args: str) -> str:
    """Run a git command and return stdout, or '' on failure."""
    if not os.path.isdir(root):
        return ""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_current_diff(root: str) -> str:
    """Get current uncommitted changes (staged + unstaged)."""
    staged = _git(root, "diff", "--cached")
    unstaged = _git(root, "diff")
    return (staged + unstaged).strip()


def get_file_history(root: str, filepath: str, n: int = 10) -> list[dict]:
    """Get last N commits that touched a file.

    Returns list of {hash, message, author, date}.
    """
    out = _git(root, "log", f"-{n}", "--format=%H|%s|%an|%ci", "--", filepath)
    if not out.strip():
        return []

    history: list[dict] = []
    for line in out.strip().splitlines():
        parts = line.split("|", 3)
        if len(parts) >= 4:
            history.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3],
            })
    return history


def get_branch_context(root: str) -> dict:
    """Get current branch, recent branches, ahead/behind."""
    branch = _git(root, "branch", "--show-current").strip()
    if not branch:
        return {}

    return {
        "branch": branch,
        "commit_count": len(_git(root, "log", "--oneline", "-20").strip().splitlines()),
    }


def suggest_commit_message(root: str) -> str:
    """Generate a commit message suggestion from staged changes."""
    diff = _git(root, "diff", "--cached", "--stat")
    if not diff.strip():
        return ""

    # Parse changed files from stat output
    files: list[str] = []
    for line in diff.strip().splitlines():
        if "|" in line:
            fname = line.split("|")[0].strip()
            files.append(fname)

    if not files:
        return ""

    # Simple heuristic: describe what changed
    if len(files) == 1:
        return f"Update {files[0]}"
    return f"Update {len(files)} files: {', '.join(files[:3])}"


def get_risky_files(root: str, top_n: int = 10) -> list[dict]:
    """Find files with high churn (most likely to cause issues if edited).

    Returns list of {file, commits, risk_score}.
    """
    out = _git(root, "log", "--name-only", "--pretty=format:", "--since=90 days ago")
    if not out.strip():
        return []

    from collections import Counter
    counts: Counter[str] = Counter()
    for line in out.strip().splitlines():
        line = line.strip()
        if line:
            counts[line] += 1

    risky: list[dict] = []
    for filepath, commit_count in counts.most_common(top_n):
        risky.append({
            "file": filepath,
            "commits": commit_count,
            "risk_score": round(commit_count / max(counts.values()), 2),
        })
    return risky
