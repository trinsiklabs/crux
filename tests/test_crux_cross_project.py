"""Tests for crux_cross_project.py — cross-project aggregation."""

import json
import os

import pytest

from scripts.lib.crux_init import init_project, init_user
from scripts.lib.crux_session import SessionState, save_session
from scripts.lib.crux_cross_project import (
    discover_projects,
    register_project,
    unregister_project,
    aggregate_digests,
    aggregate_corrections,
    generate_user_digest,
)


@pytest.fixture
def env(tmp_path):
    """Multi-project environment with shared home."""
    home = tmp_path / "home"
    home.mkdir()
    init_user(home=str(home))

    projects = {}
    for name in ["alpha", "beta", "gamma"]:
        p = home / "projects" / name
        p.mkdir(parents=True)
        init_project(project_dir=str(p))
        projects[name] = str(p)

    return {"home": str(home), "projects": projects, "tmp": str(tmp_path)}


def _write_interactions(project_dir, count, date_str="2026-03-06"):
    log_dir = os.path.join(project_dir, ".crux", "analytics", "interactions")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, f"{date_str}.jsonl"), "w") as f:
        for i in range(count):
            f.write(json.dumps({
                "timestamp": f"{date_str}T01:00:00Z",
                "tool_name": "Bash", "tool_input": {},
            }) + "\n")


def _write_corrections(project_dir, count, category="style"):
    corr_dir = os.path.join(project_dir, ".crux", "corrections")
    os.makedirs(corr_dir, exist_ok=True)
    with open(os.path.join(corr_dir, "corrections.jsonl"), "a") as f:
        for i in range(count):
            f.write(json.dumps({
                "original": f"bad{i}", "corrected": f"good{i}",
                "category": category, "mode": "build-py",
                "timestamp": "2026-03-06T01:00:00Z",
            }) + "\n")


def _set_mode(project_dir, mode):
    state = SessionState(active_mode=mode, active_tool="claude-code")
    save_session(state, project_crux_dir=os.path.join(project_dir, ".crux"))


# ---------------------------------------------------------------------------
# discover_projects
# ---------------------------------------------------------------------------

