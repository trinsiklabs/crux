"""Tests for impact.lsp_signals — LSP symbol matching for impact analysis."""

import json
import os
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from scripts.lib.impact.lsp_signals import (
    symbol_matches, reference_graph, check_lsp,
    _query_symbols, _query_references, _uri_to_relpath,
)


class TestCheckLsp:
    def test_returns_false_when_no_lsp(self):
        assert check_lsp("/nonexistent/path") is False

    def test_returns_false_when_check_fails(self, tmp_path):
        # Real dir but no LSP running
        assert check_lsp(str(tmp_path)) is False


class TestSymbolMatches:
    def test_returns_dict(self):
        result = symbol_matches("/nonexistent", ["auth"])
        assert isinstance(result, dict)

    def test_returns_empty_when_no_lsp(self, tmp_path):
        result = symbol_matches(str(tmp_path), ["auth"])
        assert result == {}

    def test_returns_empty_for_empty_keywords(self, tmp_path):
        result = symbol_matches(str(tmp_path), [])
        assert result == {}

    def test_with_mock_lsp_response(self, tmp_path):
        """Simulate LSP workspace/symbol response."""
        symbols = [
            {"name": "AuthService", "location": {"uri": f"file://{tmp_path}/auth.py"}},
            {"name": "authenticate", "location": {"uri": f"file://{tmp_path}/auth.py"}},
            {"name": "Database", "location": {"uri": f"file://{tmp_path}/db.py"}},
        ]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_symbols", return_value=symbols):
                result = symbol_matches(str(tmp_path), ["auth"])
        assert "auth.py" in result
        assert result["auth.py"] > result.get("db.py", 0)

    def test_multiple_keywords_accumulate(self, tmp_path):
        symbols_auth = [
            {"name": "AuthService", "location": {"uri": f"file://{tmp_path}/auth.py"}},
        ]
        symbols_db = [
            {"name": "Database", "location": {"uri": f"file://{tmp_path}/db.py"}},
        ]
        def fake_query(root, kw):
            if "auth" in kw:
                return symbols_auth
            if "db" in kw:
                return symbols_db
            return []

        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_symbols", side_effect=fake_query):
                result = symbol_matches(str(tmp_path), ["auth", "db"])
        assert "auth.py" in result
        assert "db.py" in result


class TestReferenceGraph:
    def test_returns_list(self):
        result = reference_graph("/nonexistent", "auth.py")
        assert isinstance(result, list)

    def test_returns_empty_when_no_lsp(self, tmp_path):
        result = reference_graph(str(tmp_path), "auth.py")
        assert result == []

    def test_with_mock_references(self, tmp_path):
        refs = [
            {"uri": f"file://{tmp_path}/api.py", "range": {}},
            {"uri": f"file://{tmp_path}/test_auth.py", "range": {}},
        ]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_references", return_value=refs):
                result = reference_graph(str(tmp_path), "auth.py")
        assert "api.py" in result
        assert "test_auth.py" in result

    def test_excludes_self_references(self, tmp_path):
        refs = [
            {"uri": f"file://{tmp_path}/auth.py", "range": {}},
            {"uri": f"file://{tmp_path}/api.py", "range": {}},
        ]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_references", return_value=refs):
                result = reference_graph(str(tmp_path), "auth.py")
        assert "auth.py" not in result
        assert "api.py" in result

class TestStubs:
    def test_query_symbols_returns_empty(self):
        assert _query_symbols("/any", "auth") == []

    def test_query_references_returns_empty(self):
        assert _query_references("/any", "auth.py") == []


class TestUriToRelpath:
    def test_valid_file_uri(self):
        assert _uri_to_relpath("file:///home/user/proj/auth.py", "/home/user/proj") == "auth.py"

    def test_non_file_scheme(self):
        assert _uri_to_relpath("http://example.com/auth.py", "/home") is None

    def test_outside_root(self):
        assert _uri_to_relpath("file:///other/path/auth.py", "/home/user/proj") is None


class TestSymbolMatchesEdge:
    def test_symbol_without_uri(self, tmp_path):
        symbols = [{"name": "Auth", "location": {}}]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_symbols", return_value=symbols):
                result = symbol_matches(str(tmp_path), ["auth"])
        assert result == {}

    def test_symbol_uri_outside_root(self, tmp_path):
        symbols = [{"name": "Auth", "location": {"uri": "file:///other/path/auth.py"}}]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_symbols", return_value=symbols):
                result = symbol_matches(str(tmp_path), ["auth"])
        assert result == {}

    def test_symbol_no_keyword_in_name(self, tmp_path):
        """Symbol exists but keyword doesn't match name — gets score of 1."""
        symbols = [{"name": "FooBar", "location": {"uri": f"file://{tmp_path}/foo.py"}}]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_symbols", return_value=symbols):
                result = symbol_matches(str(tmp_path), ["baz"])
        assert "foo.py" in result


class TestReferenceGraphEdge:
    def test_deduplicates(self, tmp_path):
        refs = [
            {"uri": f"file://{tmp_path}/api.py", "range": {}},
            {"uri": f"file://{tmp_path}/api.py", "range": {}},
        ]
        with patch("scripts.lib.impact.lsp_signals.check_lsp", return_value=True):
            with patch("scripts.lib.impact.lsp_signals._query_references", return_value=refs):
                result = reference_graph(str(tmp_path), "auth.py")
        assert result.count("api.py") == 1
