"""Tests for crux_bip_analytics.py — BIP engagement tracking."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scripts.lib.crux_bip_analytics import (
    TypefullyStats,
    GitHubStats,
    BlogStats,
    BIPAnalytics,
    fetch_typefully_stats,
    fetch_github_stats,
    fetch_blog_stats,
    load_analytics,
    save_analytics,
    fetch_all_analytics,
    get_analytics_summary,
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


def _mock_response(status: int = 200, body: dict | list | None = None) -> MagicMock:
    """Build a mock urllib response."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body or {}).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class TestDataStructures:
    def test_typefully_stats_defaults(self):
        stats = TypefullyStats()
        assert stats.total_drafts == 0
        assert stats.scheduled_count == 0
        assert stats.published_count == 0
        assert stats.draft_count == 0
        assert stats.last_published_at is None

    def test_github_stats_defaults(self):
        stats = GitHubStats()
        assert stats.stars == 0
        assert stats.forks == 0
        assert stats.watchers == 0
        assert stats.repo_name == ""

    def test_blog_stats_defaults(self):
        stats = BlogStats()
        assert stats.page_views == 0
        assert stats.unique_visitors == 0
        assert stats.top_posts == []

    def test_bip_analytics_defaults(self):
        analytics = BIPAnalytics()
        assert analytics.typefully.total_drafts == 0
        assert analytics.github.stars == 0
        assert analytics.blog.page_views == 0
        assert analytics.last_updated is None


# ---------------------------------------------------------------------------
# Typefully stats
# ---------------------------------------------------------------------------

class TestTypefullyStats:
    @patch("scripts.lib.crux_bip_analytics.list_drafts")
    @patch("scripts.lib.crux_bip_analytics.TypefullyClient")
    def test_fetch_typefully_stats(self, mock_client, mock_list, bip_dir):
        mock_list.return_value = [
            {"id": 1, "status": "draft"},
            {"id": 2, "status": "scheduled"},
            {"id": 3, "status": "published", "published_at": "2026-03-01T12:00:00Z"},
            {"id": 4, "status": "published", "published_at": "2026-03-05T12:00:00Z"},
        ]

        stats = fetch_typefully_stats(bip_dir)

        assert stats.total_drafts == 4
        assert stats.draft_count == 1
        assert stats.scheduled_count == 1
        assert stats.published_count == 2
        assert stats.last_published_at == "2026-03-05T12:00:00Z"
        assert stats.fetched_at is not None

    @patch("scripts.lib.crux_bip_analytics.list_drafts")
    @patch("scripts.lib.crux_bip_analytics.TypefullyClient")
    def test_fetch_typefully_stats_empty(self, mock_client, mock_list, bip_dir):
        mock_list.return_value = []
        stats = fetch_typefully_stats(bip_dir)
        assert stats.total_drafts == 0

    @patch("scripts.lib.crux_bip_analytics.TypefullyClient")
    def test_fetch_typefully_stats_error(self, mock_client, bip_dir):
        from scripts.lib.crux_typefully import TypefullyError
        mock_client.side_effect = TypefullyError("Connection failed")

        stats = fetch_typefully_stats(bip_dir)
        assert stats.total_drafts == 0
        assert stats.fetched_at is not None


# ---------------------------------------------------------------------------
# GitHub stats
# ---------------------------------------------------------------------------

