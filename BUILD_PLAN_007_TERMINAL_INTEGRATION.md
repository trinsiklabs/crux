# BUILD_PLAN_007: Terminal Integration — CLI Interface for Crux

**Created:** 2026-03-26
**Status:** NOT STARTED
**Priority:** MUST-CLOSE
**Competitive Gap:** Cursor and Windsurf have native terminal integration. Crux has no direct terminal interface — it's only accessible via MCP tools in other tools.
**Goal:** `crux` CLI provides a terminal-native interface to all Crux capabilities — status, session management, tool switching, knowledge lookup, and health checks — without needing to be inside an AI coding tool session.

**Constraint:** TDD, 100% coverage on new code.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Currently `bin/crux` only has: setup, update, doctor, adopt, version. Users can't interact with Crux directly from the terminal. Checking session state, switching tools, looking up knowledge, running diagnostics — all require being inside a Claude Code or CruxCLI session. A terminal CLI makes Crux a first-class citizen on the command line.

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
- [ ] 1.2 `crux status` — read and display session state (mode, tool, working_on, files, decisions)
- [ ] 1.3 `crux switch <tool>` — call switch_tool() with auto_handoff, show result
- [ ] 1.4 Tests for each subcommand

## Phase 2: Knowledge + Diagnostics

- [ ] 2.1 `crux knowledge <query>` — call lookup_knowledge(), format results
- [ ] 2.2 `crux health` — call verify_health(), show pass/fail table
- [ ] 2.3 `crux digest [date]` — show daily digest
- [ ] 2.4 `crux log [--tail N]` — show recent interactions from analytics
- [ ] 2.5 Tests for knowledge, health, digest, log

## Phase 3: MCP Server Management

- [ ] 3.1 `crux mcp start` — start MCP server in foreground (stdio)
- [ ] 3.2 `crux mcp status` — show registered servers, connection status, tool count
- [ ] 3.3 `crux mcp tools` — list all MCP tools with descriptions
- [ ] 3.4 Tests for MCP subcommands

## Phase 4: Interactive Features

- [ ] 4.1 `crux correct "<original>" "<corrected>"` — log a correction from terminal
- [ ] 4.2 `crux handoff` — show or regenerate handoff context
- [ ] 4.3 `crux impact "<prompt>"` — run analyze_impact from terminal
- [ ] 4.4 Colored output, table formatting
- [ ] 4.5 Tests and integration verification

---

## Convergence Criteria

- All subcommands operational from terminal
- Zero dependency on being inside an AI tool session
- Same handler functions as MCP tools (no duplication)
- Full test suite passes
- Two consecutive clean audit passes
