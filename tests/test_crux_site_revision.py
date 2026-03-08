"""Tests for crux_site_revision.py — site content auto-revision."""

import os
import tempfile

import pytest

from scripts.lib.crux_site_revision import (
    ToolChange,
    ModeChange,
    CoverageChange,
    PageUpdate,
    SiteRevisionResult,
    parse_mcp_tools,
    detect_tool_changes,
    get_modes_from_dir,
    detect_mode_changes,
    parse_mode_description,
    parse_coverage_report,
    detect_coverage_changes,
    map_changes_to_pages,
    detect_site_revisions,
    detect_tool_changes_from_dicts,
    get_tool_count,
    get_mode_count,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_mcp_content():
    return '''
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("crux")

@mcp.tool()
def lookup_knowledge(query: str) -> dict:
    """Search knowledge entries by keyword.

    Args:
        query: Search term
    """
    return {}

@mcp.tool()
def get_session_state() -> dict:
    """Get the current Crux session state."""
    return {}

@mcp.tool()
def validate_script(content: str) -> dict:
    """Validate a script against safety rules.

    More details here.
    """
    return {}
'''


@pytest.fixture
def sample_mode_content():
    return '''---
name: security
description: Security-focused code review and hardening
temperature: 0.3
---

# Security Mode

You are a security expert.
'''


# ---------------------------------------------------------------------------
# ToolChange tests
# ---------------------------------------------------------------------------

class TestToolChange:
    def test_creates_tool_change(self):
        tc = ToolChange(name="lookup", change_type="added", docstring="Search stuff")
        assert tc.name == "lookup"
        assert tc.change_type == "added"
        assert tc.docstring == "Search stuff"

    def test_optional_docstring(self):
        tc = ToolChange(name="removed_tool", change_type="removed")
        assert tc.docstring is None


# ---------------------------------------------------------------------------
# ModeChange tests
# ---------------------------------------------------------------------------

class TestModeChange:
    def test_creates_mode_change(self):
        mc = ModeChange(name="security", change_type="added", description="Security review")
        assert mc.name == "security"
        assert mc.change_type == "added"
        assert mc.description == "Security review"


# ---------------------------------------------------------------------------
# CoverageChange tests
# ---------------------------------------------------------------------------

class TestCoverageChange:
    def test_calculates_delta(self):
        tc = CoverageChange(module="crux_mcp", old_coverage=80.0, new_coverage=85.0)
        assert tc.delta == 5.0

    def test_delta_none_without_both(self):
        tc = CoverageChange(module="crux_mcp", new_coverage=85.0)
        assert tc.delta is None

    def test_negative_delta(self):
        tc = CoverageChange(module="crux_mcp", old_coverage=90.0, new_coverage=85.0)
        assert tc.delta == -5.0


# ---------------------------------------------------------------------------
# SiteRevisionResult tests
# ---------------------------------------------------------------------------

class TestSiteRevisionResult:
    def test_to_dict(self):
        result = SiteRevisionResult(
            tool_changes=[ToolChange(name="new_tool", change_type="added", docstring="A new tool")],
            mode_changes=[ModeChange(name="new_mode", change_type="added", description="A new mode")],
            pages_to_update=[PageUpdate(path="/site/index.njk", reason="Tools changed", changes=["1 tool added"])],
        )
        d = result.to_dict()
        assert d["summary"]["tools_changed"] == 1
        assert d["summary"]["modes_changed"] == 1
        assert d["summary"]["pages_affected"] == 1
        assert d["tool_changes"][0]["name"] == "new_tool"
        assert d["mode_changes"][0]["name"] == "new_mode"

    def test_empty_result(self):
        result = SiteRevisionResult()
        d = result.to_dict()
        assert d["summary"]["tools_changed"] == 0
        assert d["summary"]["pages_affected"] == 0


# ---------------------------------------------------------------------------
# parse_mcp_tools tests
# ---------------------------------------------------------------------------

class TestParseMcpTools:
    def test_extracts_tools(self, sample_mcp_content):
        tools = parse_mcp_tools(sample_mcp_content)
        assert "lookup_knowledge" in tools
        assert "get_session_state" in tools
        assert "validate_script" in tools

    def test_extracts_first_line_of_docstring(self, sample_mcp_content):
        tools = parse_mcp_tools(sample_mcp_content)
        assert tools["lookup_knowledge"] == "Search knowledge entries by keyword."
        assert tools["get_session_state"] == "Get the current Crux session state."
        assert tools["validate_script"] == "Validate a script against safety rules."

    def test_empty_content(self):
        tools = parse_mcp_tools("")
        assert tools == {}

    def test_no_tools(self):
        content = "def regular_function(): pass"
        tools = parse_mcp_tools(content)
        assert tools == {}


# ---------------------------------------------------------------------------
# detect_tool_changes tests
# ---------------------------------------------------------------------------

class TestDetectToolChanges:
    def test_detects_added_tools(self, sample_mcp_content):
        changes = detect_tool_changes(sample_mcp_content, baseline_content="")
        added = [c for c in changes if c.change_type == "added"]
        assert len(added) == 3
        names = {c.name for c in added}
        assert "lookup_knowledge" in names

    def test_detects_removed_tools(self):
        baseline = '''
@mcp.tool()
def old_tool() -> dict:
    """Old tool that was removed."""
    return {}
'''
        current = ""
        changes = detect_tool_changes(current, baseline)
        removed = [c for c in changes if c.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].name == "old_tool"

    def test_detects_modified_tools(self):
        baseline = '''
@mcp.tool()
def my_tool() -> dict:
    """Original description."""
    return {}
'''
        current = '''
@mcp.tool()
def my_tool() -> dict:
    """Updated description."""
    return {}
'''
        changes = detect_tool_changes(current, baseline)
        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) == 1
        assert modified[0].name == "my_tool"
        assert modified[0].docstring == "Updated description."

    def test_no_baseline_empty_string(self, sample_mcp_content):
        # Empty string baseline means we're comparing against nothing
        changes = detect_tool_changes(sample_mcp_content, baseline_content="")
        # All tools appear as added when baseline is empty
        assert len(changes) == 3
        assert all(c.change_type == "added" for c in changes)

    def test_no_baseline_none(self, sample_mcp_content):
        # None baseline means no comparison - all tools are "added"
        changes = detect_tool_changes(sample_mcp_content, baseline_content=None)
        assert len(changes) == 3
        assert all(c.change_type == "added" for c in changes)


