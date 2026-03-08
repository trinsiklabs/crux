"""Tests for BIP inline review flow."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from scripts.lib.crux_bip_review import (
    get_pending_drafts,
    ReviewResult,
    skip_draft,
)


@pytest.fixture
def bip_dir(tmp_path):
    """Create a BIP directory with test drafts."""
    bip = tmp_path / ".crux" / "bip"
    bip.mkdir(parents=True)
    (bip / "drafts").mkdir()
    return str(bip)


class TestGetPendingDrafts:
    def test_empty_drafts_dir(self, bip_dir):
        drafts = get_pending_drafts(bip_dir)
        assert drafts == []

    def test_returns_drafts(self, bip_dir):
        drafts_dir = os.path.join(bip_dir, "drafts")
        draft = {"content": "test post", "source": "test"}
        with open(os.path.join(drafts_dir, "001.json"), "w") as f:
            json.dump(draft, f)

        drafts = get_pending_drafts(bip_dir)
        assert len(drafts) == 1
        assert drafts[0]["content"] == "test post"
        assert drafts[0]["_id"] == "001"

    def test_skips_invalid_json(self, bip_dir):
        drafts_dir = os.path.join(bip_dir, "drafts")
        with open(os.path.join(drafts_dir, "bad.json"), "w") as f:
            f.write("not json")

        drafts = get_pending_drafts(bip_dir)
        assert drafts == []

    def test_no_drafts_dir(self, tmp_path):
        bip = tmp_path / "no_drafts"
        bip.mkdir()
        drafts = get_pending_drafts(str(bip))
        assert drafts == []


class TestSkipDraft:
    def test_moves_to_skipped(self, bip_dir):
        drafts_dir = os.path.join(bip_dir, "drafts")
        draft_path = os.path.join(drafts_dir, "001.json")
        with open(draft_path, "w") as f:
            json.dump({"content": "test"}, f)

        draft = {"_path": draft_path, "_id": "001"}
        skip_draft(draft, bip_dir)

        assert not os.path.exists(draft_path)
        assert os.path.exists(os.path.join(bip_dir, "skipped", "001.json"))


class TestReviewResult:
    def test_approved_result(self):
        result = ReviewResult(action="approved", draft_id="001", message="ok")
        assert result.action == "approved"
        assert result.draft_id == "001"

    def test_no_drafts_result(self):
        result = ReviewResult(action="no_drafts")
        assert result.action == "no_drafts"
        assert result.draft_id is None
