"""Persistent codebase indexing — files, symbols, search.

Builds a catalog of all source files with their symbols (functions,
classes, constants). Persisted in .crux/index/ for fast incremental
updates. Uses Python ast module for Python files, regex for others.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

from scripts.lib.impact.ast_signals import parse_definitions

SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__", "vendor", "dist", "build", "_site", ".crux"}

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".ex": "elixir",
    ".exs": "elixir",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".sh": "bash",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".css": "css",
}

# Regex patterns for non-Python symbol extraction
_TS_DEF = re.compile(r"(?:export\s+)?(?:function|class|const|let|var|interface|type|enum)\s+(\w+)")
_EX_DEF = re.compile(r"(?:def|defp|defmodule|defstruct)\s+(\S+)")


def detect_language(filepath: str) -> str:
    """Detect language from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    return LANGUAGE_MAP.get(ext, "unknown")


def build_catalog(root: str) -> dict[str, dict]:
    """Scan all source files and build a catalog with metadata.

    Returns dict: relative_path → {language, lines, mtime, symbols}.
    """
    if not os.path.isdir(root):
        return {}

    catalog: dict[str, dict] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            lang = detect_language(fname)
            if lang == "unknown":
                continue

            try:
                stat = os.stat(full)
                with open(full, errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                continue

            symbols = extract_symbols(full, lang)

            catalog[rel] = {
                "language": lang,
                "lines": lines,
                "mtime": stat.st_mtime,
                "symbols": symbols,
            }

    return catalog


def extract_symbols(filepath: str, language: str) -> list[dict]:
    """Extract symbols from a file based on language.

    Python: uses ast module (via ast_signals.parse_definitions).
    TypeScript/JavaScript: regex extraction.
    Elixir: regex extraction.
    Others: empty.
    """
    if language == "python":
        return parse_definitions(filepath)

    if language in ("typescript", "javascript"):
        return _regex_extract(filepath, _TS_DEF)

    if language == "elixir":
        return _regex_extract(filepath, _EX_DEF)

    return []


def _regex_extract(filepath: str, pattern: re.Pattern) -> list[dict]:
    """Extract symbols using a regex pattern."""
    try:
        with open(filepath, errors="ignore") as f:
            source = f.read()
    except OSError:
        return []

    symbols: list[dict] = []
    for i, line in enumerate(source.splitlines(), 1):
        match = pattern.search(line)
        if match:
            symbols.append({"name": match.group(1), "type": "definition", "line": i})
    return symbols


def search_index(query: str, root: str) -> list[dict]:
    """Search the codebase index for files and symbols matching query.

    Returns ranked list of results: {file, symbol, line, score}.
    """
    if not query:
        return []

    catalog = build_catalog(root)
    lower_query = query.lower()
    results: list[dict] = []

    for rel, info in catalog.items():
        # Match file path
        if lower_query in rel.lower():
            results.append({"file": rel, "symbol": None, "line": None, "score": 2.0})

        # Match symbols
        for sym in info.get("symbols", []):
            name = sym.get("name", "")
            if lower_query in name.lower():
                # Exact match scores higher
                score = 3.0 if name.lower() == lower_query else 1.5
                results.append({
                    "file": rel,
                    "symbol": name,
                    "line": sym.get("line"),
                    "score": score,
                })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def index_stats(root: str) -> dict:
    """Return stats about the codebase index."""
    catalog = build_catalog(root)
    languages: defaultdict[str, int] = defaultdict(int)
    total_symbols = 0
    total_lines = 0

    for info in catalog.values():
        languages[info["language"]] += 1
        total_symbols += len(info.get("symbols", []))
        total_lines += info.get("lines", 0)

    return {
        "total_files": len(catalog),
        "total_symbols": total_symbols,
        "total_lines": total_lines,
        "languages": dict(languages),
    }


def save_index(catalog: dict, crux_dir: str) -> None:
    """Persist the index to .crux/index/catalog.json."""
    index_dir = os.path.join(crux_dir, "index")
    os.makedirs(index_dir, exist_ok=True)
    path = os.path.join(index_dir, "catalog.json")
    with open(path, "w") as f:
        json.dump(catalog, f)


def load_index(crux_dir: str) -> dict:
    """Load persisted index from .crux/index/catalog.json."""
    path = os.path.join(crux_dir, "index", "catalog.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
