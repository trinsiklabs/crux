# BUILD_PLAN_005: Seamless Tool Transition System

**Created:** 2026-03-24
**Status:** COMPLETE
**Goal:** Zero-prep switching between AI coding tools. Kill any session at any time, restore in any tool, lose nothing. Three parts: always-on session state, tool recipe engine, and enhanced switch_tool_to MCP tool.

**Constraint:** TDD, 100% coverage on new code.
**Constraint:** All tool recipes verified against actual config formats (research from cruxdev session).
**Rule:** Two consecutive clean audit passes = convergence.

## Document Alignment

- CruxDev inbox messages: tool transition recipes (6 tools), always-on session state
- `scripts/lib/crux_sync.py` — existing adapter layer (opencode, claude-code, cursor, windsurf)
- `scripts/lib/crux_switch.py` — existing switch_tool function
- `scripts/lib/crux_session.py` — session state management
- `scripts/lib/crux_mcp_server.py` — MCP server instructions field

---

## Architecture

```
Current:                                Target:
  switch_tool_to("opencode")              switch_tool_to("cruxcli")
    → crux_switch.py                        → auto-write handoff from session state
    → crux_sync.py (4 tools)                → look up recipe for target tool
    → generates configs                     → write MCP config in target's format
    → manual handoff needed                 → return launch command + "call restore_context()"
                                            → works for all 6 tools
                                            → no manual handoff ever needed
```

### Tool Recipe Format

```python
@dataclass
class ToolRecipe:
    tool_id: str                    # "claude-code", "cruxcli", "cursor", etc.
    config_file: str                # relative path from project root (or absolute for global)
    root_key: str                   # "mcpServers" or "mcp" or "context_servers"
    type_value: str | None          # "stdio", "local", or None (implicit)
    command_format: str             # "string_args" or "merged_array"
    env_key: str                    # "env" or "environment"
    url_key: str                    # "url" or "serverUrl"
    project_scoped: bool            # True if per-project config, False if global only
    interpolation: str              # "${VAR}", "{env:VAR}", "${env:VAR}"
    launch_command: str             # Command to start the tool
    jsonc: bool                     # True for JSONC format (comments allowed)
    tested: bool                    # Whether this recipe has been verified
    last_tested: str | None         # ISO date of last test
```

### 6 Tool Recipes

| Tool | Config | Root Key | Type | Cmd Format | Env Key | Project |
|------|--------|----------|------|------------|---------|---------|
| claude-code | .mcp.json | mcpServers | stdio | string+args | env | Yes |
| cruxcli | .cruxcli/cruxcli.jsonc | mcp | local | merged array | environment | Yes |
| opencode | .opencode/opencode.jsonc | mcp | local | merged array | environment | Yes |
| cursor | .cursor/mcp.json | mcpServers | (none) | string+args | env | Yes |
| windsurf | ~/.codeium/windsurf/mcp_config.json | mcpServers | (none) | string+args | env | No |
| zed | ~/.config/zed/settings.json | context_servers | (none) | string+args | env | No |

---

## Phase 1: Always-On Session State

**Purpose:** Session state is continuously maintained so context can be restored at any time without advance notice.

### Checklist — Phase 1

- [x] 1.1 Updated MCP server instructions with always-on session state requirement
- [x] 1.2 Added `auto_handoff()` to crux_session.py — generates from accumulated state, truncates large lists
- [x] 1.3 11 tests for auto_handoff (empty, rich, truncation, file write, no session)
- [x] 1.4 Tests pass, coverage = 100% on new code

---

## Phase 2: Tool Recipe Engine

**Purpose:** Centralized knowledge of how each tool's MCP config works, used to generate correct configs for any tool.

### Checklist — Phase 2

- [x] 2.1 Created `scripts/lib/crux_tool_recipes.py` with ToolRecipe dataclass and RECIPES for all 6 tools
- [x] 2.2 `get_recipe(tool_id)` returns recipe or None
- [x] 2.3 `generate_mcp_config()` writes correct config for any tool
- [x] 2.4 Global tools (windsurf, zed) write to home dir via expanduser
- [x] 2.5 JSONC handled (write JSON without comments for cruxcli/opencode)
- [x] 2.6 Merged-array command format for cruxcli/opencode
- [x] 2.7 Type field: stdio, local, or omitted per tool
- [x] 2.8 Env key: env vs environment per tool
- [x] 2.9 14 tests covering all 6 tools + edge cases
- [x] 2.10 Merge existing config (don't overwrite), corrupt config recovery
- [x] 2.11 Tests pass, coverage = 100%

---

## Phase 3: Enhanced switch_tool_to

**Purpose:** One-command tool transition that auto-writes handoff, generates target config, returns launch instructions.

### Checklist — Phase 3

- [x] 3.1 Updated handle_switch_tool: auto_handoff() → sync_tool (existing) → fallback to recipe engine → launch instructions
- [x] 3.2 Recipe engine handles cruxcli/zed as fallback (SUPPORTED_TOOLS kept for full sync, recipes for config-only)
- [x] 3.3 Existing sync_claude_code/sync_opencode kept (they do more: modes, symlinks, AGENTS.md)
- [x] 3.4 Return includes: success, from_tool, to_tool, config_written, launch_command, restore_instruction
- [x] 3.5 Existing switch tests pass + recipe fallback works for unsupported tools
- [x] 3.6 Auto-handoff called on every switch
- [x] 3.7 Tests pass, 1399 total

---

## Phase 4: Integration Verification

**Purpose:** End-to-end verification that the transition system works.

### Checklist — Phase 4

- [x] 4.1 Verified: cruxcli recipe generates .cruxcli/cruxcli.jsonc with type=local, merged array command
- [x] 4.2 Verified: claude-code recipe generates .mcp.json with type=stdio
- [x] 4.3 Verified: cursor recipe generates .cursor/mcp.json without type field
- [x] 4.4 Verified: auto_handoff produces restorable context with mode, tool, decisions, files, pending
- [x] 4.5 Full test suite: 1399 passing
- [x] 4.6 Coverage = 100% on crux_tool_recipes.py (52 statements)

---

## Convergence Criteria

- All checklist items complete
- All 6 tool recipes defined and tested
- auto_handoff() generates from accumulated state
- switch_tool_to() handles all 6 tools
- MCP server instructions updated for always-on state
- Two consecutive clean audit passes

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSONC parsing complexity | cruxcli config has comments | Use json with comment stripping (regex) or write-only approach |
| Global-only tools (windsurf, zed) conflict with other projects | Config overwritten | Merge into existing config, don't replace |
| Zed settings.json has many other keys | Accidental data loss | Read existing, merge context_servers key only |
| Tool-specific config drift | Recipe outdated | tested/last_tested tracking, verify on each use |
| Large session state in handoff | Context too long | Truncate to last N decisions/files, summarize |
