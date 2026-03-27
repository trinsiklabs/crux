# BUILD_PLAN_015: Fix Session State Staleness

**Created:** 2026-03-27
**Status:** IN PROGRESS
**Goal:** Prevent stale session state (wrong mode, old decisions, expired context) from being injected into agent system prompts. Add project-type detection, state expiry, and decision metadata.

**Constraint:** Implementation is 100% Rust. All code in src/.
**Rule:** TDD. Tests before code.
**Rule:** Two consecutive clean passes = convergence.

## Document Alignment

- `src/session.rs` — session state management (Rust)
- `src/server.rs` — MCP tools including restore_context, update_session (Rust)
- `src/context.rs` — project type detection (Rust, already has detect_tech_stack)
- `src/cli/mod.rs` — hook handlers (Rust)
- `BUILD_PLAN_014_SESSION_RECOVERY.md` — related but addresses corruption, not staleness

---

## Phase 1: Project Type Detection

**Purpose:** Auto-detect project language/framework from filesystem markers so the correct mode can be selected.

### Checklist — Phase 1

- [ ] 1.1 Create `detect_project_type(project_dir)` function that scans for:
  - `package.json` / `tsconfig.json` → TypeScript/JavaScript
  - `pyproject.toml` / `requirements.txt` / `setup.py` → Python
  - `mix.exs` → Elixir
  - `Cargo.toml` → Rust
  - `go.mod` → Go
  - `Gemfile` → Ruby
  - Returns: primary language, confidence, suggested mode
- [ ] 1.2 Map project types to recommended modes (e.g., TypeScript → `build-ts`, Python → `build-py`, Elixir → `build-ex`)
- [ ] 1.3 Tests for detection across all supported project types
- [ ] 1.4 Tests for ambiguous projects (e.g., both `package.json` and `pyproject.toml`)

---

## Phase 2: State Expiry and Validation

**Purpose:** Detect and handle stale session state before injecting it into prompts.

### Checklist — Phase 2

- [ ] 2.1 Add `expires_at` field to SessionState (default: 24 hours from `updated_at`)
- [ ] 2.2 In `restore_context()`: check if state is expired; if yes, archive and create fresh state
- [ ] 2.3 In `restore_context()`: detect project type and compare with `state.active_mode`; warn or auto-switch if mismatched
- [ ] 2.4 Add configurable TTL via `.crux/config.json` (`session_ttl_hours`, default 24)
- [ ] 2.5 Actually call `archive_session()` (exists but never invoked)
- [ ] 2.6 Tests for expiry detection, auto-archival, mode mismatch warning

---

## Phase 3: Decision Metadata

**Purpose:** Add timestamps and project context to decisions so stale ones can be filtered.

### Checklist — Phase 3

- [ ] 3.1 Change `key_decisions` from `list[str]` to `list[{text, timestamp, project_dir}]`
- [ ] 3.2 Migrate existing string decisions to new format (add current timestamp, current project_dir)
- [ ] 3.3 In `restore_context()`: only inject decisions from last 24 hours (configurable)
- [ ] 3.4 In `restore_context()`: only inject decisions matching current project directory
- [ ] 3.5 Tests for decision filtering by age and project

---

## Phase 4: Pending Task Validation

**Purpose:** Prevent stale pending tasks from being injected.

### Checklist — Phase 4

- [ ] 4.1 Add timestamp to pending tasks (same format as decisions)
- [ ] 4.2 In `restore_context()`: filter pending tasks older than 24 hours
- [ ] 4.3 In `restore_context()`: validate `files_touched` still exist on disk; remove deleted
- [ ] 4.4 Tests for pending task filtering and file validation

---

## Phase 5: Session Lifecycle Hooks

**Purpose:** Auto-archive or refresh state on significant changes.

### Checklist — Phase 5

- [ ] 5.1 In `handle_session_start`: detect project type; if mode doesn't match, log warning and optionally auto-switch
- [ ] 5.2 In `handle_session_start`: if state is >24h old, archive and start fresh
- [ ] 5.3 Clear `working_on` and `pending` when a new session starts (they're session-scoped, not project-scoped)
- [ ] 5.4 Preserve `key_decisions` across sessions (they're project-scoped) but filter by age
- [ ] 5.5 Tests for lifecycle transitions

---

## Post-Execution Convergence Checklist

- [ ] Documentation convergence
- [ ] Inbox check: check_inbox() for messages from other sessions

---

## Test Commands

```bash
cd /Users/user/personal/crux && cargo test
```

## Convergence Criteria

- Project type detection works for 7 languages
- Stale state (>24h) auto-archived on session start
- Mode mismatch detected and warned/corrected
- Decisions filtered by age and project
- Pending tasks validated for freshness
- Two consecutive clean audit passes
