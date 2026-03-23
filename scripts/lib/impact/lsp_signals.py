"""LSP symbol signals for impact analysis — gracefully degrades without LSP."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from urllib.parse import urlparse, unquote


def check_lsp(root: str) -> bool:
    """Check if an LSP server is available for the given root.

    Currently returns False — LSP integration is deferred.
    Callers should always handle the no-LSP case.
    """
    return False


def _query_symbols(root: str, keyword: str) -> list[dict]:
    """Query LSP for workspace symbols matching a keyword.

    Returns list of symbol dicts with 'name' and 'location.uri' fields.
    Stub — returns empty until LSP integration is wired.
    """
    return []


def _query_references(root: str, filepath: str) -> list[dict]:
    """Query LSP for references to symbols defined in a file.

    Returns list of reference dicts with 'uri' and 'range' fields.
    Stub — returns empty until LSP integration is wired.
    """
    return []


def _uri_to_relpath(uri: str, root: str) -> str | None:
    """Convert a file:// URI to a path relative to root."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    abspath = unquote(parsed.path)
    if not abspath.startswith(root):
        return None
    rel = os.path.relpath(abspath, root)
    return rel


def symbol_matches(root: str, keywords: list[str]) -> dict[str, float]:
    """Find files containing symbols matching keywords via LSP.

    Returns dict mapping relative filepath to match score.
    Returns empty dict if LSP is not available (graceful degradation).
    """
    if not keywords:
        return {}

    if not check_lsp(root):
        return {}

    counts: defaultdict[str, int] = defaultdict(int)

    for kw in keywords:
        symbols = _query_symbols(root, kw)
        for sym in symbols:
            name = sym.get("name", "")
            uri = sym.get("location", {}).get("uri", "")
            if not uri:
                continue
            rel = _uri_to_relpath(uri, root)
            if rel is None:
                continue
            # Score higher for exact keyword match in symbol name
            if kw.lower() in name.lower():
                counts[rel] += 2
            else:
                counts[rel] += 1

    if not counts:
        return {}

    max_count = max(counts.values())
    return {fp: round(c / max_count, 6) for fp, c in counts.items()}


def reference_graph(root: str, filepath: str) -> list[str]:
    """Find files that reference symbols defined in filepath via LSP.

    Returns list of relative filepaths (deduplicated, excludes self).
    Returns empty list if LSP is not available (graceful degradation).
    """
    if not check_lsp(root):
        return []

    refs = _query_references(root, filepath)
    seen: set[str] = set()
    result: list[str] = []

    for ref in refs:
        uri = ref.get("uri", "")
        rel = _uri_to_relpath(uri, root)
        if rel is None or rel == filepath or rel in seen:
            continue
        seen.add(rel)
        result.append(rel)

    return result