class TestGitHubStats:
    @patch("scripts.lib.crux_bip_analytics.urlopen")
    def test_fetch_github_stats(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(200, {
            "stargazers_count": 1500,
            "forks_count": 200,
            "subscribers_count": 50,
            "open_issues_count": 25,
        })

        stats = fetch_github_stats("owner/repo")

        assert stats.stars == 1500
        assert stats.forks == 200
        assert stats.watchers == 50
        assert stats.open_issues == 25
        assert stats.repo_name == "owner/repo"
        assert stats.fetched_at is not None

    @patch("scripts.lib.crux_bip_analytics.urlopen")
    def test_fetch_github_stats_with_token(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(200, {"stargazers_count": 100})

        stats = fetch_github_stats("owner/repo", token="ghp_token123")
        assert stats.stars == 100

    def test_fetch_github_stats_invalid_repo(self):
        stats = fetch_github_stats("invalid-repo")
        assert stats.stars == 0
        assert stats.repo_name == "invalid-repo"

    def test_fetch_github_stats_empty_repo(self):
        stats = fetch_github_stats("")
        assert stats.stars == 0

    @patch("scripts.lib.crux_bip_analytics.urlopen")
    def test_fetch_github_stats_api_error(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(None, 404, "Not Found", {}, None)

        stats = fetch_github_stats("owner/repo")
        assert stats.stars == 0

    def test_fetch_github_stats_injection_prevention(self):
        # Path traversal attempt
        stats = fetch_github_stats("../../../etc/passwd")
        assert stats.stars == 0

        # Special characters
        stats = fetch_github_stats("owner/repo;rm -rf /")
        assert stats.stars == 0


# ---------------------------------------------------------------------------
# Blog stats
# ---------------------------------------------------------------------------

class TestBlogStats:
    def test_fetch_blog_stats_placeholder(self):
        stats = fetch_blog_stats()
        assert stats.page_views == 0
        assert stats.unique_visitors == 0
        assert stats.fetched_at is not None

    def test_fetch_blog_stats_with_url(self):
        stats = fetch_blog_stats(blog_url="https://blog.example.com")
        assert stats.page_views == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load_analytics(self, bip_dir):
        analytics = BIPAnalytics(
            typefully=TypefullyStats(total_drafts=10, published_count=5),
            github=GitHubStats(stars=100, forks=20, repo_name="owner/repo"),
            blog=BlogStats(page_views=1000),
            last_updated="2026-03-08T12:00:00Z",
        )

        save_analytics(analytics, bip_dir)
        loaded = load_analytics(bip_dir)

        assert loaded.typefully.total_drafts == 10
        assert loaded.typefully.published_count == 5
        assert loaded.github.stars == 100
        assert loaded.github.forks == 20
        assert loaded.github.repo_name == "owner/repo"
        assert loaded.blog.page_views == 1000
        assert loaded.last_updated == "2026-03-08T12:00:00Z"

    def test_load_missing_analytics(self, bip_dir):
        analytics = load_analytics(bip_dir)
        assert analytics.typefully.total_drafts == 0
        assert analytics.github.stars == 0

    def test_load_corrupt_analytics(self, bip_dir):
        Path(bip_dir, "analytics.json").write_text("not valid json{{{")
        analytics = load_analytics(bip_dir)
        assert analytics.typefully.total_drafts == 0

    def test_analytics_file_location(self, bip_dir):
        analytics = BIPAnalytics(last_updated="2026-03-08T12:00:00Z")
        save_analytics(analytics, bip_dir)

        assert os.path.exists(os.path.join(bip_dir, "analytics.json"))


# ---------------------------------------------------------------------------
# Full fetch
# ---------------------------------------------------------------------------

class TestFetchAllAnalytics:
    @patch("scripts.lib.crux_bip_analytics.fetch_github_stats")
    @patch("scripts.lib.crux_bip_analytics.fetch_typefully_stats")
    def test_fetch_all_analytics(self, mock_tf, mock_gh, bip_dir):
        mock_tf.return_value = TypefullyStats(total_drafts=5, published_count=3)
        mock_gh.return_value = GitHubStats(stars=100, repo_name="owner/repo")

        analytics = fetch_all_analytics(
            bip_dir=bip_dir,
            github_repo="owner/repo",
        )

        assert analytics.typefully.total_drafts == 5
        assert analytics.github.stars == 100
        assert analytics.last_updated is not None

        # Check it was persisted
        loaded = load_analytics(bip_dir)
        assert loaded.typefully.total_drafts == 5

    @patch("scripts.lib.crux_bip_analytics.fetch_typefully_stats")
    def test_fetch_all_without_github(self, mock_tf, bip_dir):
        mock_tf.return_value = TypefullyStats(total_drafts=2)

        analytics = fetch_all_analytics(bip_dir=bip_dir)

        assert analytics.typefully.total_drafts == 2
        assert analytics.github.stars == 0
        assert analytics.github.repo_name == ""


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestGetAnalyticsSummary:
    def test_get_analytics_summary(self, bip_dir):
        analytics = BIPAnalytics(
            typefully=TypefullyStats(
                total_drafts=10,
                scheduled_count=2,
                published_count=5,
                draft_count=3,
                last_published_at="2026-03-07T12:00:00Z",
            ),
            github=GitHubStats(
                stars=500,
                forks=50,
                watchers=30,
                open_issues=10,
                repo_name="owner/repo",
            ),
            blog=BlogStats(
                page_views=5000,
                unique_visitors=1000,
                top_posts=[{"title": "Post 1"}],
            ),
            last_updated="2026-03-08T12:00:00Z",
        )
        save_analytics(analytics, bip_dir)

        summary = get_analytics_summary(bip_dir)

        assert summary["last_updated"] == "2026-03-08T12:00:00Z"
        assert summary["typefully"]["total_drafts"] == 10
        assert summary["typefully"]["scheduled"] == 2
        assert summary["typefully"]["published"] == 5
        assert summary["typefully"]["drafts"] == 3
        assert summary["github"]["stars"] == 500
        assert summary["github"]["forks"] == 50
        assert summary["github"]["repo"] == "owner/repo"
        assert summary["blog"]["page_views"] == 5000
        assert summary["blog"]["top_posts_count"] == 1

    def test_get_analytics_summary_empty(self, bip_dir):
        summary = get_analytics_summary(bip_dir)
        assert summary["typefully"]["total_drafts"] == 0
        assert summary["github"]["stars"] == 0


# ---------------------------------------------------------------------------
# MCP Handler integration
# ---------------------------------------------------------------------------

class TestMCPHandler:
    @patch("scripts.lib.crux_bip_analytics.fetch_all_analytics")
    def test_handle_bip_get_analytics_cached(self, mock_fetch, tmp_path):
        from scripts.lib.crux_mcp_handlers import handle_bip_get_analytics

        # Set up project directory structure
        project_dir = str(tmp_path)
        crux_bip_dir = tmp_path / ".crux" / "bip"
        crux_bip_dir.mkdir(parents=True)

        # Save some analytics
        analytics = BIPAnalytics(
            typefully=TypefullyStats(total_drafts=5),
            last_updated="2026-03-08T10:00:00Z",
        )
        save_analytics(analytics, str(crux_bip_dir))

        result = handle_bip_get_analytics(project_dir=project_dir, refresh=False)

        assert result["status"] == "ok"
        assert result["typefully"]["total_drafts"] == 5
        mock_fetch.assert_not_called()

    @patch("scripts.lib.crux_bip_analytics.fetch_all_analytics")
    def test_handle_bip_get_analytics_refresh(self, mock_fetch, tmp_path):
        from scripts.lib.crux_mcp_handlers import handle_bip_get_analytics

        project_dir = str(tmp_path)
        crux_bip_dir = tmp_path / ".crux" / "bip"
        crux_bip_dir.mkdir(parents=True)

        # Mock the fetch to save analytics
        def mock_fetch_impl(**kwargs):
            analytics = BIPAnalytics(
                typefully=TypefullyStats(total_drafts=10),
                last_updated="2026-03-08T12:00:00Z",
            )
            save_analytics(analytics, str(crux_bip_dir))
            return analytics

        mock_fetch.side_effect = mock_fetch_impl

        result = handle_bip_get_analytics(
            project_dir=project_dir,
            github_repo="owner/repo",
            refresh=True,
        )

        assert result["status"] == "ok"
        mock_fetch.assert_called_once()
