"""Tests for audit backend abstraction (PLAN-169, PLAN-170)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.lib.crux_audit_backend import (
    AuditBackend,
    AuditFinding,
    AuditRequiredError,
    AuditResult,
    ClaudeSubagentBackend,
    DisabledBackend,
    OllamaBackend,
    _format_audit_prompt,
    _parse_audit_response,
    detect_context_mode,
    detect_opencode_context,
    get_audit_backend,
    get_backend_status,
)


# ---------------------------------------------------------------------------
# AuditResult tests
# ---------------------------------------------------------------------------


class TestAuditResult:
    def test_passed_result(self):
        result = AuditResult(passed=True, skipped=False, backend="test")
        assert result.passed is True
        assert result.skipped is False
        assert result.findings == []

    def test_failed_result_with_findings(self):
        finding = AuditFinding(
            severity="high",
            title="Command injection",
            description="Unsafe variable expansion",
        )
        result = AuditResult(
            passed=False,
            skipped=False,
            findings=[finding],
            backend="test",
        )
        assert result.passed is False
        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"

    def test_skipped_result(self):
        result = AuditResult(
            passed=True,
            skipped=True,
            reason="Ollama unavailable",
            backend="test",
        )
        assert result.skipped is True
        assert "Ollama" in result.reason


# ---------------------------------------------------------------------------
# OllamaBackend tests
# ---------------------------------------------------------------------------


class TestOllamaBackend:
    def test_name_includes_model(self):
        backend = OllamaBackend(model="qwen3:8b")
        assert "qwen3:8b" in backend.name
        assert "Ollama" in backend.name

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_is_available_when_running(self, mock_check):
        mock_check.return_value = True
        backend = OllamaBackend()
        assert backend.is_available() is True

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_is_available_when_down(self, mock_check):
        mock_check.return_value = False
        backend = OllamaBackend()
        assert backend.is_available() is False

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_audit_success(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "response": json.dumps({
                "passed": True,
                "findings": [],
                "summary": "No issues found",
            }),
        }
        backend = OllamaBackend()
        result = backend.audit("echo hello", "low", "system prompt")

        assert result.passed is True
        assert result.skipped is False
        assert result.summary == "No issues found"

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_audit_with_findings(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "response": json.dumps({
                "passed": False,
                "findings": [
                    {
                        "severity": "high",
                        "title": "Command injection",
                        "description": "Unsafe use of $VAR",
                    }
                ],
                "summary": "Security issues found",
            }),
        }
        backend = OllamaBackend()
        result = backend.audit("rm -rf $VAR", "high", "system prompt")

        assert result.passed is False
        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_audit_ollama_failure(self, mock_generate):
        mock_generate.return_value = {"success": False, "error": "Connection refused"}
        backend = OllamaBackend()
        result = backend.audit("echo hello", "low", "system prompt")

        assert result.passed is True  # Skipped means pass
        assert result.skipped is True
        assert "failed" in result.reason.lower()

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_audit_invalid_json_response(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "response": "This is not JSON",
        }
        backend = OllamaBackend()
        result = backend.audit("echo hello", "low", "system prompt")

        assert result.skipped is True
        assert "parse" in result.reason.lower()


# ---------------------------------------------------------------------------
# ClaudeSubagentBackend tests
# ---------------------------------------------------------------------------


class TestClaudeSubagentBackend:
    def test_name(self):
        backend = ClaudeSubagentBackend()
        assert "Claude" in backend.name
        assert "subagent" in backend.name

    @patch("subprocess.run")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_is_available_with_claude(self, mock_find, mock_run):
        mock_find.return_value = "/usr/local/bin/claude"
        backend = ClaudeSubagentBackend()
        backend._claude_path = "/usr/local/bin/claude"
        assert backend.is_available() is True

    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_is_available_without_claude(self, mock_find):
        mock_find.return_value = None
        backend = ClaudeSubagentBackend()
        backend._claude_path = None
        assert backend.is_available() is False

    def test_audit_without_claude_binary(self):
        backend = ClaudeSubagentBackend()
        backend._claude_path = None
        result = backend.audit("echo hello", "low", "system prompt")

        assert result.skipped is True
        assert "not found" in result.reason.lower()


# ---------------------------------------------------------------------------
# DisabledBackend tests
# ---------------------------------------------------------------------------


class TestDisabledBackend:
    def test_name_indicates_disabled(self):
        backend = DisabledBackend()
        assert "DISABLED" in backend.name

    def test_is_always_available(self):
        backend = DisabledBackend()
        assert backend.is_available() is True

    def test_audit_always_skips(self):
        backend = DisabledBackend()
        result = backend.audit("rm -rf /", "high", "system prompt")

        assert result.passed is True
        assert result.skipped is True
        assert "No audit backend" in result.reason


# ---------------------------------------------------------------------------
# Backend selection tests
# ---------------------------------------------------------------------------


class TestGetAuditBackend:
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_prefers_ollama_when_available(self, mock_check):
        mock_check.return_value = True
        # Clear cache
        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        backend = get_audit_backend(force_refresh=True)
        assert isinstance(backend, OllamaBackend)

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_falls_back_to_claude(self, mock_find, mock_check):
        mock_check.return_value = False
        mock_find.return_value = "/usr/local/bin/claude"

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        backend = get_audit_backend(force_refresh=True)
        assert isinstance(backend, ClaudeSubagentBackend)

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_falls_back_to_disabled(self, mock_find, mock_check):
        mock_check.return_value = False
        mock_find.return_value = None

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        backend = get_audit_backend(force_refresh=True)
        assert isinstance(backend, DisabledBackend)


class TestGetBackendStatus:
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_returns_status_dict(self, mock_find, mock_check):
        mock_check.return_value = True
        mock_find.return_value = "/usr/local/bin/claude"

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        status = get_backend_status()

        assert "active_backend" in status
        assert "ollama_available" in status
        assert "claude_available" in status
        assert "backends" in status


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestFormatAuditPrompt:
    def test_includes_risk_level(self):
        prompt = _format_audit_prompt("echo hello", "high")
        assert "high-risk" in prompt

    def test_includes_script_content(self):
        prompt = _format_audit_prompt("rm -rf /tmp", "low")
        assert "rm -rf /tmp" in prompt

    def test_includes_code_block(self):
        prompt = _format_audit_prompt("echo test", "medium")
        assert "```bash" in prompt


class TestParseAuditResponse:
    def test_parses_valid_json(self):
        response = json.dumps({"passed": True, "findings": []})
        result = _parse_audit_response(response)
        assert result["passed"] is True

    def test_parses_json_in_code_block(self):
        response = "```json\n{\"passed\": false, \"findings\": []}\n```"
        result = _parse_audit_response(response)
        assert result["passed"] is False

    def test_returns_none_for_invalid_json(self):
        result = _parse_audit_response("not json")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = _parse_audit_response("")
        assert result is None


# ---------------------------------------------------------------------------
# Protocol compliance tests
# ---------------------------------------------------------------------------


class TestBackendProtocol:
    def test_ollama_implements_protocol(self):
        backend = OllamaBackend()
        assert isinstance(backend, AuditBackend)

    def test_claude_implements_protocol(self):
        backend = ClaudeSubagentBackend()
        assert isinstance(backend, AuditBackend)

    def test_disabled_implements_protocol(self):
        backend = DisabledBackend()
        assert isinstance(backend, AuditBackend)


# ---------------------------------------------------------------------------
# OpenCode enforcement tests (PLAN-170)
# ---------------------------------------------------------------------------


class TestOpenCodeDetection:
    def test_detect_opencode_from_env(self):
        with patch.dict("os.environ", {"CRUX_TOOL": "opencode"}):
            assert detect_opencode_context() is True

    def test_detect_claude_code_from_env(self):
        with patch.dict("os.environ", {"CRUX_TOOL": "claude-code"}):
            assert detect_opencode_context() is False

    def test_detect_claude_code_entry_point(self):
        with patch.dict("os.environ", {"CLAUDE_CODE_ENTRY_POINT": "1"}, clear=False):
            # Clear CRUX_TOOL to test fallback
            env = {"CLAUDE_CODE_ENTRY_POINT": "1"}
            with patch.dict("os.environ", env, clear=True):
                assert detect_opencode_context() is False

    def test_context_mode_unknown_default(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("pathlib.Path.exists", return_value=False):
                mode = detect_context_mode()
                assert mode == "unknown"


class TestOpenCodeEnforcement:
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch("scripts.lib.crux_audit_backend.detect_opencode_context")
    def test_opencode_raises_when_ollama_unavailable(self, mock_detect, mock_check):
        mock_detect.return_value = True
        mock_check.return_value = False

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        with pytest.raises(AuditRequiredError) as exc_info:
            get_audit_backend(force_refresh=True, context="auto")

        assert "OpenCode requires local Ollama" in str(exc_info.value)
        assert "ollama serve" in str(exc_info.value)

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_opencode_explicit_context_raises(self, mock_check):
        mock_check.return_value = False

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        with pytest.raises(AuditRequiredError):
            get_audit_backend(force_refresh=True, context="opencode")

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_opencode_with_ollama_works(self, mock_check):
        mock_check.return_value = True

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        backend = get_audit_backend(force_refresh=True, context="opencode")
        assert isinstance(backend, OllamaBackend)

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_claude_code_still_falls_back(self, mock_find, mock_check):
        mock_check.return_value = False
        mock_find.return_value = "/usr/local/bin/claude"

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        # Claude Code mode should still fall back
        backend = get_audit_backend(force_refresh=True, context="claude-code")
        assert isinstance(backend, ClaudeSubagentBackend)

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_enforce_opencode_can_be_disabled(self, mock_find, mock_check):
        mock_check.return_value = False
        mock_find.return_value = None  # No Claude either

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        # With enforce_opencode=False, should not raise even in opencode context
        backend = get_audit_backend(
            force_refresh=True,
            context="opencode",
            enforce_opencode=False,
        )
        # Falls through to DisabledBackend since both Ollama and Claude unavailable
        assert isinstance(backend, DisabledBackend)


class TestBackendStatusWithMode:
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch("scripts.lib.crux_audit_backend.detect_context_mode")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_status_shows_opencode_blocked(self, mock_find, mock_mode, mock_check):
        mock_check.return_value = False
        mock_mode.return_value = "opencode"
        mock_find.return_value = None

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        status = get_backend_status()

        assert status["context_mode"] == "opencode"
        assert status["ollama_required"] is True
        assert status["audit_blocked"] is True
        assert "BLOCKED" in status["active_backend"]

    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    @patch("scripts.lib.crux_audit_backend.detect_context_mode")
    @patch.object(ClaudeSubagentBackend, "_find_claude_binary")
    def test_status_shows_claude_code_fallback(self, mock_find, mock_mode, mock_check):
        mock_check.return_value = False
        mock_mode.return_value = "claude-code"
        mock_find.return_value = "/usr/local/bin/claude"

        import scripts.lib.crux_audit_backend as mod
        mod._cached_backend = None
        mod._cached_backend_check_time = 0

        status = get_backend_status()

        assert status["context_mode"] == "claude-code"
        assert status["ollama_required"] is False
        assert status["audit_blocked"] is False
