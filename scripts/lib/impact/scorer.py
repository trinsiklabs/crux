"""Scoring engine — combine signals into ranked file list."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from scripts.lib.impact.git_signals import churn, recency
from scripts.lib.impact.keywords import extract_keywords, grep_matches
from scripts.lib.impact.lsp_signals import symbol_matches
from scripts.lib.impact.ast_signals import symbol_relevance as ast_relevance

DEFAULT_WEIGHTS: dict[str, float] = {
    "keyword": 0.25,
    "churn": 0.15,
    "ast": 0.25,
    "symbol": 0.15,
    "proximity": 0.20,
}


@dataclass
class RankedFile:
    """A file with its relevance score and contributing reasons."""
    path: str
    score: float
    reasons: dict[str, float] = field(default_factory=dict)


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    """Normalize scores to 0-1 range."""
    if not scores:
        return {}
    mx = max(scores.values())
    if mx == 0:
        return {k: 0.0 for k in scores}
    return {k: v / mx for k, v in scores.items()}


def _proximity_scores(
    keyword_scores: dict[str, float],
    root: str,
) -> dict[str, float]:
    """Boost files in the same directory as high-scoring keyword matches."""
    if not keyword_scores:
        return {}

    # Find directories containing top-scoring files
    top_dirs: set[str] = set()
    threshold = max(keyword_scores.values()) * 0.5 if keyword_scores else 0
    for fp, score in keyword_scores.items():
        if score >= threshold:
            top_dirs.add(os.path.dirname(fp))

    # Walk root and score files near top directories
    skip = {"node_modules", ".git", ".venv", "__pycache__", "vendor", "dist", "build", "_site"}
    proximity: dict[str, float] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        for fname in filenames:
            rel = os.path.join(rel_dir, fname) if rel_dir else fname
            if rel in keyword_scores:
                continue  # Already scored by keywords
            for td in top_dirs:
                if rel_dir == td:
                    proximity[rel] = 1.0
                    break
                elif rel_dir.startswith(td + os.sep) or td.startswith(rel_dir + os.sep):
                    proximity[rel] = max(proximity.get(rel, 0), 0.5)

    return proximity


def rank_files(
    root: str,
    prompt: str,
    top_n: int = 20,
    include_reasons: bool = True,
    weights: dict[str, float] | None = None,
) -> list[RankedFile]:
    """Rank files by relevance to a prompt using all available signals.

    Args:
        root: Repository root path.
        prompt: Natural language description of the task.
        top_n: Maximum number of files to return.
        include_reasons: Whether to include per-dimension scores.
        weights: Custom dimension weights (defaults to DEFAULT_WEIGHTS).

    Returns:
        List of RankedFile sorted by score descending.
    """
    if not os.path.isdir(root):
        return []

    keywords = extract_keywords(prompt)
    if not keywords:
        return []

    w = weights or DEFAULT_WEIGHTS

    # Gather raw signals
    kw_raw = grep_matches(root, keywords)
    churn_raw = churn(root)
    sym_raw = symbol_matches(root, keywords)
    ast_raw = ast_relevance(root, keywords)

    # Normalize each dimension to 0-1
    kw_norm = _normalize(kw_raw)
    churn_norm = _normalize({k: float(v) for k, v in churn_raw.items()})
    sym_norm = _normalize(sym_raw)
    ast_norm = _normalize(ast_raw)
    prox_raw = _proximity_scores(kw_norm, root)
    prox_norm = _normalize(prox_raw)

    # Collect all files seen across any dimension
    all_files: set[str] = set()
    all_files.update(kw_norm)
    all_files.update(churn_norm)
    all_files.update(sym_norm)
    all_files.update(ast_norm)
    all_files.update(prox_norm)

    if not all_files:
        return []

    # Score each file
    results: list[RankedFile] = []
    for fp in all_files:
        kw_s = kw_norm.get(fp, 0.0)
        ch_s = churn_norm.get(fp, 0.0)
        sy_s = sym_norm.get(fp, 0.0)
        as_s = ast_norm.get(fp, 0.0)
        pr_s = prox_norm.get(fp, 0.0)

        score = (
            w.get("keyword", 0) * kw_s
            + w.get("churn", 0) * ch_s
            + w.get("symbol", 0) * sy_s
            + w.get("ast", 0) * as_s
            + w.get("proximity", 0) * pr_s
        )

        reasons = {}
        if include_reasons:
            reasons = {
                "keyword": round(kw_s, 4),
                "churn": round(ch_s, 4),
                "ast": round(as_s, 4),
                "symbol": round(sy_s, 4),
                "proximity": round(pr_s, 4),
            }

        results.append(RankedFile(path=fp, score=round(score, 6), reasons=reasons))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
