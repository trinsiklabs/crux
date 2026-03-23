"""Git history signals for impact analysis — churn, recency, co-change."""

from __future__ import annotations

import os
import subprocess
import time
from collections import Counter, defaultdict


def _run_git(root: str, *args: str) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    if not os.path.isdir(root):
        return None
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def churn(root: str, days: int = 90) -> dict[str, int]:
    """Count how many commits touched each file in the last N days.

    Returns dict mapping filepath to commit count.
    """
    since = f"--since={days} days ago" if days > 0 else "--since=0 seconds ago"
    out = _run_git(root, "log", "--name-only", "--pretty=format:", since)
    if out is None:
        return {}
    counts: Counter[str] = Counter()
    for line in out.strip().splitlines():
        line = line.strip()
        if line:
            counts[line] += 1
    return dict(counts)


def recency(root: str) -> dict[str, float]:
    """Score each file 0-1 by how recently it was changed (1 = most recent).

    Uses git log to find the last commit timestamp per file.
    """
    out = _run_git(root, "log", "--format=%ct", "--name-only", "--no-merges")
    if out is None:
        return {}

    timestamps: dict[str, int] = {}
    current_ts: int | None = None

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            current_ts = int(line)
        elif current_ts is not None and line not in timestamps:
            timestamps[line] = current_ts

    if not timestamps:
        return {}

    now = int(time.time())
    max_age = max(now - ts for ts in timestamps.values()) or 1

    return {
        fp: 1.0 - ((now - ts) / max_age)
        for fp, ts in timestamps.items()
    }


def cochange(root: str, filepath: str, days: int = 90) -> list[str]:
    """Find files that frequently change in the same commit as filepath.

    Returns list of filepaths sorted by co-change frequency (descending).
    """
    since = f"--since={days} days ago" if days > 0 else "--since=0 seconds ago"
    out = _run_git(root, "log", "--name-only", "--pretty=format:", since,
                   "--", filepath)
    if out is None:
        return []

    # Get commits that touched this file
    commit_out = _run_git(root, "log", "--format=%H", since, "--", filepath)
    if not commit_out:
        return []

    commits = [h.strip() for h in commit_out.strip().splitlines() if h.strip()]
    if not commits:
        return []

    # For each commit, get all files changed
    cofiles: Counter[str] = Counter()
    for sha in commits:
        files_out = _run_git(root, "diff-tree", "--no-commit-id", "--name-only",
                             "-r", sha)
        if files_out:
            for f in files_out.strip().splitlines():
                f = f.strip()
                if f and f != filepath:
                    cofiles[f] += 1

    return [f for f, _ in cofiles.most_common()]
