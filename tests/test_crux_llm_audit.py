"""Tests for crux_llm_audit.py — LLM-based script auditing for Gates 4-5.

Updated for PLAN-169 backend abstraction.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from scripts.lib.crux_llm_audit import (
    audit_script_8b,
    audit_script_32b,
)
from scripts.lib.crux_audit_backend import (
    _format_audit_prompt as format_audit_prompt,
    AuditResult,
    OllamaBackend,
)


SAMPLE_SCRIPT = """#!/bin/bash
set -euo pipefail
# Risk: medium
# Description: Deploy app
DRY_RUN="${DRY_RUN:-0}"
main() { echo "deploying"; }
main "$@"
"""

CLEAN_RESPONSE = json.dumps({
    "passed": True,
    "findings": [],
    "summary": "No security issues found.",
})

FINDINGS_RESPONSE = json.dumps({
    "passed": False,
    "findings": [{
        "severity": "high",
        "title": "Unquoted variable",
        "description": "DRY_RUN not quoted in conditional",
    }],
    "summary": "Security issues found",
})


# ---------------------------------------------------------------------------
# format_audit_prompt
# ---------------------------------------------------------------------------

class TestFormatAuditPrompt:
    def test_includes_script_content(self):
        prompt = format_audit_prompt("echo hello", "low")
        assert "echo hello" in prompt

    def test_includes_risk_level(self):
        prompt = format_audit_prompt("echo hello", "high")
        assert "high" in prompt.lower()

    def test_requests_json_response(self):
        prompt = format_audit_prompt("echo hello", "medium")
        assert "json" in prompt.lower()


# ---------------------------------------------------------------------------
# audit_script_8b
# ---------------------------------------------------------------------------

class TestAuditScript8b:
    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_clean_audit_passes(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        result = audit_script_8b(SAMPLE_SCRIPT, "medium")
        assert result["passed"] is True
        assert result["skipped"] is False
        assert len(result["findings"]) == 0

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_audit_with_findings_fails(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": FINDINGS_RESPONSE}
        result = audit_script_8b(SAMPLE_SCRIPT, "medium")
        assert result["passed"] is False
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "high"

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_ollama_unavailable_skips_gracefully(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": False, "error": "Connection refused"}
        result = audit_script_8b(SAMPLE_SCRIPT, "medium")
        assert result["passed"] is True
        assert result["skipped"] is True

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_malformed_llm_response_skips(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": "not json at all"}
        result = audit_script_8b(SAMPLE_SCRIPT, "medium")
        assert result["passed"] is True
        assert result["skipped"] is True

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_uses_8b_model(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        audit_script_8b(SAMPLE_SCRIPT, "low")
        call_args = mock_gen.call_args
        assert "qwen3:8b" in call_args.kwargs.get("model", "")

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_low_risk_still_audited(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        result = audit_script_8b(SAMPLE_SCRIPT, "low")
        assert result["skipped"] is False

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_custom_endpoint(self, mock_gen):
        """Custom endpoint forces OllamaBackend directly."""
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        result = audit_script_8b(SAMPLE_SCRIPT, "low", endpoint="http://gpu:11434")
        assert mock_gen.called
        assert "gpu:11434" in str(mock_gen.call_args)

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_custom_model(self, mock_gen):
        """Custom model is passed through."""
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        audit_script_8b(SAMPLE_SCRIPT, "low", endpoint="http://localhost:11434", model="llama3:8b")
        call_args = mock_gen.call_args
        assert call_args.kwargs.get("model") == "llama3:8b"

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_markdown_wrapped_json_response(self, mock_check, mock_gen):
        mock_check.return_value = True
        wrapped = "```json\n" + CLEAN_RESPONSE + "\n```"
        mock_gen.return_value = {"success": True, "response": wrapped}
        result = audit_script_8b(SAMPLE_SCRIPT, "medium")
        assert result["passed"] is True
        assert result["skipped"] is False

    def test_result_includes_backend_info(self):
        """Results now include backend field (PLAN-169)."""
        with patch("scripts.lib.crux_audit_backend.generate") as mock_gen:
            with patch("scripts.lib.crux_audit_backend.check_ollama_running") as mock_check:
                mock_check.return_value = True
                mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
                result = audit_script_8b(SAMPLE_SCRIPT, "medium")
                assert "backend" in result
                assert "Ollama" in result["backend"]


# ---------------------------------------------------------------------------
# audit_script_32b
# ---------------------------------------------------------------------------

class TestAuditScript32b:
    def test_skips_non_high_risk(self):
        result = audit_script_32b(SAMPLE_SCRIPT, "medium")
        assert result["passed"] is True
        assert result["skipped"] is True
        assert "high-risk" in result["reason"].lower() or "not high" in result["reason"].lower()

    def test_skips_low_risk(self):
        result = audit_script_32b(SAMPLE_SCRIPT, "low")
        assert result["skipped"] is True

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_high_risk_runs_audit(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        result = audit_script_32b(SAMPLE_SCRIPT, "high")
        assert result["skipped"] is False
        assert mock_gen.called

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_audit_with_findings_fails(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": FINDINGS_RESPONSE}
        result = audit_script_32b(SAMPLE_SCRIPT, "high")
        assert result["passed"] is False

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_ollama_unavailable_skips_gracefully(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": False, "error": "Connection refused"}
        result = audit_script_32b(SAMPLE_SCRIPT, "high")
        assert result["passed"] is True
        assert result["skipped"] is True

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_uses_32b_model(self, mock_gen):
        """Custom endpoint forces use of specified model."""
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        # Use explicit endpoint to force OllamaBackend with the 32b model
        audit_script_32b(SAMPLE_SCRIPT, "high", endpoint="http://localhost:11434")
        call_args = mock_gen.call_args
        assert "qwen3:32b" in call_args.kwargs.get("model", "")

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_custom_model(self, mock_gen):
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        audit_script_32b(SAMPLE_SCRIPT, "high", endpoint="http://localhost:11434", model="llama3:70b")
        call_args = mock_gen.call_args
        assert call_args.kwargs.get("model") == "llama3:70b"

    @patch("scripts.lib.crux_audit_backend.generate")
    @patch("scripts.lib.crux_audit_backend.check_ollama_running")
    def test_malformed_response_skips(self, mock_check, mock_gen):
        mock_check.return_value = True
        mock_gen.return_value = {"success": True, "response": "invalid json"}
        result = audit_script_32b(SAMPLE_SCRIPT, "high")
        assert result["skipped"] is True

    @patch("scripts.lib.crux_audit_backend.generate")
    def test_custom_endpoint(self, mock_gen):
        mock_gen.return_value = {"success": True, "response": CLEAN_RESPONSE}
        audit_script_32b(SAMPLE_SCRIPT, "high", endpoint="http://gpu:11434")
        assert mock_gen.called
