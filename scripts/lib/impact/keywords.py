"""Keyword extraction and grep-based file matching for impact analysis."""

from __future__ import annotations

import os
import re
import subprocess
from collections import defaultdict

STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "and", "but",
    "or", "nor", "not", "so", "yet", "both", "either", "neither", "each",
    "every", "all", "any", "few", "more", "most", "other", "some", "such",
    "no", "only", "own", "same", "than", "too", "very", "just", "because",
    "if", "when", "where", "how", "what", "which", "who", "whom", "this",
    "that", "these", "those", "it", "its", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "add", "fix", "update", "remove", "delete", "change", "modify", "make",
    "get", "set", "use", "try", "check", "create", "build", "run",
})


def _split_identifier(token: str) -> list[str]:
    """Split camelCase and snake_case identifiers into parts."""
    # Split on underscores
    parts = token.split("_")
    result = []
    for part in parts:
        # Split camelCase: insert boundary before uppercase letters
        camel = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", part)
        for sub in camel.split("_"):
            if sub:
                result.append(sub.lower())
    return result


def extract_keywords(prompt: str) -> list[str]:
    """Extract searchable keywords from a natural language prompt.

    Splits camelCase/snake_case identifiers, removes stopwords,
    deduplicates, and lowercases.
    """
    if not prompt.strip():
        return []

    tokens = re.findall(r"[A-Za-z0-9_]+", prompt)
    seen: set[str] = set()
    result: list[str] = []

    for token in tokens:
        parts = _split_identifier(token)
        for part in parts:
            low = part.lower()
            if low not in STOPWORDS and len(low) > 1 and low not in seen:
                seen.add(low)
                result.append(low)

    return result


def grep_matches(root: str, keywords: list[str]) -> dict[str, float]:
    """Find files matching keywords and score by match density.

    Returns dict mapping relative filepath to match score.
    Scores are match count / total lines (density).
    """
    if not keywords or not os.path.isdir(root):
        return {}

    counts: defaultdict[str, int] = defaultdict(int)
    lines: dict[str, int] = {}

    for kw in keywords:
        try:
            result = subprocess.run(
                ["grep", "-r", "-i", "-l",
                 "--exclude-dir=node_modules", "--exclude-dir=.git",
                 "--exclude-dir=.venv", "--exclude-dir=__pycache__",
                 "--exclude-dir=vendor", "--exclude-dir=dist",
                 "--exclude-dir=build", "--exclude-dir=_site",
                 "--include=*.py", "--include=*.js",
                 "--include=*.ts", "--include=*.tsx", "--include=*.jsx",
                 "--include=*.ex", "--include=*.exs",
                 "--include=*.md", "--include=*.json", "--include=*.yaml",
                 "--include=*.yml", "--include=*.toml", "--include=*.cfg",
                 "--include=*.txt", "--include=*.html", "--include=*.css",
                 "--include=*.sh", "--include=*.rs", "--include=*.go",
                 kw, root],
                capture_output=True, text=True, timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

        if result.returncode != 0:
            continue

        for path in result.stdout.strip().splitlines():
            path = path.strip()
            if not path:
                continue
            rel = os.path.relpath(path, root)
            counts[rel] += 1

    if not counts:
        return {}

    # Calculate density: count keyword occurrences per file
    scores: dict[str, float] = {}
    for rel, match_count in counts.items():
        full = os.path.join(root, rel)
        if rel not in lines:
            try:
                with open(full, "r", errors="ignore") as f:
                    lines[rel] = max(len(f.readlines()), 1)
            except OSError:
                lines[rel] = 1
        density = match_count / lines[rel]
        scores[rel] = round(density, 6)

    return scores