# ---------------------------------------------------------------------------
# parse_mode_description tests
# ---------------------------------------------------------------------------

class TestParseModeDescription:
    def test_extracts_description(self, sample_mode_content):
        desc = parse_mode_description(sample_mode_content)
        assert desc == "Security-focused code review and hardening"

    def test_no_description(self):
        content = "# Just a header\n\nSome content."
        desc = parse_mode_description(content)
        assert desc is None


# ---------------------------------------------------------------------------
# get_modes_from_dir tests
# ---------------------------------------------------------------------------

class TestGetModesFromDir:
    def test_gets_modes(self, temp_dir, sample_mode_content):
        # Create mode files
        mode_file = os.path.join(temp_dir, "security.md")
        with open(mode_file, "w") as f:
            f.write(sample_mode_content)

        modes = get_modes_from_dir(temp_dir)
        assert "security" in modes
        assert modes["security"] == "Security-focused code review and hardening"

    def test_skips_template_files(self, temp_dir):
        # Create template file
        template = os.path.join(temp_dir, "_template.md")
        with open(template, "w") as f:
            f.write("# Template")

        modes = get_modes_from_dir(temp_dir)
        assert "_template" not in modes
        assert len(modes) == 0

    def test_nonexistent_dir(self):
        modes = get_modes_from_dir("/nonexistent/path")
        assert modes == {}


# ---------------------------------------------------------------------------
# detect_mode_changes tests
# ---------------------------------------------------------------------------

class TestDetectModeChanges:
    def test_detects_added_modes(self):
        current = {"security": "Security review", "debug": "Debugging"}
        baseline = {"security": "Security review"}
        changes = detect_mode_changes(current, baseline)
        added = [c for c in changes if c.change_type == "added"]
        assert len(added) == 1
        assert added[0].name == "debug"

    def test_detects_removed_modes(self):
        current = {"security": "Security review"}
        baseline = {"security": "Security review", "old_mode": "Old"}
        changes = detect_mode_changes(current, baseline)
        removed = [c for c in changes if c.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].name == "old_mode"

    def test_detects_modified_modes(self):
        current = {"security": "Updated description"}
        baseline = {"security": "Original description"}
        changes = detect_mode_changes(current, baseline)
        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) == 1
        assert modified[0].description == "Updated description"

    def test_no_changes(self):
        current = {"security": "Same description"}
        baseline = {"security": "Same description"}
        changes = detect_mode_changes(current, baseline)
        assert len(changes) == 0


