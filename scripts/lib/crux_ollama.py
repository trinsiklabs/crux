"""Lightweight Ollama REST API client using only stdlib."""

from __future__ import annotations

import json
import logging
import warnings
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_ENDPOINT = "http://localhost:11434"

_logger = logging.getLogger(__name__)


def _validate_endpoint(endpoint: str) -> None:
    """Warn if using insecure HTTP on non-localhost endpoints."""
    parsed = urlparse(endpoint)
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        warnings.warn(
            f"Using insecure HTTP for non-localhost endpoint: {endpoint}. "
            "Consider using HTTPS for remote connections.",
            SecurityWarning,
            stacklevel=3,
        )


def check_ollama_running(endpoint: str = DEFAULT_ENDPOINT) -> bool:
    """Return True if the Ollama server is reachable."""
    _validate_endpoint(endpoint)
    try:
        with urlopen(f"{endpoint}/api/tags", timeout=5) as resp:
            return resp.status == 200
    except (URLError, TimeoutError, OSError):
        return False


def list_models(endpoint: str = DEFAULT_ENDPOINT) -> dict:
    """List models available in Ollama."""
    _validate_endpoint(endpoint)
    try:
        with urlopen(f"{endpoint}/api/tags", timeout=10) as resp:
            data = json.loads(resp.read())
            return {"success": True, "models": data.get("models", [])}
    except (URLError, TimeoutError, OSError) as exc:
        _logger.debug("Connection failed during list_models: %s", exc)
        return {"success": False, "error": "Connection failed", "models": []}
    except (json.JSONDecodeError, ValueError) as exc:
        _logger.debug("Invalid response during list_models: %s", exc)
        return {"success": False, "error": "Invalid response from server", "models": []}


def pull_model(name: str, endpoint: str = DEFAULT_ENDPOINT) -> dict:
    """Pull a model from the Ollama registry."""
    if not name:
        return {"success": False, "error": "Model name required"}

    _validate_endpoint(endpoint)
    req = Request(
        f"{endpoint}/api/pull",
        data=json.dumps({"name": name}).encode(),
        headers={"Content-type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read())
            return {"success": True, "model": name, "status": data.get("status", "unknown")}
    except (URLError, TimeoutError, OSError) as exc:
        _logger.debug("Connection failed during pull_model for %s", name)
        return {"success": False, "error": "Connection failed", "model": name}
    except (json.JSONDecodeError, ValueError) as exc:
        _logger.debug("Invalid response during pull_model for %s", name)
        return {"success": False, "error": "Invalid response from server", "model": name}


def generate(
    model: str,
    prompt: str,
    system: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = 120,
) -> dict:
    """Generate a completion from an Ollama model (non-streaming)."""
    if not model:
        return {"success": False, "error": "Model name required"}
    if not prompt:
        return {"success": False, "error": "Prompt required"}

    _validate_endpoint(endpoint)
    payload: dict = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system

    req = Request(
        f"{endpoint}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return {
                "success": True,
                "response": data.get("response", ""),
                "model": data.get("model", model),
                "done": data.get("done", True),
            }
    except (URLError, TimeoutError, OSError) as exc:
        _logger.debug("Connection failed during generate")
        return {"success": False, "error": "Connection failed"}
    except (json.JSONDecodeError, ValueError) as exc:
        _logger.debug("Invalid response during generate")
        return {"success": False, "error": "Invalid response from server"}
