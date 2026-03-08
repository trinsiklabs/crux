"""Site content auto-revision: detect feature changes and map to affected pages.

Detects changes to:
- MCP tools (new tools in crux_mcp_server.py)
- Modes (new .md files in ~/.crux/modes/)
- Test coverage (pytest coverage reports)

Maps changes to affected website pages in site/src/.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from scripts.lib.crux_paths import get_user_paths


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolChange:
    """Represents a change to an MCP tool."""
    name: str
    change_type: str  # "added", "modified", "removed"
    docstring: Optional[str] = None


@dataclass
class ModeChange:
    """Represents a change to a mode."""
    name: str
    change_type: str  # "added", "modified", "removed"
    description: Optional[str] = None


@dataclass
class CoverageChange:
    """Represents a change to test coverage."""
    module: str
    old_coverage: Optional[float] = None
    new_coverage: Optional[float] = None

    @property
    def delta(self) -> Optional[float]:
        if self.old_coverage is not None and self.new_coverage is not None:
            return self.new_coverage - self.old_coverage
        return None


@dataclass
class PageUpdate:
    """Represents a page that needs to be updated."""
    path: str
    reason: str
    changes: list[str] = field(default_factory=list)
    priority: str = "normal"  # "high", "normal", "low"


@dataclass
class SiteRevisionResult:
    """Result of site revision detection."""
    tool_changes: list[ToolChange] = field(default_factory=list)
    mode_changes: list[ModeChange] = field(default_factory=list)
    coverage_changes: list[CoverageChange] = field(default_factory=list)
    pages_to_update: list[PageUpdate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tool_changes": [
                {"name": t.name, "change_type": t.change_type, "docstring": t.docstring}
                for t in self.tool_changes
            ],
            "mode_changes": [
                {"name": m.name, "change_type": m.change_type, "description": m.description}
                for m in self.mode_changes
            ],
            "coverage_changes": [
                {
                    "module": c.module,
                    "old_coverage": c.old_coverage,
                    "new_coverage": c.new_coverage,
                    "delta": c.delta,
                }
                for c in self.coverage_changes
            ],
            "pages_to_update": [
                {
                    "path": p.path,
                    "reason": p.reason,
                    "changes": p.changes,
                    "priority": p.priority,
                }
                for p in self.pages_to_update
            ],
            "summary": {
                "tools_changed": len(self.tool_changes),
                "modes_changed": len(self.mode_changes),
                "coverage_changed": len(self.coverage_changes),
                "pages_affected": len(self.pages_to_update),
            },
        }


# ---------------------------------------------------------------------------
# Tool detection
# ---------------------------------------------------------------------------

# Regex to find @mcp.tool() decorated functions
TOOL_PATTERN = re.compile(
    r'@mcp\.tool\(\)\s*\n'
    r'def\s+(\w+)\s*\([^)]*\)\s*->\s*\w+:\s*\n'
    r'\s*"""([^"]*(?:""[^"]*)*?)"""',
    re.MULTILINE
)


def parse_mcp_tools(content: str) -> dict[str, str]:
    """Parse MCP tool definitions from server source code.

    Returns dict mapping tool name to docstring.
    """
    tools = {}
    for match in TOOL_PATTERN.finditer(content):
        name = match.group(1)
        docstring = match.group(2).strip()
        # Extract first line of docstring as description
        first_line = docstring.split("\n")[0].strip()
        tools[name] = first_line
    return tools


def detect_tool_changes(
    current_content: str,
    baseline_content: Optional[str] = None,
) -> list[ToolChange]:
    """Detect changes to MCP tools between baseline and current.

    If no baseline provided, all current tools are marked as existing.
    """
    current_tools = parse_mcp_tools(current_content)
    baseline_tools = parse_mcp_tools(baseline_content) if baseline_content else {}

    changes = []

    # Find added tools
    for name, docstring in current_tools.items():
        if name not in baseline_tools:
            changes.append(ToolChange(name=name, change_type="added", docstring=docstring))
        elif baseline_tools[name] != docstring:
            changes.append(ToolChange(name=name, change_type="modified", docstring=docstring))

    # Find removed tools
    for name in baseline_tools:
        if name not in current_tools:
            changes.append(ToolChange(name=name, change_type="removed"))

    return changes


def get_current_tools(home: Optional[str] = None) -> dict[str, str]:
    """Get the current set of MCP tools from the server."""
    paths = get_user_paths(home)
    server_path = os.path.join(paths.scripts_lib, "crux_mcp_server.py")

    if not os.path.exists(server_path):
        return {}

    with open(server_path, "r") as f:
        content = f.read()

    return parse_mcp_tools(content)


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

MODE_DESCRIPTION_PATTERN = re.compile(r'^description:\s*(.+)$', re.MULTILINE)


def parse_mode_description(content: str) -> Optional[str]:
    """Extract description from mode frontmatter."""
    match = MODE_DESCRIPTION_PATTERN.search(content)
    if match:
        return match.group(1).strip()
    return None


def get_modes_from_dir(modes_dir: str) -> dict[str, Optional[str]]:
    """Get all modes and their descriptions from a directory."""
    modes = {}

    if not os.path.isdir(modes_dir):
        return modes

    for filename in os.listdir(modes_dir):
        if filename.endswith(".md") and not filename.startswith("_"):
            name = os.path.splitext(filename)[0]
            filepath = os.path.join(modes_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()
            modes[name] = parse_mode_description(content)

    return modes


def detect_mode_changes(
    current_modes: dict[str, Optional[str]],
    baseline_modes: Optional[dict[str, Optional[str]]] = None,
) -> list[ModeChange]:
    """Detect changes to modes between baseline and current."""
    if baseline_modes is None:
        baseline_modes = {}

    changes = []

    # Find added/modified modes
    for name, desc in current_modes.items():
        if name not in baseline_modes:
            changes.append(ModeChange(name=name, change_type="added", description=desc))
        elif baseline_modes[name] != desc:
            changes.append(ModeChange(name=name, change_type="modified", description=desc))

    # Find removed modes
    for name in baseline_modes:
        if name not in current_modes:
            changes.append(ModeChange(name=name, change_type="removed"))

    return changes


def get_current_modes(home: Optional[str] = None) -> dict[str, Optional[str]]:
    """Get the current set of modes."""
    paths = get_user_paths(home)
    return get_modes_from_dir(paths.modes)


# ---------------------------------------------------------------------------
# Test coverage detection
# ---------------------------------------------------------------------------

COVERAGE_LINE_PATTERN = re.compile(
    r'^([^\s]+)\s+\d+\s+\d+\s+(\d+)%',
    re.MULTILINE
)


def parse_coverage_report(content: str) -> dict[str, float]:
    """Parse pytest coverage report and extract module coverage percentages."""
    coverage = {}

    for match in COVERAGE_LINE_PATTERN.finditer(content):
        module = match.group(1)
        percent = float(match.group(2))
        coverage[module] = percent

    return coverage


def detect_coverage_changes(
    current_coverage: dict[str, float],
    baseline_coverage: Optional[dict[str, float]] = None,
    threshold: float = 5.0,
) -> list[CoverageChange]:
    """Detect significant coverage changes.

    Args:
        current_coverage: Current coverage percentages by module
        baseline_coverage: Previous coverage percentages
        threshold: Minimum percentage change to report (default 5%)
    """
    if baseline_coverage is None:
        return []

    changes = []

    # Check for coverage changes
    all_modules = set(current_coverage.keys()) | set(baseline_coverage.keys())

    for module in all_modules:
        old = baseline_coverage.get(module)
        new = current_coverage.get(module)

        if old is None and new is not None:
            # New module with coverage
            changes.append(CoverageChange(module=module, new_coverage=new))
        elif old is not None and new is None:
            # Module removed
            changes.append(CoverageChange(module=module, old_coverage=old))
        elif old is not None and new is not None:
            delta = abs(new - old)
            if delta >= threshold:
                changes.append(CoverageChange(module=module, old_coverage=old, new_coverage=new))

    return changes


# ---------------------------------------------------------------------------
# Page mapping
# ---------------------------------------------------------------------------

# Map feature types to affected pages
PAGE_MAPPINGS = {
    "tools": [
        "docs/mcp-server/index.md",  # Main MCP docs
        "index.njk",  # Homepage mentions tool count
        "architecture/index.md",  # Architecture overview
    ],
    "modes": [
        "docs/modes/index.md",  # Modes documentation
        "modes/index.njk",  # Modes listing page
        "index.njk",  # Homepage mentions mode count
    ],
    "coverage": [
        "architecture/index.md",  # Quality metrics
    ],
    "safety": [
        "safety-pipeline/index.md",  # Safety pipeline docs
    ],
}

# Additional specific mappings for certain tool categories
TOOL_CATEGORY_PAGES = {
    "bip_": ["docs/mcp-server/index.md"],  # Build-in-public tools
    "figma_": ["docs/mcp-server/index.md"],  # Figma tools
    "security": ["safety-pipeline/index.md", "docs/mcp-server/index.md"],
    "design": ["docs/mcp-server/index.md"],
    "tdd": ["safety-pipeline/index.md", "docs/mcp-server/index.md"],
    "audit": ["safety-pipeline/index.md", "docs/mcp-server/index.md"],
}


def map_changes_to_pages(
    tool_changes: list[ToolChange],
    mode_changes: list[ModeChange],
    coverage_changes: list[CoverageChange],
    site_dir: Optional[str] = None,
) -> list[PageUpdate]:
    """Map detected changes to pages that need updates."""
    pages: dict[str, PageUpdate] = {}

    if site_dir is None:
        paths = get_user_paths()
        site_dir = os.path.join(os.path.dirname(paths.root), "site", "src")

    def add_page(path: str, reason: str, change: str, priority: str = "normal"):
        full_path = os.path.join(site_dir, path)
        if path not in pages:
            pages[path] = PageUpdate(path=full_path, reason=reason, priority=priority)
        pages[path].changes.append(change)
        # Upgrade priority if needed
        if priority == "high" and pages[path].priority != "high":
            pages[path].priority = "high"

    # Process tool changes
    if tool_changes:
        for page in PAGE_MAPPINGS["tools"]:
            add_page(
                page,
                "MCP tools changed",
                f"{len(tool_changes)} tool(s) changed",
                priority="high" if any(t.change_type == "added" for t in tool_changes) else "normal"
            )

        # Check for specific tool categories
        for tool in tool_changes:
            for prefix, pages_list in TOOL_CATEGORY_PAGES.items():
                if tool.name.startswith(prefix) or prefix in tool.name:
                    for page in pages_list:
                        add_page(page, f"Tool '{tool.name}' {tool.change_type}", tool.name)

    # Process mode changes
    if mode_changes:
        for page in PAGE_MAPPINGS["modes"]:
            add_page(
                page,
                "Modes changed",
                f"{len(mode_changes)} mode(s) changed",
                priority="high" if any(m.change_type == "added" for m in mode_changes) else "normal"
            )

    # Process coverage changes
    if coverage_changes:
        for page in PAGE_MAPPINGS["coverage"]:
            add_page(
                page,
                "Test coverage changed",
                f"{len(coverage_changes)} module(s) with coverage changes",
                priority="low"
            )

    return list(pages.values())


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def detect_site_revisions(
    home: Optional[str] = None,
    baseline_tools: Optional[dict[str, str]] = None,
    baseline_modes: Optional[dict[str, Optional[str]]] = None,
    baseline_coverage: Optional[dict[str, float]] = None,
    site_dir: Optional[str] = None,
) -> SiteRevisionResult:
    """Detect all feature changes and map to affected site pages.

    Args:
        home: Home directory for Crux paths
        baseline_tools: Previous tool definitions (name -> docstring)
        baseline_modes: Previous mode definitions (name -> description)
        baseline_coverage: Previous coverage data (module -> percentage)
        site_dir: Site source directory

    Returns:
        SiteRevisionResult with all detected changes and affected pages
    """
    paths = get_user_paths(home)

    # Detect tool changes
    current_tools = get_current_tools(home)
    tool_changes = detect_tool_changes_from_dicts(current_tools, baseline_tools)

    # Detect mode changes
    current_modes = get_current_modes(home)
    mode_changes = detect_mode_changes(current_modes, baseline_modes)

    # Coverage changes need baseline to be meaningful
    coverage_changes = []
    if baseline_coverage:
        # Would need current coverage report - skipped if not available
        pass

    # Map to pages
    pages_to_update = map_changes_to_pages(
        tool_changes, mode_changes, coverage_changes, site_dir
    )

    return SiteRevisionResult(
        tool_changes=tool_changes,
        mode_changes=mode_changes,
        coverage_changes=coverage_changes,
        pages_to_update=pages_to_update,
    )


def detect_tool_changes_from_dicts(
    current: dict[str, str],
    baseline: Optional[dict[str, str]] = None,
) -> list[ToolChange]:
    """Detect tool changes from pre-parsed dicts."""
    if baseline is None:
        baseline = {}

    changes = []

    for name, docstring in current.items():
        if name not in baseline:
            changes.append(ToolChange(name=name, change_type="added", docstring=docstring))
        elif baseline[name] != docstring:
            changes.append(ToolChange(name=name, change_type="modified", docstring=docstring))

    for name in baseline:
        if name not in current:
            changes.append(ToolChange(name=name, change_type="removed"))

    return changes


def get_tool_count(home: Optional[str] = None) -> int:
    """Get the current number of MCP tools."""
    return len(get_current_tools(home))


def get_mode_count(home: Optional[str] = None) -> int:
    """Get the current number of modes."""
    return len(get_current_modes(home))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    import json
    import sys

    home = sys.argv[1] if len(sys.argv) > 1 else None

    result = detect_site_revisions(home=home)

    print(json.dumps(result.to_dict(), indent=2))

    # Summary
    summary = result.to_dict()["summary"]
    print(f"\nSummary:", file=sys.stderr)
    print(f"  Tools: {get_tool_count(home)}", file=sys.stderr)
    print(f"  Modes: {get_mode_count(home)}", file=sys.stderr)
    print(f"  Pages to update: {summary['pages_affected']}", file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    main()
