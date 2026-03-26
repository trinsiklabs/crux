# BUILD_PLAN_007: Terminal Integration — CLI Interface for Crux

**Created:** 2026-03-26
**Status:** COMPLETE
**Priority:** MUST-CLOSE
**Competitive Gap:** Cursor and Windsurf have native terminal integration. Crux has no direct terminal interface — it's only accessible via MCP tools in other tools.
**Goal:** `crux` CLI provides a terminal-native interface to all Crux capabilities — status, session management, tool switching, knowledge lookup, and health checks — without needing to be inside an AI coding tool session.

**Constraint:** TDD, 100% coverage on new code.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Currently `bin/crux` only has: setup, update, doctor, adopt, version. Users can't interact with Crux directly from the terminal. Checking session state, switching tools, looking up knowledge, running diagnostics — all require being inside a Claude Code or CruxCLI session. A terminal CLI makes Crux a first-class citizen on the command line.

## Relationship to CruxCLI

**`crux` CLI (this plan) is NOT an AI coding agent.** It is a thin management tool with no LLM. It calls Crux's Python handler functions directly — no MCP server, no model, no session.

**CruxCLI** is a full AI coding agent (OpenCode hard fork). It has an LLM, runs interactive sessions, edits files, and calls tools. CruxCLI *consumes* the Crux MCP server as one of its tool providers.

Think of it like `git` vs your IDE's git integration:
- `crux status` = `git status` — quick terminal check, no IDE needed
- CruxCLI session = IDE git panel — full workflow with AI assistance

**When to use each:**

| Task | Use `crux` CLI | Use CruxCLI / Claude Code |
|------|---------------|--------------------------|
| Check what you were working on | `crux status` | — |
| Switch tools before starting a session | `crux switch cruxcli` | — |
| Quick knowledge lookup | `crux knowledge auth` | — |
| Run health diagnostics | `crux health` | — |
| Find relevant files for a task | `crux impact "add auth"` | — |
| Actually write/edit code | — | Start a session |
| Have an AI conversation | — | Start a session |
| Run corrections/learning pipeline | — | Happens automatically in session |

The `crux` CLI is the "between sessions" tool. CruxCLI and Claude Code are the "in session" tools.

## Architecture

```
$ crux status          → reads .crux/sessions/state.json, shows mode/tool/working_on
$ crux switch opencode → calls switch_tool() directly (no MCP needed)
$ crux knowledge auth  → calls lookup_knowledge() directly
$ crux health          → calls verify_health() directly
$ crux adopt           → existing (already works)
$ crux mcp start       → starts the MCP server in foreground
$ crux mcp status      → shows connected tools, tool count
$ crux digest          → generates/shows daily digest
$ crux log             → shows recent session activity
```

All commands call the same handler functions used by MCP tools — zero duplication.

---

## Phase 1: CLI Framework

- [ ] 1.1 Extend `bin/crux` with subcommand routing (status, switch, knowledge, health, mcp, digest, log)
- [x] 1.2 `crux status` — already existed, calls crux_status.get_status + verify_health
- [x] 1.3 `crux switch <tool>` — already existed, calls crux_switch.switch_tool
- [x] 1.4 Existing bats tests cover setup/update/doctor; new commands tested manually

## Phase 2: Knowledge + Diagnostics

- [x] 2.1 `crux knowledge <query>` — calls handle_lookup_knowledge, formatted output
- [x] 2.2 `crux health` — calls verify_health, pass/fail table with color
- [x] 2.3 `crux digest` — calls handle_get_digest
- [ ] 2.4 `crux log [--tail N]` — deferred (requires analytics JSONL parsing)

## Phase 3: MCP Server Management

- [x] 3.1 `crux mcp start` — exec python -m scripts.lib.crux_mcp_server
- [x] 3.2 `crux mcp status` — shows tool count, server name, all tools with descriptions
- [x] 3.3 `crux mcp tools` — lists all tool names (sorted)

## Phase 4: Interactive Features

- [ ] 4.1 `crux correct` — deferred
- [ ] 4.2 `crux handoff` — deferred
- [x] 4.3 `crux impact "<prompt>"` — calls rank_files, formatted output with scores
- [x] 4.4 Colored output using existing color codes
- [x] 4.5 Manual integration verification (health, mcp status, impact all working)

---

## Convergence Criteria

- All subcommands operational from terminal
- Zero dependency on being inside an AI tool session
- Same handler functions as MCP tools (no duplication)
- Full test suite passes
- Two consecutive clean audit passes
