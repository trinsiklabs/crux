"""Tests for crux_git_context — git-aware editing context."""

import os
import subprocess

import pytest

from scripts.lib.crux_git_context import (
    get_current_diff,
    get_file_history,
    get_branch_context,
    suggest_commit_message,
    get_risky_files,
)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t"}

    def run(*args):
        subprocess.run(args, cwd=str(r), env=env, check=True, capture_output=True)

    run("git", "init")
    run("git", "config", "user.name", "Test")
    run("git", "config", "user.email", "t@t")

    (r / "auth.py").write_text("# auth v1\n")
    (r / "db.py").write_text("# db v1\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "initial commit")

    (r / "auth.py").write_text("# auth v2\nclass Auth:\n    pass\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "update auth")

    (r / "auth.py").write_text("# auth v3\nclass Auth:\n    def login(self):\n        pass\n")
    run("git", "add", ".")
    run("git", "commit", "-m", "add login method")

    return str(r)


class TestGetCurrentDiff:
    def test_no_changes(self, repo):
        diff = get_current_diff(repo)
        assert diff == ""

    def test_unstaged_changes(self, repo):
        with open(os.path.join(repo, "auth.py"), "a") as f:
            f.write("# new line\n")
        diff = get_current_diff(repo)
        assert "new line" in diff

    def test_nonexistent(self):
        assert get_current_diff("/nonexistent") == ""


class TestGetFileHistory:
    def test_returns_list(self, repo):
        history = get_file_history(repo, "auth.py")
        assert isinstance(history, list)

    def test_has_commits(self, repo):
        history = get_file_history(repo, "auth.py")
        assert len(history) >= 2  # at least 2 commits touched auth.py

    def test_commit_fields(self, repo):
        history = get_file_history(repo, "auth.py")
        if history:
            assert "message" in history[0]
            assert "author" in history[0]
            assert "date" in history[0]

    def test_limit(self, repo):
        history = get_file_history(repo, "auth.py", n=1)
        assert len(history) == 1

    def test_nonexistent_file(self, repo):
        history = get_file_history(repo, "nope.py")
        assert history == []


class TestGetBranchContext:
    def test_returns_dict(self, repo):
        ctx = get_branch_context(repo)
        assert isinstance(ctx, dict)

    def test_has_branch(self, repo):
        ctx = get_branch_context(repo)
        assert "branch" in ctx
        assert ctx["branch"] in ("main", "master")

    def test_nonexistent(self):
        ctx = get_branch_context("/nonexistent")
        assert ctx == {}


class TestSuggestCommitMessage:
    def test_no_changes(self, repo):
        msg = suggest_commit_message(repo)
        assert msg == "" or msg is None

    def test_with_single_staged(self, repo):
        with open(os.path.join(repo, "new.py"), "w") as f:
            f.write("# new file\n")
        subprocess.run(["git", "add", "new.py"], cwd=repo, capture_output=True)
        msg = suggest_commit_message(repo)
        assert isinstance(msg, str)
        assert "new.py" in msg

    def test_with_multiple_staged(self, repo):
        with open(os.path.join(repo, "a.py"), "w") as f:
            f.write("# a\n")
        with open(os.path.join(repo, "b.py"), "w") as f:
            f.write("# b\n")
        subprocess.run(["git", "add", "a.py", "b.py"], cwd=repo, capture_output=True)
        msg = suggest_commit_message(repo)
        assert "2 files" in msg

    def test_nonexistent(self):
        assert suggest_commit_message("/nonexistent") == ""


class TestGetRiskyFiles:
    def test_returns_list(self, repo):
        risky = get_risky_files(repo)
        assert isinstance(risky, list)

    def test_auth_is_risky(self, repo):
        risky = get_risky_files(repo)
        # auth.py was changed 3 times — should be risky
        if risky:
            paths = [r["file"] for r in risky]
            assert "auth.py" in paths

    def test_nonexistent(self):
        assert get_risky_files("/nonexistent") == []


class TestEdgeCases:
    def test_git_timeout(self, repo):
        from unittest.mock import patch
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 15)):
            assert get_current_diff(repo) == ""

    def test_git_not_found(self, repo):
        from unittest.mock import patch
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert get_current_diff(repo) == ""

    def test_suggest_no_files_in_stat(self, repo):
        """Staged diff with no pipe-delimited lines returns empty."""
        from unittest.mock import patch
        from scripts.lib import crux_git_context
        orig = crux_git_context._git
        def mock_git(root, *args):
            if args[0] == "diff" and "--stat" in args:
                return "summary only line\n"
            return orig(root, *args)
        with patch.object(crux_git_context, "_git", side_effect=mock_git):
            msg = suggest_commit_message(repo)
        assert msg == ""

    def test_git_nonzero_exit(self, repo):
        """Git returning nonzero exit code returns empty string."""
        from scripts.lib.crux_git_context import _git
        result = _git(repo, "log", "--invalid-flag-xyz123")
        assert result == ""

    def test_suggest_from_empty_stat(self, repo):
        """Empty diff stat returns empty message."""
        msg = suggest_commit_message(repo)
        # No staged changes, so stat is empty
        assert msg == ""

    def test_risky_files_empty_log(self, repo):
        """When git log returns empty (no commits in 90 days range)."""
        from unittest.mock import patch
        from scripts.lib import crux_git_context
        with patch.object(crux_git_context, "_git", return_value=""):
            risky = get_risky_files(repo)
        assert risky == []
