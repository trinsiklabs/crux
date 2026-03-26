# BUILD_PLAN_006: MCP Server Consumption — Connect to External MCP Servers

**Created:** 2026-03-26
**Status:** PHASES 0-1 COMPLETE (registry + security). Phases 2-3 (connection + proxying) deferred — requires MCP client SDK, better suited to CruxCLI-side implementation.
**Priority:** MUST-CLOSE
**Competitive Gap:** Cursor, Windsurf, Roo Code can connect to external MCP servers. Crux exposes MCP but doesn't consume others.
**Goal:** Crux MCP server acts as a proxy/aggregator — it can connect to external MCP servers and expose their tools alongside its own 43 tools. Any tool connected to Crux automatically gets access to all registered MCP servers.

**Constraint:** TDD, 100% coverage on new code.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Crux's value proposition is "one MCP server, all tools." But if a project uses a database MCP server, a GitHub MCP server, and a Figma MCP server, those are currently configured per-tool (in .mcp.json for Claude Code, .cursor/mcp.json for Cursor, etc). Crux should aggregate them — configure external servers once in `.crux/mcp-servers.json`, and every connected tool gets them all.

## Architecture

```
Claude Code / CruxCLI / Cursor
        │
        ▼
   Crux MCP Server (43 tools + proxied tools)
        │
    ┌───┼───────────┐
    ▼   ▼           ▼
  GitHub  Database   Custom
  MCP     MCP        MCP
  Server  Server     Server
```

### Config Format (.crux/mcp-servers.json)

```json
{
  "servers": {
    "github": {
      "command": ["github-mcp-server"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    },
    "postgres": {
      "command": ["postgres-mcp", "--connection", "postgresql://..."]
    }
  }
}
```

---

## Phase 0: Security Model

- [x] 0.1 External servers require explicit user registration (no auto-discovery)
- [x] 0.2 Tool allowlist: registry includes `allowed_tools` filter per server (default: all)
- [x] 0.3 No credential forwarding: _FORBIDDEN_ENV_KEYS strips CRUX_HOME/PROJECT/etc
- [x] 0.4 Timeout enforcement: configurable per-server (default 30s)

---

## Phase 1: External Server Registry

- [x] 1.1 Created `scripts/lib/crux_mcp_registry.py` with ServerConfig dataclass
- [x] 1.2 `load_registry(crux_dir)` reads `.crux/mcp-servers.json`
- [x] 1.3 `save_registry(crux_dir, servers)` writes config
- [x] 1.4 MCP tools: `register_mcp_server`, `remove_mcp_server`, `list_mcp_servers` (3 new tools, total 46)
- [x] 1.5 15 tests, 100% coverage on crux_mcp_registry.py
- [x] 1.6 Full suite: 1428 passing

## Phase 2: Server Connection Manager

- [ ] 2.1 `connect_server(name, config)` → spawn stdio subprocess, MCP handshake
- [ ] 2.2 `disconnect_server(name)` → clean shutdown
- [ ] 2.3 `list_external_tools(name)` → list tools from a connected server
- [ ] 2.4 Connection pooling: start servers lazily on first tool call
- [ ] 2.5 Health check: detect crashed servers, auto-reconnect
- [ ] 2.6 Tests with mock MCP servers

## Phase 3: Tool Proxying

- [ ] 3.1 On Crux MCP server startup, connect to all registered external servers
- [ ] 3.2 Proxy external tools through Crux: `crux_<server>_<tool>` naming
- [ ] 3.3 Forward tool calls to external server, return results
- [ ] 3.4 Handle timeouts and errors gracefully
- [ ] 3.5 Tests for tool proxying end-to-end

## Phase 4: Integration

- [ ] 4.1 MCP tool: `call_external_tool(server, tool, args)` — direct call
- [ ] 4.2 Update docs/API.md with new tools
- [ ] 4.3 Full test suite passes

---

## Convergence Criteria

- External MCP servers configurable via `.crux/mcp-servers.json`
- Tools from external servers accessible through Crux
- Any tool connected to Crux gets all external server tools
- Configure once, use everywhere
- Two consecutive clean audit passes
