"""Stdlib-only REST client for the Typefully API.

Manages draft creation, scheduling, listing, and deletion.
Auth via Bearer token stored in `.crux/bip/typefully.key`.
"""

from __future__ import annotations

import json
import logging
import os
import stat
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.typefully.com/v2"
DEFAULT_TIMEOUT = 30

_logger = logging.getLogger(__name__)


class TypefullyError(Exception):
    pass


class TypefullyClient:
    """Configured Typefully API client.

    SECURITY: API key is stored in _api_key. The __repr__ method is
    overridden to prevent accidental exposure in logs or stack traces.
    """

    def __init__(self, bip_dir: str) -> None:
        config_path = os.path.join(bip_dir, "config.json")
        if not os.path.exists(config_path):
            raise TypefullyError(f"BIP config not found: {config_path}")

        with open(config_path) as f:
            config = json.load(f)

        self.social_set_id: int = config.get("social_set_id", 0)
        key_path = config.get("api_key_path", "")

        if not key_path or not os.path.exists(key_path):
            raise TypefullyError(f"API key file not found: {key_path}")

        # SECURITY: Check file permissions - reject if world-readable
        file_stat = os.stat(key_path)
        file_mode = file_stat.st_mode
        if file_mode & stat.S_IROTH:
            raise TypefullyError(
                f"API key file {key_path} is world-readable (mode {oct(file_mode)}). "
                "Fix with: chmod 600 " + key_path
            )

        with open(key_path) as f:
            self._api_key = f.read().strip()

    def __repr__(self) -> str:
        """Sanitized repr to prevent credential exposure in logs."""
        return f"<TypefullyClient social_set_id={self.social_set_id}>"

    def __str__(self) -> str:
        """Sanitized str to prevent credential exposure."""
        return self.__repr__()

    def _validate_path(self, path: str) -> None:
        """Validate API path to prevent injection attacks."""
        if not path.startswith("/"):
            raise TypefullyError("API path must start with /")
        if "//" in path:
            raise TypefullyError("API path cannot contain //")
        # Reject path traversal attempts
        if ".." in path:
            raise TypefullyError("API path cannot contain ..")

    def _url(self, path: str) -> str:
        self._validate_path(path)
        return f"{BASE_URL}/social-sets/{self.social_set_id}{path}"

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        url = self._url(path)
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._api_key}")
        req.add_header("Content-Type", "application/json")

        try:
            with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                if resp.status >= 400:
                    raise TypefullyError(f"Typefully API error: {resp.status}")
                return json.loads(resp.read().decode())
        except HTTPError as e:
            # Log error details but don't expose in exception
            _logger.debug("Typefully API HTTP error: %s", e.code)
            raise TypefullyError(f"Typefully API error: HTTP {e.code}") from None
        except URLError as e:
            _logger.debug("Typefully API connection error: %s", e.reason)
            raise TypefullyError("Typefully API connection failed") from None
        except json.JSONDecodeError as e:
            _logger.debug("Typefully API invalid response")
            raise TypefullyError("Invalid response from Typefully API") from None
        except Exception as e:
            # Catch-all to prevent leaking auth headers in stack traces
            _logger.exception("Unexpected error during Typefully API request")
            raise TypefullyError("Typefully API request failed") from None
        finally:
            # Clear sensitive data from request object
            if hasattr(req, 'headers'):
                req.headers.clear()


def create_draft(
    client: TypefullyClient,
    text: str,
    publish_at: str | None = None,
) -> dict:
    """Create a single-tweet draft."""
    body: dict = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": [{"text": text}],
            }
        }
    }
    if publish_at:
        body["publish_at"] = publish_at
    return client._request("POST", "/drafts", body)


def create_thread(
    client: TypefullyClient,
    posts: list[str],
    publish_at: str | None = None,
) -> dict:
    """Create a multi-tweet thread draft."""
    if not posts:
        raise TypefullyError("Cannot create thread with empty posts list")
    body: dict = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": [{"text": t} for t in posts],
            }
        }
    }
    if publish_at:
        body["publish_at"] = publish_at
    return client._request("POST", "/drafts", body)


def list_drafts(client: TypefullyClient) -> list:
    """List all drafts."""
    return client._request("GET", "/drafts")


def delete_draft(client: TypefullyClient, draft_id: int) -> dict:
    """Delete a draft by ID."""
    return client._request("DELETE", f"/drafts/{draft_id}")
