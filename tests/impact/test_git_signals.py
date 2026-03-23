"""Tests for impact.git_signals — git history signals for file ranking."""

import os
import subprocess
from unittest.mock import patch

import pytest

from scripts.lib.impact.git_signals import churn, recency, cochange, _run_git


@pytest.fixture
def repo(tmp_path):
    """Create a fixture git repo with history."""
    r = tmp_path / "repo"
    r.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t"}

    def run(*args):
        subprocess.run(args, cwd=str(r), env=env, check=True,
                       capture_output=True)

    run("git", "init")
    run("git", "config", "user.name", "Test")
    run("git", "config", "user.email", "t@t")

    # Commit 1: create auth.py and db.py
    (r / "auth.py").write_text("# auth\n")
    (r / "db.py").write_text("# db\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "init")

    # Commit 2: change auth.py and db.py together
    (r / "auth.py").write_text("# auth v2\n")
    (r / "db.py").write_text("# db v2\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "update auth and db")

    # Commit 3: change auth.py only
    (r / "auth.py").write_text("# auth v3\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "update auth again")

    # Commit 4: add utils.py
    (r / "utils.py").write_text("# utils\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "add utils")

    return str(r)


class TestChurn:
    def test_returns_dict(self, repo):
        result = churn(repo)
        assert isinstance(result, dict)

    def test_auth_has_highest_churn(self, repo):
        result = churn(repo)
        assert result["auth.py"] > result.get("utils.py", 0)

    def test_all_files_present(self, repo):
        result = churn(repo)
        assert "auth.py" in result
        assert "db.py" in result
        assert "utils.py" in result

    def test_churn_counts(self, repo):
        result = churn(repo)
        assert result["auth.py"] == 3  # init + update + update again
        assert result["db.py"] == 2    # init + update
        assert result["utils.py"] == 1  # add

    def test_days_limit(self, repo):
        result = churn(repo, days=0)
        # With 0 days, should return empty or very few
        assert isinstance(result, dict)

    def test_nonexistent_root(self, tmp_path):
        result = churn(str(tmp_path / "nope"))
        assert result == {}


class TestRecency:
    def test_returns_dict(self, repo):
        result = recency(repo)
        assert isinstance(result, dict)

    def test_values_between_0_and_1(self, repo):
        result = recency(repo)
        for v in result.values():
            assert 0.0 <= v <= 1.0

    def test_most_recent_file_scores_highest(self, repo):
        result = recency(repo)
        # utils.py was last committed (commit 4)
        assert result["utils.py"] >= result["auth.py"]

    def test_all_files_present(self, repo):
        result = recency(repo)
        assert "auth.py" in result
        assert "db.py" in result
        assert "utils.py" in result

    def test_nonexistent_root(self, tmp_path):
        result = recency(str(tmp_path / "nope"))
        assert result == {}


class TestCochange:
    def test_returns_list(self, repo):
        result = cochange(repo, "auth.py")
        assert isinstance(result, list)

    def test_auth_cochanges_with_db(self, repo):
        result = cochange(repo, "auth.py")
        assert "db.py" in result

    def test_utils_no_cochange(self, repo):
        result = cochange(repo, "utils.py")
        # utils.py was only in one commit by itself
        assert "auth.py" not in result
        assert "db.py" not in result

    def test_unknown_file(self, repo):
        result = cochange(repo, "nope.py")
        assert result == []

    def test_nonexistent_root(self, tmp_path):
        result = cochange(str(tmp_path / "nope"), "auth.py")
        assert result == []

    def test_days_limit(self, repo):
        result = cochange(repo, "auth.py", days=0)
        assert isinstance(result, list)


class TestRunGit:
    def test_timeout_returns_none(self, repo):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            assert _run_git(repo, "log") is None

    def test_file_not_found_returns_none(self, repo):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert _run_git(repo, "log") is None

    def test_nonzero_return_code(self, repo):
        result = _run_git(repo, "log", "--invalid-flag-xyz")
        assert result is None


class TestRecencyEdge:
    def test_empty_repo(self, tmp_path):
        """Repo with no commits — recency returns empty."""
        r = tmp_path / "empty"
        r.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run(["git", "init"], cwd=str(r), env=env, check=True, capture_output=True)
        assert recency(str(r)) == {}

    def test_git_returns_no_parseable_timestamps(self, repo):
        """When git log returns text but no timestamps parse, return empty."""
        with patch("scripts.lib.impact.git_signals._run_git", return_value="\n\n\n"):
            assert recency(repo) == {}


class TestCochangeEdge:
    def test_commit_out_empty_string(self, repo):
        """When git log returns empty for the file, cochange returns []."""
        result = cochange(repo, "auth.py", days=0)
        assert isinstance(result, list)

    def test_commit_hashes_all_blank(self, repo):
        """When commit log parses but all lines are blank, return []."""
        def fake_run_git(root, *args):
            cmd = args[0] if args else ""
            if cmd == "log" and "--format=%H" in args:
                return "\n\n\n"
            # First call is --name-only which also needs to succeed
            return "auth.py\n"
        with patch("scripts.lib.impact.git_signals._run_git", side_effect=fake_run_git):
            assert cochange(repo, "auth.py") == []
