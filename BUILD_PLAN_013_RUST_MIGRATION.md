# BUILD_PLAN_013: Complete Migration to Rust

**Created:** 2026-03-26
**Status:** NOT STARTED
**Goal:** Rewrite the entire Crux codebase in Rust. Single binary, zero runtime dependencies. MCP server via rmcp, CLI via clap, plugins via Extism/WASM. Drop Python, drop bash, drop JavaScript.

**Constraint:** TDD — Rust tests before implementation.
**Constraint:** Feature parity — every MCP tool, CLI command, hook, and plugin must work identically.
**Constraint:** Single binary output — `crux` is one executable that does everything.
**Rule:** Two consecutive clean audit passes = convergence.

## What Gets Rewritten

| Current | Language | Lines | Rust Target |
|---------|----------|-------|-------------|
| `scripts/lib/` (38 modules) | Python | ~6,000 | `src/lib/` Rust modules |
| `scripts/lib/crux_mcp_server.py` (56 tools) | Python | ~700 | `src/server.rs` via rmcp |
| `scripts/lib/crux_mcp_handlers.py` | Python | ~900 | `src/handlers/` modules |
| `scripts/lib/impact/` (4 modules) | Python | ~500 | `src/impact/` modules |
| `bin/crux` (CLI) | Bash | ~600 | `src/cli/` via clap |
| `plugins/` (7 plugins) | JavaScript | ~1,200 | WASM plugins or compiled-in |
| `tools/` (9 tools) | JavaScript | ~800 | Compiled into MCP server |
| `scripts/lib/crux_hooks.py` | Python | ~800 | `src/hooks.rs` |
| `setup.sh` | Bash | ~1,500 | `crux setup` subcommand |
| Tests (1537+) | Python/JS/Bash | ~8,000 | Rust `#[test]` + integration |

**Total current: ~15,000 lines across Python/Bash/JS → single Rust crate.**

## Architecture

```
crux (single binary)
├── src/
│   ├── main.rs              # Entry: CLI dispatch or MCP server mode
│   ├── cli/                  # clap subcommands (status, switch, health, etc.)
│   │   ├── mod.rs
│   │   ├── status.rs
│   │   ├── switch.rs
│   │   ├── setup.rs
│   │   └── ...
│   ├── server.rs             # rmcp MCP server (56 tools)
│   ├── handlers/             # Pure handler functions (one per domain)
│   │   ├── mod.rs
│   │   ├── session.rs        # session state, handoff, restore
│   │   ├── knowledge.rs      # lookup, promote, memory
│   │   ├── safety.rs         # pipeline, TDD gate, security audit
│   │   ├── impact.rs         # analyze_impact, AST, git signals
│   │   ├── git.rs            # git context, diff, risk, commit suggest
│   │   ├── index.rs          # codebase indexing, search
│   │   ├── bip.rs            # build-in-public pipeline
│   │   ├── tools.rs          # tool switching, recipes, MCP registry
│   │   ├── design.rs         # design validation, contrast, WCAG
│   │   ├── models.rs         # model tiers, routing, quality
│   │   └── diagnostics.rs    # health, status, digest, processors
│   ├── hooks.rs              # PostToolUse, SessionStart, Stop, correction detection
│   ├── session.rs            # SessionState, auto_handoff, save/load
│   ├── paths.rs              # Path resolution (.crux/, ~/.crux/)
│   ├── init.rs               # init_project, init_user
│   ├── sync.rs               # Tool-specific config generation
│   ├── recipes.rs            # ToolRecipe for 6 tools
│   ├── security.rs           # Path validation, sanitization, atomic writes
│   ├── memory.rs             # MemoryEntry, save/load/search/forget
│   ├── registry.rs           # External MCP server registry
│   └── plugins/              # WASM plugin system (Extism)
│       ├── mod.rs
│       └── loader.rs
├── modes/                    # 24 mode .md files (unchanged, loaded at runtime)
├── Cargo.toml
├── build.rs                  # Embed modes/ at compile time (optional)
└── tests/
    ├── integration/          # End-to-end MCP protocol tests
    └── ...                   # Unit tests inline via #[cfg(test)]
```

### Key Dependencies (Cargo.toml)

```toml
[dependencies]
rmcp = "0.16"              # MCP server SDK
tokio = { version = "1", features = ["full"] }  # Async runtime
clap = { version = "4", features = ["derive"] }  # CLI parsing
serde = { version = "1", features = ["derive"] }  # Serialization
serde_json = "1"           # JSON handling
schemars = "0.8"           # JSON Schema generation for MCP tools
chrono = "0.4"             # Timestamps
uuid = { version = "1", features = ["v4"] }  # Memory entry IDs
walkdir = "2"              # Directory traversal
grep-regex = "0.1"         # ripgrep's regex for keyword search
syn = "2"                  # Python AST → Rust syn for code analysis (optional)
tree-sitter = "0.25"       # Multi-language AST parsing (Python, TS, Elixir, Rust)
tree-sitter-python = "0.23"
tree-sitter-typescript = "0.23"
tree-sitter-javascript = "0.23"
extism = "1"               # WASM plugin runtime (optional, for Phase 8)
```

