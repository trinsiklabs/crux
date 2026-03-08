"""BIP analytics: engagement tracking from Typefully, blog traffic, GitHub stats.

Fetches and aggregates engagement data from multiple sources:
- Typefully API: draft counts, scheduled posts, published performance
- GitHub API: star/fork counts for the repository
- Blog traffic: placeholder for future analytics integration

Analytics are stored in .crux/bip/analytics.json for historical tracking.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.lib.crux_typefully import TypefullyClient, TypefullyError, list_drafts


_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
GITHUB_API_BASE = "https://api.github.com"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TypefullyStats:
    """Engagement stats from Typefully."""
    total_drafts: int = 0
    scheduled_count: int = 0
    published_count: int = 0
    draft_count: int = 0
    last_published_at: str | None = None
    fetched_at: str | None = None


@dataclass
class GitHubStats:
    """Repository stats from GitHub."""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    repo_name: str = ""
    fetched_at: str | None = None


@dataclass
class BlogStats:
    """Blog traffic stats (placeholder for future integration)."""
    page_views: int = 0
    unique_visitors: int = 0
    top_posts: list[dict] = field(default_factory=list)
    fetched_at: str | None = None


@dataclass
class BIPAnalytics:
    """Combined BIP analytics from all sources."""
    typefully: TypefullyStats = field(default_factory=TypefullyStats)
    github: GitHubStats = field(default_factory=GitHubStats)
    blog: BlogStats = field(default_factory=BlogStats)
    last_updated: str | None = None


# ---------------------------------------------------------------------------
# Typefully analytics
# ---------------------------------------------------------------------------

def fetch_typefully_stats(bip_dir: str) -> TypefullyStats:
    """Fetch engagement stats from Typefully API.

    Returns draft counts categorized by status (draft, scheduled, published).
    """
    now = datetime.now(timezone.utc).isoformat()
    stats = TypefullyStats(fetched_at=now)

    try:
        client = TypefullyClient(bip_dir=bip_dir)
        drafts = list_drafts(client)

        if not isinstance(drafts, list):
            _logger.warning("Unexpected Typefully response format")
            return stats

        stats.total_drafts = len(drafts)

        for draft in drafts:
            status = draft.get("status", "").lower()
            if status == "scheduled":
                stats.scheduled_count += 1
            elif status == "published":
                stats.published_count += 1
                # Track most recent publish time
                published_at = draft.get("published_at")
                if published_at:
                    if not stats.last_published_at or published_at > stats.last_published_at:
                        stats.last_published_at = published_at
            else:
                stats.draft_count += 1

    except TypefullyError as e:
        _logger.warning(f"Failed to fetch Typefully stats: {e}")
    except Exception as e:
        _logger.exception("Unexpected error fetching Typefully stats")

    return stats


# ---------------------------------------------------------------------------
# GitHub analytics
# ---------------------------------------------------------------------------

def fetch_github_stats(repo: str, token: str | None = None) -> GitHubStats:
    """Fetch repository stats from GitHub API.

    Args:
        repo: Repository in "owner/repo" format (e.g., "anthropics/claude-code").
        token: Optional GitHub personal access token for higher rate limits.

    Returns:
        GitHubStats with star/fork/watcher counts.
    """
    now = datetime.now(timezone.utc).isoformat()
    stats = GitHubStats(repo_name=repo, fetched_at=now)

    if not repo or "/" not in repo:
        _logger.warning(f"Invalid repo format: {repo}")
        return stats

    # Validate repo format to prevent injection
    parts = repo.split("/")
    if len(parts) != 2 or not all(p.replace("-", "").replace("_", "").isalnum() for p in parts):
        _logger.warning(f"Invalid repo format: {repo}")
        return stats

    url = f"{GITHUB_API_BASE}/repos/{repo}"

    try:
        req = Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "Crux-BIP-Analytics")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            if resp.status >= 400:
                _logger.warning(f"GitHub API error: {resp.status}")
                return stats
            data = json.loads(resp.read().decode())

        stats.stars = data.get("stargazers_count", 0)
        stats.forks = data.get("forks_count", 0)
        stats.watchers = data.get("subscribers_count", 0)  # True watchers, not stars
        stats.open_issues = data.get("open_issues_count", 0)

    except HTTPError as e:
        _logger.warning(f"GitHub API HTTP error: {e.code}")
    except URLError as e:
        _logger.warning(f"GitHub API connection error: {e.reason}")
    except json.JSONDecodeError:
        _logger.warning("Invalid JSON response from GitHub API")
    except Exception as e:
        _logger.exception("Unexpected error fetching GitHub stats")
    finally:
        # Clear sensitive headers
        if hasattr(req, 'headers'):
            req.headers.clear()

    return stats


# ---------------------------------------------------------------------------
# Blog analytics (placeholder)
# ---------------------------------------------------------------------------

def fetch_blog_stats(blog_url: str | None = None) -> BlogStats:
    """Fetch blog traffic stats.

    Currently a placeholder - returns empty stats.
    Future implementation could integrate with:
    - Plausible Analytics API
    - Google Analytics API
    - Self-hosted analytics

    Args:
        blog_url: Base URL of the blog (for API discovery).

    Returns:
        BlogStats (currently empty placeholder).
    """
    now = datetime.now(timezone.utc).isoformat()
    return BlogStats(fetched_at=now)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_analytics(bip_dir: str) -> BIPAnalytics:
    """Load stored analytics from disk."""
    path = os.path.join(bip_dir, "analytics.json")
    if not os.path.exists(path):
        return BIPAnalytics()

    try:
        with open(path) as f:
            data = json.load(f)

        analytics = BIPAnalytics()
        analytics.last_updated = data.get("last_updated")

        if "typefully" in data:
            tf = data["typefully"]
            analytics.typefully = TypefullyStats(**{
                k: v for k, v in tf.items()
                if k in TypefullyStats.__dataclass_fields__
            })

        if "github" in data:
            gh = data["github"]
            analytics.github = GitHubStats(**{
                k: v for k, v in gh.items()
                if k in GitHubStats.__dataclass_fields__
            })

        if "blog" in data:
            bl = data["blog"]
            analytics.blog = BlogStats(**{
                k: v for k, v in bl.items()
                if k in BlogStats.__dataclass_fields__
            })

        return analytics

    except (json.JSONDecodeError, OSError, TypeError) as e:
        _logger.warning(f"Failed to load analytics: {e}")
        return BIPAnalytics()


def save_analytics(analytics: BIPAnalytics, bip_dir: str) -> None:
    """Save analytics to disk."""
    os.makedirs(bip_dir, exist_ok=True)
    path = os.path.join(bip_dir, "analytics.json")

    data = {
        "typefully": asdict(analytics.typefully),
        "github": asdict(analytics.github),
        "blog": asdict(analytics.blog),
        "last_updated": analytics.last_updated,
    }

    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        _logger.error(f"Failed to save analytics: {e}")


# ---------------------------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------------------------

def fetch_all_analytics(
    bip_dir: str,
    github_repo: str | None = None,
    github_token: str | None = None,
    blog_url: str | None = None,
) -> BIPAnalytics:
    """Fetch analytics from all configured sources.

    Args:
        bip_dir: Path to .crux/bip directory.
        github_repo: Optional repo in "owner/repo" format.
        github_token: Optional GitHub token for higher rate limits.
        blog_url: Optional blog URL for traffic stats.

    Returns:
        BIPAnalytics with data from all sources.
    """
    now = datetime.now(timezone.utc).isoformat()

    analytics = BIPAnalytics(
        typefully=fetch_typefully_stats(bip_dir),
        github=fetch_github_stats(github_repo, github_token) if github_repo else GitHubStats(),
        blog=fetch_blog_stats(blog_url) if blog_url else BlogStats(),
        last_updated=now,
    )

    # Persist for historical tracking
    save_analytics(analytics, bip_dir)

    return analytics


def get_analytics_summary(bip_dir: str) -> dict:
    """Get a summary of current analytics for MCP tool response.

    Loads stored analytics and returns a formatted summary.
    """
    analytics = load_analytics(bip_dir)

    return {
        "last_updated": analytics.last_updated,
        "typefully": {
            "total_drafts": analytics.typefully.total_drafts,
            "scheduled": analytics.typefully.scheduled_count,
            "published": analytics.typefully.published_count,
            "drafts": analytics.typefully.draft_count,
            "last_published_at": analytics.typefully.last_published_at,
        },
        "github": {
            "repo": analytics.github.repo_name,
            "stars": analytics.github.stars,
            "forks": analytics.github.forks,
            "watchers": analytics.github.watchers,
            "open_issues": analytics.github.open_issues,
        },
        "blog": {
            "page_views": analytics.blog.page_views,
            "unique_visitors": analytics.blog.unique_visitors,
            "top_posts_count": len(analytics.blog.top_posts),
        },
    }