# ---------------------------------------------------------------------------
# parse_coverage_report tests
# ---------------------------------------------------------------------------

class TestParseCoverageReport:
    def test_parses_coverage(self):
        report = """
Name                         Stmts   Miss  Cover
-------------------------------------------------
scripts/lib/crux_mcp.py        100     10    90%
scripts/lib/crux_paths.py       50      5    90%
scripts/lib/crux_session.py     80     20    75%
-------------------------------------------------
TOTAL                          230     35    85%
"""
        coverage = parse_coverage_report(report)
        assert coverage["scripts/lib/crux_mcp.py"] == 90.0
        assert coverage["scripts/lib/crux_paths.py"] == 90.0
        assert coverage["scripts/lib/crux_session.py"] == 75.0

    def test_empty_report(self):
        coverage = parse_coverage_report("")
        assert coverage == {}


# ---------------------------------------------------------------------------
# detect_coverage_changes tests
# ---------------------------------------------------------------------------

class TestDetectCoverageChanges:
    def test_detects_significant_changes(self):
        current = {"module_a": 85.0, "module_b": 70.0}
        baseline = {"module_a": 80.0, "module_b": 70.0}
        changes = detect_coverage_changes(current, baseline, threshold=5.0)
        assert len(changes) == 1
        assert changes[0].module == "module_a"
        assert changes[0].delta == 5.0

    def test_ignores_small_changes(self):
        current = {"module_a": 82.0}
        baseline = {"module_a": 80.0}
        changes = detect_coverage_changes(current, baseline, threshold=5.0)
        assert len(changes) == 0

    def test_new_module(self):
        current = {"new_module": 90.0}
        baseline = {}
        changes = detect_coverage_changes(current, baseline)
        assert len(changes) == 1
        assert changes[0].module == "new_module"
        assert changes[0].new_coverage == 90.0
        assert changes[0].old_coverage is None

    def test_removed_module(self):
        current = {}
        baseline = {"old_module": 80.0}
        changes = detect_coverage_changes(current, baseline)
        assert len(changes) == 1
        assert changes[0].module == "old_module"
        assert changes[0].old_coverage == 80.0

    def test_no_baseline(self):
        current = {"module_a": 85.0}
        changes = detect_coverage_changes(current, None)
        assert len(changes) == 0


# ---------------------------------------------------------------------------
# map_changes_to_pages tests
# ---------------------------------------------------------------------------

class TestMapChangesToPages:
    def test_maps_tool_changes(self, temp_dir):
        tool_changes = [ToolChange(name="new_tool", change_type="added", docstring="New tool")]
        pages = map_changes_to_pages(tool_changes, [], [], site_dir=temp_dir)
        assert len(pages) > 0
        paths = [p.path for p in pages]
        assert any("mcp-server" in p for p in paths)
        assert any("index.njk" in p for p in paths)

    def test_maps_mode_changes(self, temp_dir):
        mode_changes = [ModeChange(name="new_mode", change_type="added", description="New mode")]
        pages = map_changes_to_pages([], mode_changes, [], site_dir=temp_dir)
        assert len(pages) > 0
        paths = [p.path for p in pages]
        assert any("modes" in p for p in paths)

    def test_maps_security_tools(self, temp_dir):
        tool_changes = [ToolChange(name="security_audit", change_type="added", docstring="Security audit")]
        pages = map_changes_to_pages(tool_changes, [], [], site_dir=temp_dir)
        paths = [p.path for p in pages]
        assert any("safety-pipeline" in p for p in paths)

    def test_high_priority_for_added(self, temp_dir):
        tool_changes = [ToolChange(name="new_tool", change_type="added", docstring="New")]
        pages = map_changes_to_pages(tool_changes, [], [], site_dir=temp_dir)
        assert any(p.priority == "high" for p in pages)

    def test_aggregates_changes(self, temp_dir):
        tool_changes = [
            ToolChange(name="tool1", change_type="added", docstring="Tool 1"),
            ToolChange(name="tool2", change_type="added", docstring="Tool 2"),
        ]
        pages = map_changes_to_pages(tool_changes, [], [], site_dir=temp_dir)
        # Should not duplicate pages, just aggregate changes
        mcp_pages = [p for p in pages if "mcp-server" in p.path]
        assert len(mcp_pages) == 1
        assert len(mcp_pages[0].changes) >= 1


