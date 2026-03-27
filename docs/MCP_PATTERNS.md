# MCP Server Patterns — What We Learned Building Crux

Everything discovered building a 57-tool Rust MCP server used across Claude Code, CruxCLI, and OpenCode.

---

## 1. Capabilities Must Be Advertised

**The bug that cost us hours:** The server connected fine (`/mcp` showed "connected") but Claude Code never loaded the tools. The model said "tools aren't available" even though the server was running.

**Root cause:** The `initialize` response had `"capabilities": {}`. Claude Code saw no tool capability advertised, so it never called `tools/list`.

**Fix:**
```rust
// WRONG — empty capabilities, Claude Code ignores tools
ServerInfo {
    instructions: Some("...".into()),
    ..Default::default()
}

// CORRECT — explicitly enable tools
ServerInfo {
    instructions: Some("...".into()),
    capabilities: ServerCapabilities::builder().enable_tools().build(),
    ..Default::default()
}
```

**Rule:** Always call `enable_tools()` in capabilities. Without it, the server connects but tools are invisible.

---

## 2. Parameterless Tools — Don't Use Parameters<()>

**The bug:** Tools with `Parameters<()>` caused deserialization errors: `"failed to deserialize parameters: invalid type: map, expected unit"`.

**Root cause:** `Parameters<()>` expects `null` arguments. Claude Code sends `{}` or omits arguments entirely. The unit type `()` can't deserialize from an empty map.

**Fix:**
```rust
// WRONG — causes deserialization errors
#[tool(description = "Get session state.")]
async fn get_session_state(&self, _params: Parameters<()>) -> String { ... }

// CORRECT — no parameters at all
#[tool(description = "Get session state.")]
async fn get_session_state(&self) -> String { ... }
```

**Rule:** For tools with no parameters, omit the parameter entirely. Don't use `Parameters<()>`.

---

## 3. Tool Names Are Prefixed by the Client

Claude Code prefixes MCP tool names with the server name: `mcp__crux__restore_context`. CruxCLI prefixes with `crux_`: `crux_restore_context`. OpenCode uses similar prefixing.

**Rule:** Don't include the server name in your tool function names. The client adds the prefix.

---

## 4. Return Plain Text, Not Nested JSON

**The bug:** `restore_context` returned `{"context": "Mode: build-py\n..."}`. The client wrapped this in `{"content": [{"type": "text", "text": "{\"context\":...}"}]}`. The model received triple-nested JSON and couldn't parse it.

**Fix:**
```rust
// WRONG — returns JSON that gets double-wrapped
async fn restore_context(&self) -> String {
    serde_json::to_string(&json!({"context": parts.join("\n")})).unwrap()
}

// CORRECT — returns plain text that the model reads directly
async fn restore_context(&self) -> String {
    parts.join("\n") // Plain markdown, no JSON wrapper
}
```

**Rule:** For tools whose output the model needs to READ (not parse), return plain text. The rmcp framework wraps it in `{"content": [{"type": "text", "text": "..."}]}` automatically. For tools whose output is structured data, return JSON.

---

## 5. Per-Project Isolation via cwd

**The bug:** Multiple projects shared one MCP server config, so all sessions read the same `.crux/` directory.

**How it works:** Claude Code spawns the MCP server as a child process with `cwd` set to the project directory. CruxCLI does the same (`cwd: Instance.directory`).

**Fix:**
```rust
// Cache cwd at startup — the tool sets it to the project directory
static STARTUP_CWD: LazyLock<PathBuf> = LazyLock::new(|| {
    std::env::current_dir().unwrap_or_default()
});

fn project_dir() -> &'static Path {
    &STARTUP_CWD
}
```

**Rule:** Don't hardcode `CRUX_PROJECT` in global configs. Let each tool spawn the server with the correct cwd. The server reads `os.getcwd()` (or equivalent) at startup.

---

## 6. Config Format Varies Per Tool

| Tool | Config File | Root Key | Type Field | Command | Env Key |
|------|------------|----------|-----------|---------|---------|
| Claude Code | `.mcp.json` | `mcpServers` | `"stdio"` | string + args | `env` |
| CruxCLI | `.cruxcli/cruxcli.jsonc` | `mcp` | `"local"` | merged array | `environment` |
| OpenCode | `.opencode/opencode.json` | `mcp` | `"local"` | merged array | `environment` |
| Cursor | `.cursor/mcp.json` | `mcpServers` | (none) | string + args | `env` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` | (none) | string + args | `env` |
| Zed | `~/.config/zed/settings.json` | `context_servers` | (none) | string + args | `env` |

**Rule:** Never assume one config format. Use a recipe system that generates the correct format per tool.

---

## 7. stdout Is Sacred

All MCP communication happens over stdout (stdio transport). Any stray `println!()` breaks the JSON-RPC protocol.

**Rule:** All logging goes to stderr. Never print to stdout except MCP protocol messages.

---

## 8. The 400 Tool Concurrency Bug

Claude Code has a known bug (GitHub #9433) where tool_use blocks lose their matching tool_result. Once this happens, the conversation state is permanently corrupted. `/rewind` and `/clear` don't fix it. The session must be abandoned.

**What causes it:** Slow-starting MCP servers, server crashes during tool calls, or race conditions in the protocol.

**Mitigation:**
1. Use Rust (sub-millisecond startup) instead of Python (26ms) or Node (200ms+)
2. Never crash — catch all errors, return error responses
3. Build session recovery (`crux recover`) to extract context from corrupted .jsonl files

---

## 9. MCP Server Instructions Are Hints, Not Guarantees

The `instructions` field in `ServerInfo` tells the model what to do. Non-Claude models (MiMo, GPT, DeepSeek) often ignore it.

**Rule:** Instructions are suggestions for capable models. For critical behavior (session state updates, correction detection), enforce via hooks or infrastructure — not instructions.

---

## 10. Binary Size and Dependencies

| Component | Size Impact |
|-----------|------------|
| rmcp (MCP SDK) | ~500KB |
| tokio (async runtime) | ~300KB |
| clap (CLI) | ~200KB |
| serde_json | ~100KB |
| reqwest (HTTP) | ~200KB |
| tree-sitter + 4 grammars | ~4MB |
| **Total** | **~6.6MB** |

Tree-sitter grammars are compiled C and dominate binary size. Without tree-sitter: ~2.5MB.

**Rule:** If you don't need multi-language AST parsing, skip tree-sitter. The binary drops from 6.6MB to 2.5MB.

---

## 11. Testing MCP Servers

**Unit tests:** Test handler functions directly — session roundtrips, file operations, data structures.

**Integration tests:** Spawn the binary as a subprocess, send JSON-RPC over stdin, read responses from stdout. This tests the full MCP protocol stack.

```rust
// Integration test pattern
let mut child = Command::new(env!("CARGO_BIN_EXE_crux"))
    .args(["mcp", "start"])
    .stdin(Stdio::piped()).stdout(Stdio::piped())
    .spawn().unwrap();

// Send initialize, read response
// Send tools/list, verify tool count
// Send tools/call, verify result
```

**Rule:** Always test via the MCP protocol, not just unit tests. The protocol layer (capabilities, parameter serialization, response wrapping) is where bugs hide.
