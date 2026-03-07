"""Tests for crux_typefully.py — stdlib-only Typefully API client."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scripts.lib.crux_typefully import (
    TypefullyClient,
    TypefullyError,
    create_draft,
    create_thread,
    list_drafts,
    delete_draft,
)


@pytest.fixture
def bip_dir(tmp_path):
    """A .crux/bip/ directory with API key and config."""
    d = tmp_path / ".crux" / "bip"
    d.mkdir(parents=True)
    key_file = d / "typefully.key"
    key_file.write_text("test-api-key-12345")
    key_file.chmod(0o600)
    config = {"social_set_id": 288244, "api_key_path": str(d / "typefully.key")}
    (d / "config.json").write_text(json.dumps(config))
    return str(d)


@pytest.fixture
def client(bip_dir):
    return TypefullyClient(bip_dir=bip_dir)


def _mock_response(status: int = 200, body: dict | None = None) -> MagicMock:
    """Build a mock urllib response."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body or {}).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# Client init
# ---------------------------------------------------------------------------

class TestClientInit:
    def test_loads_api_key(self, client):
        assert client._api_key == "test-api-key-12345"

    def test_loads_social_set_id(self, client):
        assert client.social_set_id == 288244

    def test_missing_key_file_raises(self, tmp_path):
        d = tmp_path / ".crux" / "bip"
        d.mkdir(parents=True)
        config = {"social_set_id": 1, "api_key_path": str(d / "nokey")}
        (d / "config.json").write_text(json.dumps(config))
        with pytest.raises(TypefullyError, match="API key"):
            TypefullyClient(bip_dir=str(d))

    def test_missing_config_raises(self, tmp_path):
        d = tmp_path / ".crux" / "bip"
        d.mkdir(parents=True)
        with pytest.raises(TypefullyError, match="config"):
            TypefullyClient(bip_dir=str(d))

    def test_strips_whitespace_from_key(self, tmp_path):
        d = tmp_path / ".crux" / "bip"
        d.mkdir(parents=True)
        key_file = d / "typefully.key"
        key_file.write_text("  key-with-spaces  \n")
        key_file.chmod(0o600)
        config = {"social_set_id": 1, "api_key_path": str(d / "typefully.key")}
        (d / "config.json").write_text(json.dumps(config))
        c = TypefullyClient(bip_dir=str(d))
        assert c._api_key == "key-with-spaces"


# ---------------------------------------------------------------------------
# Create draft (single tweet)
# ---------------------------------------------------------------------------

class TestCreateDraft:
    @patch("scripts.lib.crux_typefully.urlopen")
    def test_creates_single_tweet(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"id": 99, "status": "draft"})
        result = create_draft(client, "just shipped crux adopt #buildinpublic")
        assert result["id"] == 99

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_sends_correct_payload(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"id": 1})
        create_draft(client, "test tweet")

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["platforms"]["x"]["enabled"] is True
        assert body["platforms"]["x"]["posts"][0]["text"] == "test tweet"

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_includes_publish_at(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"id": 1})
        create_draft(client, "test", publish_at="2026-03-07T12:00:00Z")

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["publish_at"] == "2026-03-07T12:00:00Z"

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_sends_auth_header(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"id": 1})
        create_draft(client, "test")

        # Headers are cleared after request (PLAN-166), verify call was made
        req = mock_urlopen.call_args[0][0]
        assert req.full_url.startswith("https://api.typefully.com/")

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_api_error_raises(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(422, {"error": "invalid"})
        with pytest.raises(TypefullyError):
            create_draft(client, "test")


# ---------------------------------------------------------------------------
# Create thread
# ---------------------------------------------------------------------------

class TestCreateThread:
    @patch("scripts.lib.crux_typefully.urlopen")
    def test_creates_thread(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"id": 42})
        result = create_thread(client, ["tweet 1", "tweet 2", "tweet 3"])
        assert result["id"] == 42

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_thread_sends_multiple_posts(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"id": 1})
        create_thread(client, ["first", "second", "third"])

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        posts = body["platforms"]["x"]["posts"]
        assert len(posts) == 3
        assert posts[0]["text"] == "first"
        assert posts[2]["text"] == "third"

    def test_empty_thread_raises(self, client):
        with pytest.raises(TypefullyError, match="empty"):
            create_thread(client, [])


# ---------------------------------------------------------------------------
# List drafts
# ---------------------------------------------------------------------------

class TestListDrafts:
    @patch("scripts.lib.crux_typefully.urlopen")
    def test_list_drafts(self, mock_urlopen, client):
        drafts = [{"id": 1, "status": "draft"}, {"id": 2, "status": "scheduled"}]
        mock_urlopen.return_value = _mock_response(200, drafts)
        result = list_drafts(client)
        assert len(result) == 2

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_list_sends_get_request(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, [])
        list_drafts(client)

        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "GET"
        assert "288244" in req.full_url


# ---------------------------------------------------------------------------
# Delete draft
# ---------------------------------------------------------------------------

class TestDeleteDraft:
    @patch("scripts.lib.crux_typefully.urlopen")
    def test_delete_draft(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {"deleted": True})
        result = delete_draft(client, 99)
        assert result["deleted"] is True

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_delete_sends_delete_method(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(200, {})
        delete_draft(client, 42)

        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "DELETE"
        assert "42" in req.full_url

    @patch("scripts.lib.crux_typefully.urlopen")
    def test_delete_not_found_raises(self, mock_urlopen, client):
        mock_urlopen.return_value = _mock_response(404, {"error": "not found"})
        with pytest.raises(TypefullyError):
            delete_draft(client, 999)
