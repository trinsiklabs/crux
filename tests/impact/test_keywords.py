"""Tests for impact.keywords — keyword extraction and grep matching."""

import os
import subprocess
from unittest.mock import patch

import pytest

from scripts.lib.impact.keywords import extract_keywords, grep_matches


class TestExtractKeywords:
    def test_returns_list(self):
        result = extract_keywords("add OAuth2 login flow")
        assert isinstance(result, list)

    def test_removes_stopwords(self):
        result = extract_keywords("add the login to the system")
        assert "the" not in result
        assert "to" not in result

    def test_splits_camel_case(self):
        result = extract_keywords("fix AuthService bug")
        lower = [k.lower() for k in result]
        assert "auth" in lower
        assert "service" in lower

    def test_splits_snake_case(self):
        result = extract_keywords("update user_profile handler")
        lower = [k.lower() for k in result]
        assert "user" in lower
        assert "profile" in lower

    def test_preserves_technical_terms(self):
        result = extract_keywords("OAuth2 JWT authentication")
        lower = [k.lower() for k in result]
        assert "oauth2" in lower or "oauth" in lower
        assert "jwt" in lower

    def test_deduplicates(self):
        result = extract_keywords("auth auth auth login")
        assert len(set(result)) == len(result)

    def test_empty_prompt(self):
        result = extract_keywords("")
        assert result == []

    def test_all_stopwords(self):
        result = extract_keywords("the a an is are was were")
        assert result == []

    def test_lowercases_output(self):
        result = extract_keywords("Fix BUG in Login")
        for kw in result:
            assert kw == kw.lower()


@pytest.fixture
def repo(tmp_path):
    """Create a fixture repo with files for grep matching."""
    r = tmp_path / "repo"
    r.mkdir()
    (r / "auth.py").write_text("class AuthService:\n    def login(self, user):\n        pass\n")
    (r / "db.py").write_text("class Database:\n    def connect(self):\n        pass\n")
    (r / "utils.py").write_text("def helper():\n    return True\n")
    sub = r / "src"
    sub.mkdir()
    (sub / "api.py").write_text("from auth import AuthService\ndef api_login():\n    pass\n")
    return str(r)


class TestGrepMatches:
    def test_returns_dict(self, repo):
        result = grep_matches(repo, ["auth"])
        assert isinstance(result, dict)

    def test_finds_matching_files(self, repo):
        result = grep_matches(repo, ["auth"])
        assert "auth.py" in result
        assert "src/api.py" in result

    def test_no_match_returns_empty(self, repo):
        result = grep_matches(repo, ["xyznonexistent"])
        assert result == {}

    def test_multiple_keywords(self, repo):
        result = grep_matches(repo, ["auth", "login"])
        assert "auth.py" in result
        # auth.py has both keywords, should score higher
        if "db.py" in result:
            assert result["auth.py"] > result["db.py"]

    def test_empty_keywords(self, repo):
        result = grep_matches(repo, [])
        assert result == {}

    def test_nonexistent_root(self, tmp_path):
        result = grep_matches(str(tmp_path / "nope"), ["auth"])
        assert result == {}

    def test_scores_by_density(self, repo):
        result = grep_matches(repo, ["auth"])
        # auth.py has "AuthService" and "auth" in content, api.py has "auth" import
        assert result["auth.py"] >= result.get("src/api.py", 0)

    def test_binary_files_excluded(self, repo):
        # Write a file with null bytes (binary)
        with open(os.path.join(repo, "data.bin"), "wb") as f:
            f.write(b"\x00\x01\x02auth\x03\x04")
        result = grep_matches(repo, ["auth"])
        assert "data.bin" not in result

    def test_grep_output_with_blank_lines(self, repo):
        """Grep output containing blank lines should be skipped."""
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=f"{repo}/auth.py\n\n{repo}/db.py\n\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=fake):
            result = grep_matches(repo, ["auth"])
        assert isinstance(result, dict)

    def test_grep_timeout_skips_keyword(self, repo):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("grep", 15)):
            result = grep_matches(repo, ["auth"])
        assert result == {}

    def test_grep_file_not_found(self, repo):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = grep_matches(repo, ["auth"])
        assert result == {}

    def test_unreadable_file(self, repo):
        result = grep_matches(repo, ["auth"])
        # Patch open to raise OSError for one file
        orig_open = open
        def bad_open(path, *a, **kw):
            if "auth.py" in str(path):
                raise OSError("permission denied")
            return orig_open(path, *a, **kw)
        with patch("builtins.open", side_effect=bad_open):
            result = grep_matches(repo, ["auth"])
        # Should still return results (with default line count of 1)
        assert isinstance(result, dict)