### Binary Modes

```
crux                     # No args → show help
crux status              # CLI mode: show session state
crux switch <tool>       # CLI mode: switch tools
crux mcp start           # MCP server mode: stdio transport
crux setup               # Setup mode: interactive installer
crux health              # CLI mode: health checks
crux impact "prompt"     # CLI mode: analyze_impact
crux knowledge "query"   # CLI mode: search knowledge
...
```

---

## Phase 1: Project Scaffold + Core Types

**Purpose:** Set up the Rust workspace, define all core data types, get a compiling binary that does nothing yet.

### Checklist — Phase 1

- [ ] 1.1 `cargo init crux` with workspace layout
- [ ] 1.2 Define `SessionState` struct with serde derive (mirrors Python dataclass)
- [ ] 1.3 Define `MemoryEntry` struct
- [ ] 1.4 Define `ServerConfig` struct (MCP registry)
- [ ] 1.5 Define `ToolRecipe` struct (6 tools)
- [ ] 1.6 Define `RankedFile` struct (impact analysis)
- [ ] 1.7 `paths.rs` — `crux_dir()`, `home_dir()`, `project_dir()` resolution
- [ ] 1.8 `security.rs` — path validation, safe joins, atomic writes
- [ ] 1.9 `init.rs` — `init_project()`, `init_user()` creating .crux/ structure
- [ ] 1.10 Tests for all types (serialization roundtrip, path resolution, init idempotency)
- [ ] 1.11 `cargo build` produces a binary, `cargo test` passes

---

## Phase 2: Session Management

**Purpose:** Session state persistence — the bridge between tools.

### Checklist — Phase 2

- [ ] 2.1 `session.rs` — `save_session()`, `load_session()`, `update_session()`
- [ ] 2.2 `auto_handoff()` — generate handoff from accumulated state
- [ ] 2.3 `write_handoff()`, `read_handoff()` — handoff file I/O
- [ ] 2.4 `archive_session()` — move to history/
- [ ] 2.5 Decision filtering — skip garbage (heredoc captures, >300 char)
- [ ] 2.6 File deduplication — by basename, last N
- [ ] 2.7 Tests for all operations including edge cases

---

## Phase 3: Knowledge + Memory

**Purpose:** Knowledge lookup, memory persistence, correction logging.

### Checklist — Phase 3

- [ ] 3.1 `knowledge.rs` — `lookup_knowledge()` with scope search (mode → project → user → shared)
- [ ] 3.2 `knowledge.rs` — `promote_knowledge()` project → user
- [ ] 3.3 `memory.rs` — `save_memory()`, `load_memories()`, `search_memories()`, `forget_memory()`
- [ ] 3.4 Memory deduplication and confidence scoring
- [ ] 3.5 Correction logging to JSONL
- [ ] 3.6 Interaction logging to JSONL
- [ ] 3.7 Tests

---

## Phase 4: Impact Analysis

**Purpose:** File relevance ranking — git signals, keyword grep, AST parsing.

### Checklist — Phase 4

- [ ] 4.1 `impact/git.rs` — `churn()`, `recency()`, `cochange()` via `Command::new("git")`
- [ ] 4.2 `impact/keywords.rs` — `extract_keywords()`, `grep_matches()` (use grep-regex or walkdir + contains)
- [ ] 4.3 `impact/ast.rs` — `parse_imports()`, `parse_definitions()` via tree-sitter (multi-language: Python, TS, JS, Elixir, Rust)
- [ ] 4.4 `impact/scorer.rs` — `rank_files()` with 5-dimension weighted scoring
- [ ] 4.5 Skip vendored dirs (node_modules, .venv, etc.)
- [ ] 4.6 Performance target: <2s on 10k file repos
- [ ] 4.7 Tests with fixture repos (created in temp dirs)

---

## Phase 5: Codebase Indexing + Git Context

**Purpose:** Persistent index and version history context.

### Checklist — Phase 5

- [ ] 5.1 `index.rs` — `build_catalog()`, `detect_language()`, `extract_symbols()` (multi-language via tree-sitter)
- [ ] 5.2 `index.rs` — `search_index()` with ranked results
- [ ] 5.3 `index.rs` — `save_index()`, `load_index()` to .crux/index/
- [ ] 5.4 Incremental update — only re-parse files with changed mtime
- [ ] 5.5 `git.rs` — `current_diff()`, `file_history()`, `branch_context()`, `suggest_commit()`, `risky_files()`
- [ ] 5.6 Tests

