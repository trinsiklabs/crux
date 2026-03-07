"""Tests for crux_figma.py — Figma REST API client."""

import json
from unittest.mock import patch, MagicMock
import urllib.error

import pytest

from scripts.lib.crux_figma import (
    get_file,
    get_file_styles,
    get_file_components,
    get_images,
    extract_design_tokens,
    generate_token_css,
    generate_token_tailwind,
    _parse_color,
    _request,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(data, status=200):
    """Create a mock urllib response."""
    mock = MagicMock()
    mock.read.return_value = json.dumps(data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


SAMPLE_FILE = {
    "document": {
        "name": "Design System",
        "type": "CANVAS",
        "children": [
            {
                "name": "Primary",
                "type": "RECTANGLE",
                "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.4, "b": 0.8, "a": 1.0}}],
                "cornerRadius": 8,
                "children": [],
            },
            {
                "name": "Heading 1",
                "type": "TEXT",
                "style": {
                    "fontFamily": "Inter",
                    "fontSize": 32,
                    "fontWeight": 700,
                    "lineHeightPx": 40,
                },
                "fills": [],
                "children": [],
            },
            {
                "name": "Card",
                "type": "FRAME",
                "itemSpacing": 16,
                "cornerRadius": 12,
                "fills": [{"type": "SOLID", "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}}],
                "children": [
                    {
                        "name": "Body Text",
                        "type": "TEXT",
                        "style": {"fontFamily": "Inter", "fontSize": 16, "fontWeight": 400},
                        "fills": [],
                        "children": [],
                    },
                ],
            },
        ],
    }
}


# ---------------------------------------------------------------------------
# _request
# ---------------------------------------------------------------------------

class TestRequest:
    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_successful_request(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"key": "value"})
        result = _request("/v1/files/abc", "token123")
        assert result["success"] is True
        assert result["data"]["key"] == "value"

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        err = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        err.read = lambda: b"forbidden"
        mock_urlopen.side_effect = err
        result = _request("/v1/files/abc", "bad-token")
        assert result["success"] is False
        assert result["status"] == 403
        assert "403" in result["error"]

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_url_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        result = _request("/v1/files/abc", "token")
        assert result["success"] is False
        assert result["error"]  # Generic error message (PLAN-166)

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_generic_error(self, mock_urlopen):
        mock_urlopen.side_effect = RuntimeError("unexpected")
        result = _request("/v1/files/abc", "token")
        assert result["success"] is False
        assert result["error"]  # Generic error message (PLAN-166)

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_http_error_unreadable_body(self, mock_urlopen):
        err = urllib.error.HTTPError("url", 500, "Server Error", {}, None)
        err.read = lambda: (_ for _ in ()).throw(RuntimeError("can't read"))
        mock_urlopen.side_effect = err
        result = _request("/v1/files/abc", "token")
        assert result["success"] is False
        assert result["error"]  # Generic error, no body exposed (PLAN-166)


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

class TestApiFunctions:
    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_get_file(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"document": {}})
        result = get_file("filekey", "token")
        assert result["success"] is True

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_get_file_styles(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"meta": {"styles": []}})
        result = get_file_styles("filekey", "token")
        assert result["success"] is True

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_get_file_components(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"meta": {"components": []}})
        result = get_file_components("filekey", "token")
        assert result["success"] is True

    @patch("scripts.lib.crux_figma.urllib.request.urlopen")
    def test_get_images(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"images": {"1:2": "https://example.com/img.png"}})
        result = get_images("filekey", ["1:2", "3:4"], "token", fmt="svg")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# _parse_color
# ---------------------------------------------------------------------------

