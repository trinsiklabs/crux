"""Tests for crux_memory — cross-session fact persistence."""

import json
import os

import pytest

from scripts.lib.crux_memory import (
    MemoryEntry,
    save_memory,
    load_memories,
    search_memories,
    forget_memory,
    remember,
    recall,
)
from scripts.lib.crux_init import init_project, init_user


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = home / "project"
    project.mkdir()
    init_user(home=str(home))
    init_project(project_dir=str(project))
    crux_dir = str(project / ".crux")
    user_crux = str(home / ".crux")
    return {"project": str(project), "crux_dir": crux_dir, "home": str(home), "user_crux": user_crux}


class TestMemoryEntry:
    def test_fields(self):
        e = MemoryEntry(fact="project uses PostgreSQL", source="session")
        assert e.fact == "project uses PostgreSQL"
        assert e.source == "session"
        assert e.confidence == 1.0
        assert e.use_count == 0
        assert e.id  # auto-generated

    def test_auto_id(self):
        e1 = MemoryEntry(fact="a", source="s")
        e2 = MemoryEntry(fact="b", source="s")
        assert e1.id != e2.id


class TestSaveAndLoad:
    def test_save_project_memory(self, env):
        entry = MemoryEntry(fact="uses pytest", source="detection")
        save_memory(entry, "project", env["crux_dir"])
        loaded = load_memories("project", env["crux_dir"])
        assert len(loaded) == 1
        assert loaded[0].fact == "uses pytest"

    def test_save_user_memory(self, env):
        entry = MemoryEntry(fact="prefers snake_case", source="correction")
        save_memory(entry, "user", env["user_crux"])
        loaded = load_memories("user", env["user_crux"])
        assert len(loaded) == 1

    def test_multiple_memories(self, env):
        save_memory(MemoryEntry(fact="fact1", source="s"), "project", env["crux_dir"])
        save_memory(MemoryEntry(fact="fact2", source="s"), "project", env["crux_dir"])
        loaded = load_memories("project", env["crux_dir"])
        assert len(loaded) == 2

    def test_load_empty(self, env):
        assert load_memories("project", env["crux_dir"]) == []

    def test_deduplication(self, env):
        save_memory(MemoryEntry(fact="uses pytest", source="s"), "project", env["crux_dir"])
        save_memory(MemoryEntry(fact="uses pytest", source="s"), "project", env["crux_dir"])
        loaded = load_memories("project", env["crux_dir"])
        assert len(loaded) == 1
        assert loaded[0].use_count >= 1


class TestSearch:
    def test_finds_matching(self, env):
        save_memory(MemoryEntry(fact="project uses PostgreSQL", source="s"), "project", env["crux_dir"])
        save_memory(MemoryEntry(fact="prefers dark mode", source="s"), "project", env["crux_dir"])
        results = search_memories("postgresql", "project", env["crux_dir"])
        assert len(results) == 1
        assert "PostgreSQL" in results[0].fact

    def test_case_insensitive(self, env):
        save_memory(MemoryEntry(fact="Uses PyTest", source="s"), "project", env["crux_dir"])
        results = search_memories("pytest", "project", env["crux_dir"])
        assert len(results) == 1

    def test_no_match(self, env):
        save_memory(MemoryEntry(fact="uses pytest", source="s"), "project", env["crux_dir"])
        results = search_memories("nonexistent", "project", env["crux_dir"])
        assert results == []

    def test_empty_query(self, env):
        save_memory(MemoryEntry(fact="a fact", source="s"), "project", env["crux_dir"])
        results = search_memories("", "project", env["crux_dir"])
        assert results == []


class TestForget:
    def test_forget_existing(self, env):
        entry = MemoryEntry(fact="bad fact", source="s")
        save_memory(entry, "project", env["crux_dir"])
        result = forget_memory(entry.id, "project", env["crux_dir"])
        assert result["forgotten"] is True
        loaded = load_memories("project", env["crux_dir"])
        assert len(loaded) == 0

    def test_forget_nonexistent(self, env):
        result = forget_memory("nonexistent-id", "project", env["crux_dir"])
        assert result["forgotten"] is False


class TestMcpHelpers:
    def test_remember(self, env):
        result = remember("project uses Elixir", "project", env["crux_dir"])
        assert result["saved"] is True
        loaded = load_memories("project", env["crux_dir"])
        assert any("Elixir" in m.fact for m in loaded)

    def test_recall(self, env):
        remember("project uses Phoenix", "project", env["crux_dir"])
        remember("test with ExUnit", "project", env["crux_dir"])
        result = recall("phoenix", "project", env["crux_dir"])
        assert len(result["memories"]) == 1

    def test_recall_empty(self, env):
        result = recall("anything", "project", env["crux_dir"])
        assert result["memories"] == []

    def test_corrupt_file(self, env):
        mem_dir = os.path.join(env["crux_dir"], "memory", "project")
        os.makedirs(mem_dir, exist_ok=True)
        with open(os.path.join(mem_dir, "memories.jsonl"), "w") as f:
            f.write("not json\n")
        loaded = load_memories("project", env["crux_dir"])
        assert loaded == []

    def test_blank_lines_in_jsonl(self, env):
        mem_dir = os.path.join(env["crux_dir"], "memory", "project")
        os.makedirs(mem_dir, exist_ok=True)
        entry = {"fact": "test", "source": "s", "id": "abc", "confidence": 1.0,
                 "created_at": "2026-01-01", "last_used": "2026-01-01", "use_count": 0}
        with open(os.path.join(mem_dir, "memories.jsonl"), "w") as f:
            f.write(json.dumps(entry) + "\n\n\n" + json.dumps(entry) + "\n")
        loaded = load_memories("project", env["crux_dir"])
        assert len(loaded) == 2

    def test_os_error_returns_empty(self, env):
        from unittest.mock import patch
        # Create the file first so isfile returns True
        remember("test fact", "project", env["crux_dir"])
        with patch("scripts.lib.crux_memory.open", side_effect=OSError("permission denied")):
            loaded = load_memories("project", env["crux_dir"])
        assert loaded == []