---

## Phase 6: Safety Pipeline

**Purpose:** 7-gate safety enforcement.

### Checklist — Phase 6

- [ ] 6.1 `safety/preflight.rs` — shebang, risk header, pipefail, path containment validation
- [ ] 6.2 `safety/tdd.rs` — TDD gate phase tracking (plan → red → green → complete)
- [ ] 6.3 `safety/audit.rs` — recursive security audit loop with CWE/OWASP classification
- [ ] 6.4 `safety/pipeline.rs` — gate activation per mode/risk level
- [ ] 6.5 `safety/design.rs` — WCAG contrast check, touch targets
- [ ] 6.6 LLM audit backends — Ollama, Anthropic, OpenAI HTTP clients for gates 4-5
- [ ] 6.7 Tests for each gate

---

## Phase 7: MCP Server (rmcp)

**Purpose:** The heart — 56 tools exposed via MCP protocol.

### Checklist — Phase 7

- [ ] 7.1 `server.rs` — rmcp `FastMCP` equivalent with `#[tool_router]`
- [ ] 7.2 Register all 56 tools with `#[tool]` macros delegating to handler modules
- [ ] 7.3 `_project()` and `_home()` from env vars with startup cwd fallback
- [ ] 7.4 MCP instructions text (always-on session state, restore_context on start)
- [ ] 7.5 Session adoption detection in `restore_context` (scan ~/.claude/projects/)
- [ ] 7.6 Stdio transport via `tokio::io::{stdin, stdout}`
- [ ] 7.7 Tests — tool registration, handler delegation, protocol compliance

---

## Phase 8: CLI (clap)

**Purpose:** Terminal interface — all subcommands.

### Checklist — Phase 8

- [ ] 8.1 `cli/mod.rs` — clap derive enum for all subcommands
- [ ] 8.2 `crux status` — session state + health checks
- [ ] 8.3 `crux switch <tool>` — auto_handoff + recipe-based config generation
- [ ] 8.4 `crux health` — static + liveness checks
- [ ] 8.5 `crux knowledge <query>` — search and format results
- [ ] 8.6 `crux impact "<prompt>"` — rank files, formatted output
- [ ] 8.7 `crux mcp start` — launch MCP server on stdio
- [ ] 8.8 `crux mcp status` / `crux mcp tools` — list registered tools
- [ ] 8.9 `crux digest` — show daily digest
- [ ] 8.10 `crux setup` — interactive installer (replaces setup.sh)
- [ ] 8.11 `crux adopt` — mid-session onboarding (replaces crux_adopt.py)
- [ ] 8.12 `crux update` / `crux doctor` / `crux version`
- [ ] 8.13 Colored output, table formatting
- [ ] 8.14 Tests for each subcommand

---

## Phase 9: Tool Switching + Config Sync

**Purpose:** Tool-agnostic config generation.

### Checklist — Phase 9

- [ ] 9.1 `recipes.rs` — 6 ToolRecipes (Claude Code, CruxCLI, OpenCode, Cursor, Windsurf, Zed)
- [ ] 9.2 `sync.rs` — generate .mcp.json, .cruxcli/cruxcli.jsonc, .cursor/mcp.json, etc.
- [ ] 9.3 `sync.rs` — sync_claude_code (hooks, agents, context), sync_opencode (symlinks, modes)
- [ ] 9.4 `registry.rs` — external MCP server registry CRUD
- [ ] 9.5 Tests for all 6 tool configs

---

## Phase 10: Hooks + Correction Detection

**Purpose:** Infrastructure enforcement — auto-capture without LLM cooperation.

### Checklist — Phase 10

- [ ] 10.1 `hooks.rs` — SessionStart, PostToolUse, UserPromptSubmit, Stop handlers
- [ ] 10.2 PostToolUse: auto-capture files from Edit/Write, decisions from git commits
- [ ] 10.3 Stop: auto_handoff on every session end
- [ ] 10.4 UserPromptSubmit: 10 regex correction patterns
- [ ] 10.5 Commit message extraction (prefer output over command, skip heredocs)
- [ ] 10.6 BIP event detection and counter increment
- [ ] 10.7 Hook settings generation for Claude Code (.claude/settings.local.json)
- [ ] 10.8 Tests

---

## Phase 11: Build-in-Public Pipeline

**Purpose:** Typefully integration, trigger evaluation, content gathering.

### Checklist — Phase 11

- [ ] 11.1 `bip/config.rs` — BIPConfig, BIPState
- [ ] 11.2 `bip/triggers.rs` — evaluate_triggers (commit/token/interaction thresholds, high-signal events)
- [ ] 11.3 `bip/gather.rs` — gather_content (git, corrections, knowledge, session)
- [ ] 11.4 `bip/typefully.rs` — Typefully REST API client (reqwest)
- [ ] 11.5 MCP tools: bip_generate, bip_approve, bip_status, bip_get_analytics
- [ ] 11.6 Tests

