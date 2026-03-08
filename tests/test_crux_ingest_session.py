"""Tests for crux ingest-session daemon."""

import json
import os

import pytest

from scripts.lib.crux_ingest_session import (
    IngestCheckpoint,
    load_checkpoint,
    save_checkpoint,
    extract_files_touched,
    extract_decisions,
    detect_corrections,
    SessionEntry,
)


@pytest.fixture
def crux_dir(tmp_path):
    """Create a .crux directory."""
    crux = tmp_path / ".crux"
    crux.mkdir()
    return str(crux)


class TestCheckpoint:
    def test_save_and_load(self, crux_dir):
        checkpoint = IngestCheckpoint(
            session_file="/path/to/session.jsonl",
            lines_processed=100,
            files_extracted=["/a.py", "/b.py"],
        )
        save_checkpoint(checkpoint, crux_dir)

        loaded = load_checkpoint(crux_dir)
        assert loaded is not None
        assert loaded.session_file == "/path/to/session.jsonl"
        assert loaded.lines_processed == 100
        assert len(loaded.files_extracted) == 2

    def test_load_missing(self, crux_dir):
        loaded = load_checkpoint(crux_dir)
        assert loaded is None

    def test_load_corrupt(self, crux_dir):
        os.makedirs(os.path.join(crux_dir, "ingest"))
        with open(os.path.join(crux_dir, "ingest", "checkpoint.json"), "w") as f:
            f.write("not json")
        loaded = load_checkpoint(crux_dir)
        assert loaded is None


class TestExtractFilesTouched:
    def test_extracts_edit_files(self):
        entries = [
            SessionEntry(type="tool_use", content={}, tool_name="Edit", tool_input={"file_path": "/a.py"}),
            SessionEntry(type="tool_use", content={}, tool_name="Write", tool_input={"file_path": "/b.py"}),
            SessionEntry(type="tool_use", content={}, tool_name="Read", tool_input={"file_path": "/c.py"}),
        ]
        files = extract_files_touched(entries)
        assert "/a.py" in files
        assert "/b.py" in files
        assert "/c.py" in files

    def test_deduplicates(self):
        entries = [
            SessionEntry(type="tool_use", content={}, tool_name="Edit", tool_input={"file_path": "/a.py"}),
            SessionEntry(type="tool_use", content={}, tool_name="Edit", tool_input={"file_path": "/a.py"}),
        ]
        files = extract_files_touched(entries)
        assert len(files) == 1

    def test_ignores_other_tools(self):
        entries = [
            SessionEntry(type="tool_use", content={}, tool_name="Bash", tool_input={"command": "ls"}),
        ]
        files = extract_files_touched(entries)
        assert files == []


class TestExtractDecisions:
    def test_finds_decision_markers(self):
        entries = [
            SessionEntry(type="assistant", content="I'll use PostgreSQL for the database."),
        ]
        decisions = extract_decisions(entries)
        assert len(decisions) == 1
        assert "PostgreSQL" in decisions[0]

    def test_limits_decisions(self):
        entries = [
            SessionEntry(type="assistant", content=f"I'll use approach {i}.") for i in range(30)
        ]
        decisions = extract_decisions(entries)
        assert len(decisions) <= 20


class TestDetectCorrections:
    def test_finds_correction_markers(self):
        entries = [
            SessionEntry(type="user", content="No, that's wrong. Use the other method."),
        ]
        corrections = detect_corrections(entries)
        assert len(corrections) == 1
        assert "no," in corrections[0]["marker"]

    def test_ignores_non_corrections(self):
        entries = [
            SessionEntry(type="user", content="Thanks, that looks good!"),
        ]
        corrections = detect_corrections(entries)
        assert len(corrections) == 0