# ---------------------------------------------------------------------------
# detect_tool_changes_from_dicts tests
# ---------------------------------------------------------------------------

class TestDetectToolChangesFromDicts:
    def test_detects_added(self):
        current = {"new_tool": "Description"}
        baseline = {}
        changes = detect_tool_changes_from_dicts(current, baseline)
        assert len(changes) == 1
        assert changes[0].change_type == "added"

    def test_no_baseline(self):
        current = {"tool": "Description"}
        changes = detect_tool_changes_from_dicts(current, None)
        # All tools are "added" when there's no baseline
        assert len(changes) == 1


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestDetectSiteRevisions:
    def test_returns_result(self, temp_dir):
        # Create minimal structure
        crux_dir = os.path.join(temp_dir, ".crux")
        scripts_lib = os.path.join(crux_dir, "scripts", "lib")
        modes_dir = os.path.join(crux_dir, "modes")
        os.makedirs(scripts_lib)
        os.makedirs(modes_dir)

        # Create minimal MCP server
        mcp_server = os.path.join(scripts_lib, "crux_mcp_server.py")
        with open(mcp_server, "w") as f:
            f.write('''
@mcp.tool()
def test_tool() -> dict:
    """A test tool."""
    return {}
''')

        # Create a mode
        mode_file = os.path.join(modes_dir, "test-mode.md")
        with open(mode_file, "w") as f:
            f.write("---\ndescription: Test mode\n---\n# Test")

        result = detect_site_revisions(home=temp_dir)
        assert isinstance(result, SiteRevisionResult)

    def test_with_baselines(self, temp_dir):
        # Create minimal structure
        crux_dir = os.path.join(temp_dir, ".crux")
        scripts_lib = os.path.join(crux_dir, "scripts", "lib")
        modes_dir = os.path.join(crux_dir, "modes")
        os.makedirs(scripts_lib)
        os.makedirs(modes_dir)

        # Create MCP server with tools
        mcp_server = os.path.join(scripts_lib, "crux_mcp_server.py")
        with open(mcp_server, "w") as f:
            f.write('''
@mcp.tool()
def new_tool() -> dict:
    """A new tool."""
    return {}
''')

        baseline_tools = {"old_tool": "Old tool description"}
        result = detect_site_revisions(home=temp_dir, baseline_tools=baseline_tools)

        # Should detect added tool and removed tool
        assert len(result.tool_changes) == 2
        added = [c for c in result.tool_changes if c.change_type == "added"]
        removed = [c for c in result.tool_changes if c.change_type == "removed"]
        assert len(added) == 1
        assert len(removed) == 1
        assert added[0].name == "new_tool"
        assert removed[0].name == "old_tool"


# ---------------------------------------------------------------------------
# Count functions tests
# ---------------------------------------------------------------------------

class TestCountFunctions:
    def test_get_tool_count(self, temp_dir):
        crux_dir = os.path.join(temp_dir, ".crux")
        scripts_lib = os.path.join(crux_dir, "scripts", "lib")
        os.makedirs(scripts_lib)

        mcp_server = os.path.join(scripts_lib, "crux_mcp_server.py")
        with open(mcp_server, "w") as f:
            f.write('''
@mcp.tool()
def tool1() -> dict:
    """Tool 1."""
    return {}

@mcp.tool()
def tool2() -> dict:
    """Tool 2."""
    return {}
''')

        count = get_tool_count(home=temp_dir)
        assert count == 2

    def test_get_mode_count(self, temp_dir):
        crux_dir = os.path.join(temp_dir, ".crux")
        modes_dir = os.path.join(crux_dir, "modes")
        os.makedirs(modes_dir)

        for name in ["mode1", "mode2", "mode3"]:
            with open(os.path.join(modes_dir, f"{name}.md"), "w") as f:
                f.write(f"# {name}")

        count = get_mode_count(home=temp_dir)
        assert count == 3

    def test_missing_dirs(self, temp_dir):
        assert get_tool_count(home=temp_dir) == 0
        assert get_mode_count(home=temp_dir) == 0
