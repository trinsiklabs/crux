"""Cross-session memory system — persistent fact storage.

Stores project-level and user-level facts in .crux/memory/.
Auto-deduplicates. Supports search, forget, and confidence scoring.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class MemoryEntry:
    """A single persistent fact."""
    fact: str
    source: str  # "session", "correction", "detection", "manual"
    id: str = ""
    confidence: float = 1.0
    created_at: str = ""
    last_used: str = ""
    use_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.last_used:
            self.last_used = self.created_at


def _memory_path(scope: str, crux_dir: str) -> str:
    """Path to the JSONL memory file for a scope."""
    return os.path.join(crux_dir, "memory", scope, "memories.jsonl")


def save_memory(entry: MemoryEntry, scope: str, crux_dir: str) -> None:
    """Save a memory entry. Deduplicates by fact text."""
    existing = load_memories(scope, crux_dir)

    # Check for duplicate
    for i, e in enumerate(existing):
        if e.fact.lower() == entry.fact.lower():
            existing[i].use_count += 1
            existing[i].last_used = _now_iso()
            existing[i].confidence = min(existing[i].confidence + 0.1, 2.0)
            _write_all(existing, scope, crux_dir)
            return

    existing.append(entry)
    _write_all(existing, scope, crux_dir)


def _write_all(entries: list[MemoryEntry], scope: str, crux_dir: str) -> None:
    """Write all memory entries to the JSONL file."""
    path = _memory_path(scope, crux_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(asdict(entry)) + "\n")


def load_memories(scope: str, crux_dir: str) -> list[MemoryEntry]:
    """Load all memory entries for a scope."""
    path = _memory_path(scope, crux_dir)
    if not os.path.isfile(path):
        return []

    entries: list[MemoryEntry] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(MemoryEntry(**{
                        k: v for k, v in data.items()
                        if k in MemoryEntry.__dataclass_fields__
                    }))
                except (json.JSONDecodeError, TypeError):
                    continue
    except OSError:
        return []
    return entries


def search_memories(query: str, scope: str, crux_dir: str) -> list[MemoryEntry]:
    """Search memories by keyword (case-insensitive)."""
    if not query:
        return []
    lower_query = query.lower()
    entries = load_memories(scope, crux_dir)
    return [e for e in entries if lower_query in e.fact.lower()]


def forget_memory(memory_id: str, scope: str, crux_dir: str) -> dict:
    """Remove a memory by ID."""
    entries = load_memories(scope, crux_dir)
    before = len(entries)
    entries = [e for e in entries if e.id != memory_id]
    if len(entries) < before:
        _write_all(entries, scope, crux_dir)
        return {"forgotten": True, "id": memory_id}
    return {"forgotten": False, "error": f"Memory {memory_id} not found"}


# ---------------------------------------------------------------------------
# MCP-friendly helpers
# ---------------------------------------------------------------------------

def remember(fact: str, scope: str, crux_dir: str) -> dict:
    """Save a fact to memory (MCP-friendly wrapper)."""
    entry = MemoryEntry(fact=fact, source="manual")
    save_memory(entry, scope, crux_dir)
    return {"saved": True, "fact": fact, "scope": scope}


def recall(query: str, scope: str, crux_dir: str) -> dict:
    """Search memories (MCP-friendly wrapper)."""
    results = search_memories(query, scope, crux_dir)
    return {
        "memories": [
            {"id": e.id, "fact": e.fact, "confidence": e.confidence, "use_count": e.use_count}
            for e in results
        ],
        "total": len(results),
    }
