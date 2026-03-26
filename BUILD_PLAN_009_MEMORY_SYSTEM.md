# BUILD_PLAN_009: Cross-Session Memory System

**Created:** 2026-03-26
**Status:** PHASES 1+3 COMPLETE (storage + MCP tools). Phase 2 (auto-capture) and Phase 4 (promotion/decay) deferred.
**Priority:** SHOULD-CLOSE
**Competitive Gap:** Claude Code has a memory system (~/.claude/memory/) that persists facts across sessions. Crux has knowledge entries but no structured memory that accumulates automatically.
**Goal:** Build a memory system in `.crux/memory/` that automatically captures and retrieves project-specific and user-level facts. Works across all tools — not just Claude Code.

**Constraint:** TDD, 100% coverage on new code.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Crux has corrections (reactive — captured when user corrects AI) and knowledge entries (manually promoted). Neither is automatic memory. Claude Code's memory auto-captures facts like "this project uses PostgreSQL" and "the user prefers snake_case." Crux needs equivalent memory that works across ALL tools.

## Architecture

```
Memory sources:
  corrections → pattern detection → memory entries
  session state → working_on, decisions → memory entries
  user messages → fact extraction → memory entries
  tool results → environment facts → memory entries

Storage:
  .crux/memory/project/     # per-project facts
  ~/.crux/memory/user/      # cross-project preferences

Retrieval:
  On restore_context: inject relevant memories
  On tool call: context-aware memory lookup
  MCP tool: remember(fact), recall(query), forget(id)
```

---

## Phase 1: Memory Storage

- [ ] 1.1 Create `scripts/lib/crux_memory.py` with `MemoryEntry` dataclass (id, fact, source, confidence, created_at, last_used, use_count)
- [ ] 1.2 `save_memory(entry, scope, crux_dir)` — write to project or user memory
- [ ] 1.3 `load_memories(scope, crux_dir)` → `list[MemoryEntry]`
- [ ] 1.4 `search_memories(query, scope, crux_dir)` → `list[MemoryEntry]` — keyword search
- [ ] 1.5 `forget_memory(id, scope, crux_dir)` — soft-delete
- [ ] 1.6 Tests for CRUD operations

## Phase 2: Auto-Capture from Existing Signals

- [ ] 2.1 Extract memories from correction patterns: "user prefers X over Y"
- [ ] 2.2 Extract memories from session state: "project uses Python 3.14", "testing with pytest"
- [ ] 2.3 Extract memories from git: tech stack (from file extensions), team patterns (from commit authors)
- [ ] 2.4 Deduplication: don't store the same fact twice
- [ ] 2.5 Confidence scoring: memories used more often get higher confidence
- [ ] 2.6 Tests for each extraction source

## Phase 3: MCP Tools

- [ ] 3.1 `remember(fact, scope)` — manually add a memory
- [ ] 3.2 `recall(query, scope)` — search memories
- [ ] 3.3 `forget(memory_id)` — remove a memory
- [ ] 3.4 `list_memories(scope)` — list all memories
- [ ] 3.5 Integrate into `restore_context()` — inject relevant memories alongside session state
- [ ] 3.6 Tests for MCP tools

## Phase 4: Memory Promotion

- [ ] 4.1 Project → user promotion: memories used in 3+ projects auto-promote
- [ ] 4.2 Decay: unused memories lose confidence over time
- [ ] 4.3 Max memory limit per scope (default: 500 project, 200 user)
- [ ] 4.4 Tests for promotion and decay

---

## Convergence Criteria

- Memory entries stored in .crux/memory/ (project) and ~/.crux/memory/ (user)
- Auto-capture from corrections, session state, and git
- MCP tools: remember, recall, forget, list_memories
- Relevant memories injected on restore_context
- Works across all tools via MCP
- Two consecutive clean audit passes