class TestDiscoverProjects:
    def test_finds_projects_in_home(self, env):
        # Projects are siblings of home in tmp_path, not children of home
        # Register them first
        for p in env["projects"].values():
            register_project(p, env["home"])

        result = discover_projects(env["home"])
        assert len(result) >= 3

    def test_finds_projects_via_registry(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        result = discover_projects(env["home"])
        assert env["projects"]["alpha"] in result

    def test_empty_when_no_projects(self, tmp_path):
        home = tmp_path / "empty-home"
        home.mkdir()
        init_user(home=str(home))
        result = discover_projects(str(home))
        assert result == []

    def test_deduplicates_results(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        register_project(env["projects"]["alpha"], env["home"])  # duplicate add
        result = discover_projects(env["home"])
        assert result.count(env["projects"]["alpha"]) == 1

    def test_skips_removed_projects(self, env):
        fake_path = "/tmp/nonexistent-project-abc123"
        projects = [fake_path]
        registry_path = os.path.join(env["home"], ".crux", "projects.json")
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, "w") as f:
            json.dump({"projects": projects}, f)
        result = discover_projects(env["home"])
        assert fake_path not in result


# ---------------------------------------------------------------------------
# register_project / unregister_project
# ---------------------------------------------------------------------------

class TestRegisterProject:
    def test_register_new_project(self, env):
        result = register_project(env["projects"]["alpha"], env["home"])
        assert result["registered"] is True
        assert result["total_projects"] == 1

    def test_register_duplicate_returns_false(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        result = register_project(env["projects"]["alpha"], env["home"])
        assert result["registered"] is False
        assert "already" in result["reason"]

    def test_unregister_existing(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        result = unregister_project(env["projects"]["alpha"], env["home"])
        assert result["unregistered"] is True

    def test_unregister_nonexistent(self, env):
        result = unregister_project("/nonexistent", env["home"])
        assert result["unregistered"] is False


# ---------------------------------------------------------------------------
# aggregate_digests
# ---------------------------------------------------------------------------

class TestAggregateDigests:
    def test_aggregates_interactions_across_projects(self, env):
        for name, path in env["projects"].items():
            register_project(path, env["home"])
            _write_interactions(path, 10)

        result = aggregate_digests(env["home"], date_str="2026-03-06")
        assert result["total_projects"] >= 3
        assert result["total_interactions"] >= 30

    def test_aggregates_corrections(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])
            _write_corrections(path, 5)

        result = aggregate_digests(env["home"])
        assert result["total_corrections"] >= 15

    def test_collects_modes_used(self, env):
        for name, path in env["projects"].items():
            register_project(path, env["home"])
            _set_mode(path, "build-py" if name != "gamma" else "debug")

        result = aggregate_digests(env["home"])
        assert "build-py" in result["modes_used"]
        assert "debug" in result["modes_used"]

    def test_empty_projects(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])

        result = aggregate_digests(env["home"])
        assert result["total_interactions"] == 0
        assert result["total_corrections"] == 0

    def test_per_project_breakdown(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        _write_interactions(env["projects"]["alpha"], 5)

        result = aggregate_digests(env["home"], date_str="2026-03-06")
        assert len(result["projects"]) >= 1
        alpha_summary = next(p for p in result["projects"] if p["project"] == env["projects"]["alpha"])
        assert alpha_summary["interactions"] == 5


# ---------------------------------------------------------------------------
# aggregate_corrections
# ---------------------------------------------------------------------------

class TestAggregateCorrections:
    def test_detects_cross_project_patterns(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])
            _write_corrections(path, 3, category="style")

        result = aggregate_corrections(env["home"])
        assert len(result["cross_project_patterns"]) >= 1
        style_pattern = next(p for p in result["patterns"] if p["category"] == "style")
        assert style_pattern["cross_project"] is True
        assert style_pattern["project_count"] >= 3

    def test_single_project_not_cross_project(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        _write_corrections(env["projects"]["alpha"], 3, category="logic")

        result = aggregate_corrections(env["home"])
        logic = next(p for p in result["patterns"] if p["category"] == "logic")
        assert logic["cross_project"] is False

    def test_no_corrections_returns_empty(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])

        result = aggregate_corrections(env["home"])
        assert result["patterns"] == []
        assert result["cross_project_patterns"] == []

    def test_multiple_categories(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])
        _write_corrections(env["projects"]["alpha"], 2, category="style")
        _write_corrections(env["projects"]["beta"], 3, category="logic")
        _write_corrections(env["projects"]["gamma"], 1, category="style")

        result = aggregate_corrections(env["home"])
        cats = {p["category"] for p in result["patterns"]}
        assert "style" in cats
        assert "logic" in cats

    def test_handles_malformed_corrections(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        corr_dir = os.path.join(env["projects"]["alpha"], ".crux", "corrections")
        os.makedirs(corr_dir, exist_ok=True)
        with open(os.path.join(corr_dir, "corrections.jsonl"), "w") as f:
            f.write("not json\n")
            f.write(json.dumps({"category": "style"}) + "\n")

        result = aggregate_corrections(env["home"])
        assert len(result["patterns"]) == 1


# ---------------------------------------------------------------------------
# generate_user_digest
# ---------------------------------------------------------------------------

class TestGenerateUserDigest:
    def test_generates_digest_file(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])
            _write_interactions(path, 5)
            _write_corrections(path, 2, category="style")
            _set_mode(path, "build-py")

        result = generate_user_digest(env["home"], date_str="2026-03-06")
        assert os.path.exists(result["output_path"])
        assert "2026-03-06" in result["date"]
        assert "User Digest" in result["content"]

    def test_digest_includes_cross_project_patterns(self, env):
        for path in env["projects"].values():
            register_project(path, env["home"])
            _write_corrections(path, 3, category="style")

        result = generate_user_digest(env["home"])
        assert "Cross-Project" in result["content"]
        assert "style" in result["content"]

    def test_digest_includes_per_project_breakdown(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        _write_interactions(env["projects"]["alpha"], 10)
        _set_mode(env["projects"]["alpha"], "debug")

        result = generate_user_digest(env["home"], date_str="2026-03-06")
        assert "alpha" in result["content"]
        assert "debug" in result["content"]

    def test_empty_digest_when_no_data(self, tmp_path):
        """Projects exist but have no analytics data."""
        home = tmp_path / "empty_home"
        home.mkdir()
        init_user(home=str(home))
        result = generate_user_digest(str(home))
        assert result["digest"]["total_projects"] == 0
        assert result["digest"]["total_interactions"] == 0

    def test_returns_digest_and_correction_data(self, env):
        result = generate_user_digest(env["home"])
        assert "digest" in result
        assert "corrections" in result
        assert "content" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_corrupt_registry_handled(self, env):
        registry_path = os.path.join(env["home"], ".crux", "projects.json")
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, "w") as f:
            f.write("not json")
        result = discover_projects(env["home"])
        assert isinstance(result, list)

    def test_permission_error_handled(self, env, monkeypatch):
        import scripts.lib.crux_cross_project as cp
        original_listdir = os.listdir

        def mock_listdir(path):
            if "personal" in path or path == env["home"]:
                raise PermissionError("no access")
            return original_listdir(path)

        monkeypatch.setattr(os, "listdir", mock_listdir)
        result = discover_projects(env["home"])
        assert isinstance(result, list)

    def test_discovers_projects_in_home_subdir(self, env):
        """Projects in ~/projects/ should be found."""
        projects_dir = os.path.join(env["home"], "projects")
        os.makedirs(projects_dir, exist_ok=True)
        proj = os.path.join(projects_dir, "myproject")
        os.makedirs(proj)
        init_project(project_dir=proj)

        result = discover_projects(env["home"])
        assert proj in result

    def test_missing_session_state(self, env):
        register_project(env["projects"]["alpha"], env["home"])
        # Don't set any mode — session state file may not exist
        result = aggregate_digests(env["home"])
        alpha = next(p for p in result["projects"] if p["project"] == env["projects"]["alpha"])
        # active_mode should be the default or None
        assert isinstance(alpha["active_mode"], (str, type(None)))
