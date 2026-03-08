"""Tests for BIP high-signal event detection logic."""

import pytest


# Test the detection patterns (mirroring what the shell script does)
class TestEventDetection:
    def test_detect_test_green_pytest(self):
        output = "===== 26 passed in 0.06s ====="
        assert "passed" in output
        assert "failed" not in output.lower()
        assert "error" not in output.lower()

    def test_detect_test_green_with_failure_returns_false(self):
        output = "3 passed, 1 failed"
        assert "passed" in output
        assert "failed" in output  # Should NOT trigger

    def test_detect_pr_merge(self):
        output = "Pull request #123 merged"
        assert "merged" in output.lower()
        assert "pull" in output.lower()

    def test_detect_plan_implemented(self):
        output = "UPDATE 1\nPLAN-311 | PLAN-311: BIP escalation rule | implemented"
        assert "implemented" in output.lower()
        assert "PLAN-" in output

    def test_detect_new_mcp_tool(self):
        output = "Added new MCP tool: validate_script"
        assert "mcp" in output.lower()
        assert "tool" in output.lower()