class TestParseColor:
    def test_opaque_color(self):
        assert _parse_color({"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}) == "#ff0000"

    def test_transparent_color(self):
        result = _parse_color({"r": 0.0, "g": 0.0, "b": 0.0, "a": 0.5})
        assert result == "#0000007f"

    def test_missing_alpha(self):
        assert _parse_color({"r": 0.0, "g": 1.0, "b": 0.0}) == "#00ff00"

    def test_invalid_color(self):
        assert _parse_color({}) is None

    def test_none_values(self):
        assert _parse_color({"r": None, "g": 0, "b": 0}) is None


# ---------------------------------------------------------------------------
# extract_design_tokens
# ---------------------------------------------------------------------------

class TestExtractDesignTokens:
    def test_extracts_colors(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        assert len(tokens["colors"]) >= 2  # Primary + Card bg

    def test_extracts_typography(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        assert "heading-1" in tokens["typography"]
        assert tokens["typography"]["heading-1"]["font_family"] == "Inter"
        assert tokens["typography"]["heading-1"]["font_size"] == 32

    def test_extracts_border_radius(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        assert 8 in tokens["border_radius"]
        assert 12 in tokens["border_radius"]

    def test_extracts_spacing(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        assert 16 in tokens["spacing"]

    def test_deduplicates_values(self):
        file_data = {
            "document": {
                "name": "test",
                "type": "CANVAS",
                "children": [
                    {"name": "a", "type": "FRAME", "cornerRadius": 8, "fills": [], "children": []},
                    {"name": "b", "type": "FRAME", "cornerRadius": 8, "fills": [], "children": []},
                ],
            }
        }
        tokens = extract_design_tokens(file_data)
        assert tokens["border_radius"].count(8) == 1

    def test_empty_document(self):
        tokens = extract_design_tokens({"document": {"name": "empty", "type": "CANVAS", "children": []}})
        assert tokens["colors"] == {}
        assert tokens["typography"] == {}

    def test_nested_children(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        assert "body-text" in tokens["typography"]

    def test_gradient_fill_ignored(self):
        file_data = {
            "document": {
                "name": "test",
                "type": "CANVAS",
                "children": [
                    {"name": "grad", "type": "RECTANGLE", "fills": [{"type": "GRADIENT_LINEAR"}], "children": []},
                ],
            }
        }
        tokens = extract_design_tokens(file_data)
        assert tokens["colors"] == {}

    def test_sorts_values(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        assert tokens["border_radius"] == sorted(tokens["border_radius"])
        assert tokens["spacing"] == sorted(tokens["spacing"])


# ---------------------------------------------------------------------------
# generate_token_css
# ---------------------------------------------------------------------------

class TestGenerateTokenCss:
    def test_generates_css(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        css = generate_token_css(tokens)
        assert ":root {" in css
        assert "--color-" in css
        assert "--font-" in css
        assert "--spacing-" in css
        assert "--radius-" in css
        assert css.endswith("}")

    def test_empty_tokens(self):
        css = generate_token_css({"colors": {}, "typography": {}, "spacing": [], "border_radius": []})
        assert css == ":root {\n}"


# ---------------------------------------------------------------------------
# generate_token_tailwind
# ---------------------------------------------------------------------------

class TestGenerateTokenTailwind:
    def test_generates_tailwind_theme(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        tw = generate_token_tailwind(tokens)
        assert "extend" in tw
        assert "colors" in tw["extend"]
        assert "fontFamily" in tw["extend"]
        assert "fontSize" in tw["extend"]
        assert "spacing" in tw["extend"]
        assert "borderRadius" in tw["extend"]

    def test_empty_tokens(self):
        tw = generate_token_tailwind({"colors": {}, "typography": {}, "spacing": [], "border_radius": []})
        assert tw == {"extend": {}}

    def test_colors_match(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        tw = generate_token_tailwind(tokens)
        for name, val in tokens["colors"].items():
            assert tw["extend"]["colors"][name] == val

    def test_typography_line_height_included(self):
        tokens = extract_design_tokens(SAMPLE_FILE)
        heading = tokens["typography"].get("heading-1", {})
        assert "line_height" in heading
