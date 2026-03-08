"""Tests for BIP coordinated publish workflow."""

import os
import json

import pytest

from scripts.lib.crux_bip_publish import (
    generate_blog_post,
    _slugify,
    PublishResult,
)


@pytest.fixture
def site_dir(tmp_path):
    """Create a site directory structure."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "src" / "blog").mkdir(parents=True)
    return str(site)


class TestSlugify:
    def test_basic_slug(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("Fix bug: crash!") == "fix-bug-crash"

    def test_multiple_spaces(self):
        assert _slugify("too   many   spaces") == "too-many-spaces"

    def test_leading_trailing(self):
        assert _slugify("  trimmed  ") == "trimmed"


class TestGenerateBlogPost:
    def test_creates_post_directory(self, site_dir):
        path = generate_blog_post(
            plan_id="PLAN-100",
            plan_title="Test Feature",
            summary="This is a test.",
            site_dir=site_dir,
        )
        assert path is not None
        assert os.path.exists(path)
        assert "plan-100" in path.lower()

    def test_post_contains_frontmatter(self, site_dir):
        path = generate_blog_post(
            plan_id="PLAN-100",
            plan_title="Test Feature",
            summary="This is a test.",
            site_dir=site_dir,
        )
        with open(path) as f:
            content = f.read()
        assert "layout: post.njk" in content
        assert "title:" in content
        assert "date:" in content

    def test_post_contains_summary(self, site_dir):
        path = generate_blog_post(
            plan_id="PLAN-100",
            plan_title="Test Feature",
            summary="Custom summary here.",
            site_dir=site_dir,
        )
        with open(path) as f:
            content = f.read()
        assert "Custom summary here." in content


class TestPublishResult:
    def test_success_result(self):
        result = PublishResult(
            success=True,
            blog_path="/path/to/post",
            site_deployed=True,
        )
        assert result.success
        assert result.blog_path == "/path/to/post"
        assert result.errors == []

    def test_failure_result(self):
        result = PublishResult(
            success=False,
            errors=["Something went wrong"],
        )
        assert not result.success
        assert "Something went wrong" in result.errors
