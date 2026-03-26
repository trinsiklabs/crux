# BUILD_PLAN_011: Codebase Indexing — Persistent Semantic Code Understanding

**Created:** 2026-03-26
**Status:** COMPLETE — crux_index.py with catalog, symbol extraction (Python/TS/JS/Elixir), search, persistence. MCP tools: search_code, index_codebase. 28 tests, 100% coverage.
**Priority:** SHOULD-CLOSE
**Competitive Gap:** Cursor indexes entire codebases for semantic search and chat. Crux relies on grep (text matching) and git history — no persistent index of code structure.
**Goal:** Build a persistent codebase index in `.crux/index/` that maps files, symbols, imports, and documentation. Updated incrementally on file changes. Powers fast semantic search and context selection.

**Constraint:** TDD, 100% coverage on new code.
**Constraint:** stdlib + ast module only — no embedding models or vector databases.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Cursor's codebase indexing enables "chat with your codebase" — ask questions about code and get answers from the full project. Crux's current tools (grep, git churn) find text matches but don't understand code structure. A persistent index bridges this gap without requiring embeddings or ML.

## Architecture

```
.crux/index/
├── files.json          # file → {mtime, size, language, line_count}
├── symbols.json        # file → [{name, type, line, scope}]
├── imports.json        # file → [imported_modules]
├── docstrings.json     # file → [{function, docstring}]
└── metadata.json       # index version, last_full_build, stats

Incremental updates:
  On file change (mtime differs) → re-parse that file only
  On new file → add to index
  On deleted file → remove from index
```

---

## Phase 1: File Catalog

- [ ] 1.1 Create `scripts/lib/crux_index.py`
- [ ] 1.2 `build_catalog(root)` → scan all source files, record mtime/size/language/lines
- [ ] 1.3 `detect_language(filepath)` → language from extension (.py, .ts, .ex, etc.)
- [ ] 1.4 Skip vendored dirs (node_modules, .venv, vendor, dist)
- [ ] 1.5 Incremental: only re-scan files with changed mtime
- [ ] 1.6 Tests for catalog build and incremental update

## Phase 2: Symbol Extraction

- [ ] 2.1 `extract_symbols(filepath, language)` → `list[Symbol]` — functions, classes, methods, constants
- [ ] 2.2 Python: use `ast` module (same as BUILD_PLAN_008)
- [ ] 2.3 TypeScript/JavaScript: regex-based extraction (function/class/const/export patterns)
- [ ] 2.4 Elixir: regex-based extraction (def/defp/defmodule patterns)
- [ ] 2.5 Tests for each language

## Phase 3: Search

- [ ] 3.1 `search_index(query, root)` → ranked results with file, symbol, line number
- [ ] 3.2 Match against: symbol names, docstrings, file paths
- [ ] 3.3 Rank by: exact match > prefix match > substring match > file proximity
- [ ] 3.4 MCP tool: `search_code(query)` — search the codebase index
- [ ] 3.5 Tests for search ranking

## Phase 4: MCP Integration

- [ ] 4.1 MCP tool: `index_codebase()` — build/refresh the index
- [ ] 4.2 MCP tool: `index_stats()` — show index size, file count, symbol count, last update
- [ ] 4.3 Auto-index on restore_context() if index is stale (>1 hour)
- [ ] 4.4 Integrate with analyze_impact — use index for faster symbol matching
- [ ] 4.5 Tests for MCP tools and auto-refresh

---

## Convergence Criteria

- Persistent index in .crux/index/ with files, symbols, imports, docstrings
- Incremental updates (only re-parse changed files)
- Symbol extraction for Python, TypeScript, Elixir
- search_code MCP tool for semantic search
- <5s full index build on 10k file repos
- Two consecutive clean audit passes
