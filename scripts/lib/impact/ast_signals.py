"""AST-based file analysis for impact scoring — Python files only.

Uses Python's ast module to extract imports, definitions, and build
import graphs. Gracefully degrades for non-Python or unparseable files.
"""

from __future__ import annotations

import ast
import os
from collections import Counter, defaultdict

SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__", "vendor", "dist", "build", "_site"}


def parse_imports(filepath: str) -> list[str]:
    """Extract import targets from a Python file.

    Returns module names (e.g., ['hashlib', 'db', 'utils']).
    Returns [] for non-Python, nonexistent, or unparseable files.
    """
    if not os.path.isfile(filepath) or not filepath.endswith(".py"):
        return []
    try:
        with open(filepath, errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, ValueError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
            elif node.level > 0 and node.names:
                # relative import like "from . import foo"
                for alias in node.names:
                    imports.append(alias.name)
    return imports


def parse_definitions(filepath: str) -> list[dict]:
    """Extract function, class, and constant definitions from a Python file.

    Returns list of dicts: {name, type, line}.
    """
    if not os.path.isfile(filepath) or not filepath.endswith(".py"):
        return []
    try:
        with open(filepath, errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, ValueError):
        return []

    # Collect class method names to avoid double-counting
    class_methods: set[int] = set()  # line numbers of methods inside classes

    defs: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            defs.append({"name": node.name, "type": "class", "line": node.lineno})
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defs.append({"name": item.name, "type": "function", "line": item.lineno})
                    class_methods.add(item.lineno)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno not in class_methods:
                defs.append({"name": node.name, "type": "function", "line": node.lineno})
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    defs.append({"name": target.id, "type": "constant", "line": node.lineno})
    return defs


def build_import_graph(root: str) -> dict[str, list[str]]:
    """Build a map of file → imported modules for all Python files in root.

    Skips vendored directories. Returns relative paths as keys.
    """
    if not os.path.isdir(root):
        return {}

    graph: dict[str, list[str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            imports = parse_imports(full)
            if imports:
                graph[rel] = imports
    return graph


def symbol_relevance(root: str, keywords: list[str]) -> dict[str, float]:
    """Score files by how many of their definitions match keywords.

    Also applies a hub boost for files imported by many others.
    Returns dict mapping relative filepath to relevance score.
    """
    if not keywords or not os.path.isdir(root):
        return {}

    lower_keywords = {k.lower() for k in keywords}
    scores: defaultdict[str, float] = defaultdict(float)

    # Build import graph for hub scoring
    graph = build_import_graph(root)

    # Count how many files import each module
    import_counts: Counter[str] = Counter()
    for imports in graph.values():
        for imp in imports:
            import_counts[imp] += 1

    # Score each Python file by definition matches
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)

            defs = parse_definitions(full)
            for d in defs:
                name_lower = d["name"].lower()
                for kw in lower_keywords:
                    if kw in name_lower:
                        scores[rel] += 2.0  # exact substring match
                    elif name_lower in kw:
                        scores[rel] += 1.0  # reverse match

            # Hub boost: files imported by many others are structurally important
            module_name = fname.replace(".py", "")
            hub_count = import_counts.get(module_name, 0)
            if hub_count > 0 and rel in scores:
                scores[rel] += hub_count * 0.5

    # Normalize to 0-1
    if not scores:
        return {}
    mx = max(scores.values()) or 1
    return {k: round(v / mx, 6) for k, v in scores.items()}
