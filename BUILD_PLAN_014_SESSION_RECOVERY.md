# BUILD_PLAN_014: Session Recovery — Adopt Corrupted Claude Code Sessions

**Created:** 2026-03-27
**Status:** IN PROGRESS
**Goal:** When a Claude Code session is corrupted (400 tool concurrency error, unrecoverable), Crux can ingest the session's .jsonl file directly from disk, extract all useful context (decisions, files touched, working_on, corrections, knowledge), and make it available via `restore_context` in a new session. No running Claude Code instance needed.

**Constraint:** Works entirely from the .jsonl file on disk — no API calls, no running Claude Code.
**Constraint:** Handles 72MB+ session files (12K+ messages) efficiently.
**Rule:** TDD. Tests before code.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Claude Code sessions corrupt when tool_use/tool_result blocks get mismatched (GitHub issue #9433). Once corrupted, the session cannot be loaded — `/rewind`, `/clear`, `--continue` all fail with "API Error: 400". The conversation history (decisions, context, files, corrections) is trapped in a .jsonl file that nothing can read.

Crux should be the escape hatch. `crux recover <session-id>` reads the .jsonl, extracts everything useful, writes it to `.crux/sessions/`, and the next session gets full context via `restore_context`.

## Architecture

```
~/.claude/projects/<project-hash>/<session-id>.jsonl
    │
    ▼
crux recover <session-id-or-path>
    │
    ├── Parse JSONL (streaming, handles 72MB+)
    ├── Extract assistant messages → working_on, decisions
    ├── Extract tool_use results → files touched
    ├── Extract user messages → corrections (10 regex patterns)
    ├── Extract git commits from Bash tool outputs → key decisions
    ├── Build session state from accumulated data
    └── Write to .crux/sessions/state.json + handoff.md

Next session:
    restore_context() → full context from recovered session
```

---

## Phase 1: JSONL Parser

**Purpose:** Stream-parse Claude Code session .jsonl files efficiently.

### Checklist — Phase 1

- [ ] 1.1 Create `src/recover.rs` module
- [ ] 1.2 `parse_session(path) -> SessionData` — streaming JSONL parser that handles 72MB+ files without loading all into memory
- [ ] 1.3 `SessionData` struct: messages (assistant text, user text), tool_calls (name, input, output), metadata (session_id, project, timestamps)
- [ ] 1.4 Handle malformed lines gracefully (skip, don't crash)
- [ ] 1.5 Handle the specific Claude Code message types: `user`, `assistant`, `tool_use`, `tool_result`, `file-history-snapshot`, `agent-name`, `custom-title`, `last-prompt`
- [ ] 1.6 Tests with fixture .jsonl files (small synthetic ones, not the 72MB real file)

---

## Phase 1B: Full Session Log Ingestion

**Purpose:** Ingest every interaction from the Claude Code session into Crux's analytics format, not just extracted context.

### Checklist — Phase 1B

- [ ] 1B.1 Convert all user messages to `.crux/analytics/conversations/<date>.jsonl` format (role, content, timestamp, tool, mode)
- [ ] 1B.2 Convert all assistant messages to conversations JSONL
- [ ] 1B.3 Convert all tool_use/tool_result pairs to `.crux/analytics/interactions/<date>.jsonl` format (tool_name, input, output, timestamp)
- [ ] 1B.4 Preserve original timestamps from the Claude Code session
- [ ] 1B.5 Deduplicate: if analytics already has entries for the same timestamps, skip
- [ ] 1B.6 Tests for full log ingestion

---

## Phase 2: Context Extraction

**Purpose:** Extract useful context from parsed session data.

### Checklist — Phase 2

- [ ] 2.1 Extract `working_on` from the last assistant message that describes current work
- [ ] 2.2 Extract `key_decisions` from:
  - Assistant messages containing decision language ("decided to", "chose", "using X because")
  - Git commit messages from Bash tool outputs (`[branch hash] message` pattern)
  - User messages that set direction ("let's use", "switch to", "we need")
- [ ] 2.3 Extract `files_touched` from:
  - Edit/Write tool_use inputs (file_path field)
  - Read tool_use inputs (file_path field)
  - Bash tool outputs containing file paths
- [ ] 2.4 Extract corrections from user messages (10 regex patterns from hooks.rs)
- [ ] 2.5 Extract `pending` from:
  - TODO markers in assistant messages
  - Uncompleted task items
  - Last user request that wasn't fully answered
- [ ] 2.6 Build `SessionState` from all extracted data
- [ ] 2.7 Tests for each extraction type

---

## Phase 3: Recovery CLI Command

**Purpose:** `crux recover` command that does the full pipeline.

### Checklist — Phase 3

- [ ] 3.1 `crux recover <path-or-session-id>` CLI subcommand
- [ ] 3.2 If given a session ID, auto-find the .jsonl in `~/.claude/projects/`
- [ ] 3.3 If given a path, read directly
- [ ] 3.4 Auto-detect project directory from the session's `cwd` field
- [ ] 3.5 Write recovered state to `.crux/sessions/state.json`
- [ ] 3.6 Write recovered handoff to `.crux/sessions/handoff.md`
- [ ] 3.7 Write corrections to `.crux/corrections/corrections.jsonl`
- [ ] 3.8 Print summary: "Recovered: X decisions, Y files, Z corrections from session <id>"
- [ ] 3.9 Tests for CLI flow

---

## Phase 4: MCP Tool

**Purpose:** `recover_session` MCP tool so any connected AI tool can trigger recovery.

### Checklist — Phase 4

- [ ] 4.1 Add `recover_session(session_path)` to MCP server
- [ ] 4.2 Returns recovered context summary
- [ ] 4.3 Auto-detects most recent session if no path given
- [ ] 4.4 Tests

---

## Phase 5: Auto-Detection in restore_context

**Purpose:** When `restore_context` finds an empty/stale session state, automatically check for recoverable Claude Code sessions.

### Checklist — Phase 5

- [ ] 5.1 In `restore_context`, if state is empty/stale (>24h old), scan `~/.claude/projects/<project-hash>/` for recent .jsonl files
- [ ] 5.2 If found, offer recovery: "Found a recent Claude Code session (12K messages, last modified 2 hours ago). Recovering context..."
- [ ] 5.3 Auto-recover and inject into response
- [ ] 5.4 Tests

---

## Convergence Criteria

- `crux recover` works on real corrupted .jsonl files
- Recovers: working_on, decisions, files, corrections, pending tasks
- Handles 72MB+ files without OOM
- MCP tool available for in-session recovery
- restore_context auto-detects recoverable sessions
- Two consecutive clean audit passes

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| .jsonl format changes between Claude Code versions | Parser breaks | Parse defensively — skip unknown fields, don't require all fields |
| 72MB files slow to parse | Recovery takes too long | Stream parse, don't load all into memory. Target: <5s for 72MB |
| Too many decisions extracted (noise) | Useless context | Filter: last N decisions, skip trivial ones, prefer git commits |
| Session has no useful content | Empty recovery | Detect and report: "Session has no recoverable context" |
