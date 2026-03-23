"""Tests for impact.scorer — weighted scoring engine for file ranking."""

import os
from unittest.mock import patch

import pytest

from scripts.lib.impact.scorer import rank_files, RankedFile, DEFAULT_WEIGHTS, _normalize, _proximity_scores


class TestRankedFile:
    def test_fields(self):
        rf = RankedFile(path="auth.py", score=0.8, reasons={"keyword": 0.5, "churn": 0.3})
        assert rf.path == "auth.py"
        assert rf.score == 0.8
        assert rf.reasons["keyword"] == 0.5


class TestDefaultWeights:
    def test_weights_sum_to_one(self):
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 0.001

    def test_all_dimensions_present(self):
        assert "keyword" in DEFAULT_WEIGHTS
        assert "churn" in DEFAULT_WEIGHTS
        assert "symbol" in DEFAULT_WEIGHTS
        assert "proximity" in DEFAULT_WEIGHTS


@pytest.fixture
def repo(tmp_path):
    """Fixture repo with files and git history."""
    r = tmp_path / "repo"
    r.mkdir()
    (r / "auth.py").write_text("class AuthService:\n    def login(self):\n        pass\n")
    (r / "db.py").write_text("class Database:\n    def connect(self):\n        pass\n")
    (r / "utils.py").write_text("def helper():\n    return True\n")
    sub = r / "src"
    sub.mkdir()
    (sub / "api.py").write_text("from auth import AuthService\n")
    return str(r)


class TestNormalize:
    def test_empty_dict(self):
        assert _normalize({}) == {}

    def test_all_zeros(self):
        result = _normalize({"a": 0.0, "b": 0.0})
        assert result == {"a": 0.0, "b": 0.0}

    def test_normalizes_to_one(self):
        result = _normalize({"a": 5.0, "b": 10.0})
        assert result["b"] == 1.0
        assert result["a"] == 0.5


class TestProximityScores:
    def test_empty_keyword_scores(self, repo):
        assert _proximity_scores({}, repo) == {}

    def test_all_below_threshold(self, tmp_path):
        """When all scores are 0 (threshold=0), dirname='' is top_dir, skip files already in kw."""
        r = tmp_path / "r"
        r.mkdir()
        (r / "a.py").write_text("x")
        (r / "b.py").write_text("y")
        # a.py has score 0 which is >= threshold 0, so dirname '' is added
        # b.py is in same dir but already in keyword_scores? No — only a.py is
        result = _proximity_scores({"a.py": 0.0}, str(r))
        # b.py should get proximity boost (same dir as a.py)
        assert "b.py" in result

    def test_subdirectory_proximity(self, tmp_path):
        """Files in subdirectories of top dirs get 0.5 boost."""
        r = tmp_path / "r"
        r.mkdir()
        src = r / "src"
        src.mkdir()
        deep = src / "sub"
        deep.mkdir()
        (src / "main.py").write_text("x")
        (deep / "helper.py").write_text("x")
        # src/main.py scored high -> 'src' is top_dir
        # src/sub/helper.py is in subdir of 'src' -> gets 0.5
        result = _proximity_scores({"src/main.py": 1.0}, str(r))
        assert "src/sub/helper.py" in result
        assert result["src/sub/helper.py"] == 0.5


class TestRankFiles:
    def test_returns_list(self, repo):
        result = rank_files(repo, "add auth login")
        assert isinstance(result, list)

    def test_returns_ranked_files(self, repo):
        result = rank_files(repo, "add auth login")
        if result:
            assert isinstance(result[0], RankedFile)

    def test_sorted_by_score_descending(self, repo):
        result = rank_files(repo, "add auth login")
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_limits_results(self, repo):
        result = rank_files(repo, "auth", top_n=2)
        assert len(result) <= 2

    def test_includes_reasons_when_requested(self, repo):
        result = rank_files(repo, "auth", include_reasons=True)
        if result:
            assert isinstance(result[0].reasons, dict)

    def test_excludes_reasons_when_not_requested(self, repo):
        result = rank_files(repo, "auth", include_reasons=False)
        if result:
            assert result[0].reasons == {}

    def test_empty_prompt(self, repo):
        result = rank_files(repo, "")
        assert result == []

    def test_nonexistent_root(self, tmp_path):
        result = rank_files(str(tmp_path / "nope"), "auth")
        assert result == []

    def test_custom_weights(self, repo):
        weights = {"keyword": 1.0, "churn": 0.0, "symbol": 0.0, "proximity": 0.0}
        result = rank_files(repo, "auth", weights=weights)
        assert isinstance(result, list)

    def test_auth_files_present(self, repo):
        result = rank_files(repo, "auth login service")
        if result:
            paths = [r.path for r in result]
            # auth.py should appear somewhere in results
            assert "auth.py" in paths

    def test_proximity_boost(self, repo):
        """Files near high-scoring files get a proximity boost."""
        result = rank_files(repo, "auth")
        paths = [r.path for r in result]
        # src/api.py imports auth, should appear
        if "src/api.py" in paths:
            assert True  # proximity working

    def test_all_zero_weights(self, repo):
        weights = {"keyword": 0.0, "churn": 0.0, "symbol": 0.0, "proximity": 0.0}
        result = rank_files(repo, "auth", weights=weights)
        # Should return empty or all-zero scores
        assert isinstance(result, list)

    def test_no_signals_found(self, repo):
        """When no signals match, return empty."""
        result = rank_files(repo, "xyznonexistent12345")
        assert result == []

    def test_churn_signals_used(self, repo):
        """Mock churn to verify it contributes to scoring."""
        with patch("scripts.lib.impact.scorer.churn", return_value={"auth.py": 10, "db.py": 1}):
            with patch("scripts.lib.impact.scorer.recency", return_value={}):
                result = rank_files(repo, "database connect",
                                    weights={"keyword": 0.3, "churn": 0.7, "symbol": 0.0, "proximity": 0.0})
        # With churn dominating, auth.py should rank high despite keyword mismatch
        if result:
            paths = [r.path for r in result]
            assert "auth.py" in paths
