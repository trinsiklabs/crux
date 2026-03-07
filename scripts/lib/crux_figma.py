"""Figma REST API client for importing design data.

Uses only stdlib (urllib.request). Auth via personal access token
passed as parameter - never stored in code.

SECURITY NOTE: The X-Figma-Token header contains sensitive credentials.
Do not log Request objects or enable HTTP debug logging in production.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

FIGMA_API = "https://api.figma.com"

_logger = logging.getLogger(__name__)


def _request(path: str, token: str, timeout: int = 30) -> dict:
    """Make an authenticated GET request to the Figma API."""
    url = f"{FIGMA_API}{path}"
    # SECURITY: Request object contains auth token in headers.
    # Never log or expose Request objects in error messages.
    req = urllib.request.Request(url, headers={
        "X-Figma-Token": token,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"success": True, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        # Log error body for debugging but don't expose to caller
        try:
            body = e.read().decode()
            _logger.debug("Figma API error body: %s", body)
        except Exception:
            pass
        return {"success": False, "error": f"HTTP {e.code}", "status": e.code}
    except urllib.error.URLError as e:
        _logger.debug("Figma API URL error: %s", e.reason)
        return {"success": False, "error": "Connection failed"}
    except Exception as e:
        _logger.exception("Unexpected error during Figma API request")
        return {"success": False, "error": "Request failed"}


def _encode_file_key(file_key: str) -> str:
    """URL-encode a Figma file key for safe path inclusion."""
    return urllib.parse.quote(file_key, safe="")


def get_file(file_key: str, token: str) -> dict:
    """GET /v1/files/:key - returns document structure."""
    return _request(f"/v1/files/{_encode_file_key(file_key)}", token)


def get_file_styles(file_key: str, token: str) -> dict:
    """GET /v1/files/:key/styles - returns design tokens."""
    return _request(f"/v1/files/{_encode_file_key(file_key)}/styles", token)


def get_file_components(file_key: str, token: str) -> dict:
    """GET /v1/files/:key/components - returns component library."""
    return _request(f"/v1/files/{_encode_file_key(file_key)}/components", token)


def get_images(file_key: str, node_ids: list[str], token: str, fmt: str = "png") -> dict:
    """GET /v1/images/:key - exports node renders."""
    # URL-encode each node ID and join with commas
    encoded_ids = ",".join(urllib.parse.quote(nid, safe="") for nid in node_ids)
    encoded_fmt = urllib.parse.quote(fmt, safe="")
    return _request(
        f"/v1/images/{_encode_file_key(file_key)}?ids={encoded_ids}&format={encoded_fmt}",
        token
    )


def _parse_color(color: dict) -> str | None:
    """Convert Figma RGBA dict {r, g, b, a} to hex string."""
    try:
        r = int(color["r"] * 255)
        g = int(color["g"] * 255)
        b = int(color["b"] * 255)
        a = color.get("a", 1.0)
        if a < 1.0:
            return f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
        return f"#{r:02x}{g:02x}{b:02x}"
    except (KeyError, TypeError, ValueError):
        return None


def _walk_nodes(node: dict, visitor: callable) -> None:
    """Recursively walk a Figma document node tree."""
    visitor(node)
    for child in node.get("children", []):
        _walk_nodes(child, visitor)


def extract_design_tokens(file_data: dict) -> dict:
    """Parse Figma file response into structured tokens."""
    tokens: dict = {
        "colors": {},
        "typography": {},
        "spacing": [],
        "border_radius": [],
    }

    doc = file_data.get("document", file_data)

    def visit(node: dict) -> None:
        name = node.get("name", "")
        node_type = node.get("type", "")

        # Extract fill colors
        fills = node.get("fills", [])
        for fill in fills:
            if fill.get("type") == "SOLID" and fill.get("color"):
                hex_color = _parse_color(fill["color"])
                if hex_color and name:
                    safe_name = re.sub(r"[^a-zA-Z0-9-]", "-", name.lower()).strip("-")
                    if safe_name:
                        tokens["colors"][safe_name] = hex_color

        # Extract typography from TEXT nodes
        if node_type == "TEXT":
            style = node.get("style", {})
            if style:
                safe_name = re.sub(r"[^a-zA-Z0-9-]", "-", name.lower()).strip("-")
                if safe_name:
                    entry: dict = {}
                    if "fontFamily" in style:
                        entry["font_family"] = style["fontFamily"]
                    if "fontSize" in style:
                        entry["font_size"] = style["fontSize"]
                    if "fontWeight" in style:
                        entry["font_weight"] = style["fontWeight"]
                    if "lineHeightPx" in style:
                        entry["line_height"] = style["lineHeightPx"]
                    if entry:
                        tokens["typography"][safe_name] = entry

        # Extract corner radius
        corner = node.get("cornerRadius")
        if corner is not None and corner > 0:
            if corner not in tokens["border_radius"]:
                tokens["border_radius"].append(corner)

        # Extract spacing from auto-layout
        spacing = node.get("itemSpacing")
        if spacing is not None and spacing > 0:
            if spacing not in tokens["spacing"]:
                tokens["spacing"].append(spacing)

    _walk_nodes(doc, visit)

    tokens["border_radius"].sort()
    tokens["spacing"].sort()
    return tokens


def generate_token_css(tokens: dict) -> str:
    """Generate CSS custom properties from tokens."""
    lines = [":root {"]

    for name, hex_val in sorted(tokens.get("colors", {}).items()):
        lines.append(f"  --color-{name}: {hex_val};")

    for name, typo in sorted(tokens.get("typography", {}).items()):
        if "font_family" in typo:
            lines.append(f"  --font-{name}: {typo['font_family']};")
        if "font_size" in typo:
            lines.append(f"  --text-{name}-size: {typo['font_size']}px;")
        if "font_weight" in typo:
            lines.append(f"  --text-{name}-weight: {typo['font_weight']};")

    for i, val in enumerate(tokens.get("spacing", [])):
        lines.append(f"  --spacing-{i + 1}: {val}px;")

    for i, val in enumerate(tokens.get("border_radius", [])):
        lines.append(f"  --radius-{i + 1}: {val}px;")

    lines.append("}")
    return "\n".join(lines)


def generate_token_tailwind(tokens: dict) -> dict:
    """Generate Tailwind theme extension from tokens."""
    theme: dict = {"extend": {}}

    if tokens.get("colors"):
        theme["extend"]["colors"] = {}
        for name, hex_val in tokens["colors"].items():
            theme["extend"]["colors"][name] = hex_val

    if tokens.get("typography"):
        font_families: dict[str, list[str]] = {}
        font_sizes: dict[str, str] = {}
        for name, typo in tokens["typography"].items():
            if "font_family" in typo:
                font_families[name] = [typo["font_family"]]
            if "font_size" in typo:
                font_sizes[name] = f"{typo['font_size']}px"
        if font_families:
            theme["extend"]["fontFamily"] = font_families
        if font_sizes:
            theme["extend"]["fontSize"] = font_sizes

    if tokens.get("spacing"):
        theme["extend"]["spacing"] = {}
        for i, val in enumerate(tokens["spacing"]):
            theme["extend"]["spacing"][str(i + 1)] = f"{val}px"

    if tokens.get("border_radius"):
        theme["extend"]["borderRadius"] = {}
        for i, val in enumerate(tokens["border_radius"]):
            theme["extend"]["borderRadius"][str(i + 1)] = f"{val}px"

    return theme