---

## Phase 12: Background Processors + Cross-Project

**Purpose:** Threshold-triggered continuous learning.

### Checklist — Phase 12

- [ ] 12.1 `processors.rs` — correction extraction, clustering, digest generation, mode audit
- [ ] 12.2 `cross_project.rs` — project registration, cross-project digest
- [ ] 12.3 Threshold checking (corrections queue size, interaction count)
- [ ] 12.4 Tests

---

## Phase 13: Plugins (WASM via Extism)

**Purpose:** Replace JS plugins with sandboxed WASM.

### Checklist — Phase 13

- [ ] 13.1 `plugins/loader.rs` — Extism runtime, load .wasm files from .crux/plugins/
- [ ] 13.2 Plugin interface: on_tool_result, on_user_message, on_session_start, on_session_end
- [ ] 13.3 Sandboxed execution — plugins cannot access filesystem directly
- [ ] 13.4 Port session-logger, correction-detector, think-router, token-budget as WASM plugins (or compile in as Rust modules)
- [ ] 13.5 Tests

---

## Phase 14: Setup + Distribution

**Purpose:** Replace setup.sh, produce distributable binaries.

### Checklist — Phase 14

- [ ] 14.1 `crux setup` — interactive installer in Rust (tool selection, MCP config, mode symlinks)
- [ ] 14.2 `crux update` — self-update mechanism
- [ ] 14.3 Cross-compilation CI: macOS ARM64, macOS x86_64, Linux x86_64, Linux ARM64
- [ ] 14.4 GitHub Releases with prebuilt binaries
- [ ] 14.5 Install script: `curl -fsSL https://runcrux.io/install.sh | sh`
- [ ] 14.6 Homebrew formula (optional)
- [ ] 14.7 Tests for setup flow

---

## Phase 15: Feature Parity Verification

**Purpose:** Verify every Python/Bash/JS feature works identically in Rust.

### Checklist — Phase 15

- [ ] 15.1 All 56 MCP tools callable and return identical JSON shapes
- [ ] 15.2 All CLI subcommands produce identical output
- [ ] 15.3 Session state roundtrip: Python writes → Rust reads → Python reads (backward compatible)
- [ ] 15.4 Tool switching: Rust binary generates correct configs for all 6 tools
- [ ] 15.5 Hook output: identical JSON for Claude Code hooks
- [ ] 15.6 Performance: MCP startup <5ms, analyze_impact <2s on 10k files
- [ ] 15.7 Binary size: <20MB
- [ ] 15.8 Run against existing test expectations (port key assertions)

---

## Phase 16: Cleanup + Drop Python

**Purpose:** Remove all Python/Bash/JS code. Single language.

### Checklist — Phase 16

- [ ] 16.1 Remove `scripts/lib/` (all Python modules)
- [ ] 16.2 Remove `bin/crux` (bash CLI)
- [ ] 16.3 Remove `plugins/` (JS plugins)
- [ ] 16.4 Remove `tools/` (JS tools)
- [ ] 16.5 Remove `setup.sh`
- [ ] 16.6 Remove `requirements.txt`, `pyproject.toml`, `package.json`
- [ ] 16.7 Remove `.venv/` dependency
- [ ] 16.8 Update README.md: installation is now `curl | sh` or download binary
- [ ] 16.9 Update all documentation to reflect Rust architecture
- [ ] 16.10 Update CLAUDE.md
- [ ] 16.11 Final test suite passes
- [ ] 16.12 Deploy to GitHub Releases

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| tree-sitter bindings complexity | AST parsing harder than Python ast module | tree-sitter is mature, well-documented, used by Zed/Helix/Neovim |
| Async MCP protocol complexity | rmcp requires tokio async | rmcp examples are straightforward, stdio transport is simple |
| JSON schema generation | 56 tools need schema | schemars auto-derives from Rust structs, less work than Python |
| Backward compatibility | Existing .crux/ files must still work | Serde reads JSON/JSONL the same way Python json module does |
| Compile time for 56-tool server | Slow iteration | Workspace layout with library crate enables incremental builds |
| Regex correction patterns | 10 Python regexes → Rust regex | Direct port, Rust regex crate is API-compatible |

## Convergence Criteria

- Single `crux` binary with all functionality
- All 56 MCP tools working via rmcp
- All CLI subcommands working via clap
- Session state, knowledge, memory, corrections — all backward compatible with existing .crux/ files
- Cross-compile to macOS ARM64 + Linux x86_64
- Binary size <20MB
- MCP startup <5ms
- Two consecutive clean audit passes
