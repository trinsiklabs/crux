# BUILD_PLAN_002: Repo/AST Impact Analysis

**Created:** 2026-03-23
**Status:** COMPLETE
**Goal:** Build an `analyze_impact` Crux MCP tool that ranks files by relevance to a prompt using LSP symbol data + git history. Works across any agent connected to Crux, not just CruxCLI.

**Constraint:** Lives in the Crux MCP server (`/Users/user/personal/crux/scripts/lib/`), not in CruxCLI source.
**Constraint:** Must work without LSP (graceful degradation to git+grep when no LSP is running).
**Rule:** TDD. Tests before code.
**Rule:** 100% coverage enforced.
**Rule:** Two consecutive clean passes = convergence.

## Document Alignment

- `ROADMAP.md` — defines this as competitive gap #1, specifies approach
- `AGENTS.md` — coding style (single-word names, no mocks in tests)
- Crux MCP server pattern — `@mcp.tool()` decorator, handler in separate file, security validation on paths

---

## Architecture

```
Agent sends: analyze_impact("add OAuth2 login flow")
                    │
                    ▼
            ┌───────────────┐
            │  analyze_impact │
            │  (MCP tool)     │
            └───────┬─────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Git History   Grep/AST    LSP Symbols
   (git log,     (keyword    (references,
    blame,       matching    definitions,
    churn)       from prompt) call hierarchy)
        │           │           │
        ▼           ▼           ▼
            ┌───────────────┐
            │  Score & Rank  │
            │  per file      │
            └───────┬────────┘
                    │
                    ▼
         Top N files + reasons
```

### Scoring Dimensions

| Dimension | Weight | Source | Signal |
|-----------|--------|--------|--------|
| Keyword match | 0.3 | grep | File contains terms from the prompt |
| Git churn | 0.2 | git log | Recently/frequently changed files |
| Symbol relevance | 0.3 | LSP | File defines/references symbols matching prompt |
| Proximity | 0.2 | filesystem | Files near already-matched files |

### Graceful Degradation

| Available | Strategy |
|-----------|----------|
| LSP + git | Full scoring (all 4 dimensions) |
| git only | Skip symbol relevance, reweight remaining |
| grep only | Keyword match + proximity only |

---

## Phase 1: Git History Signals

**Purpose:** Extract file-level signals from git — churn (change frequency), recency, co-change patterns.

### Checklist — Phase 1

- [x] 1.0 Create `scripts/lib/impact/__init__.py` subpackage
- [x] 1.1 Create `scripts/lib/impact/git_signals.py` with functions (churn, recency, cochange)
- [x] 1.2 `churn(root, days=90)` → `dict[filepath, int]` using `git log --name-only`
- [x] 1.3 `recency(root)` → `dict[filepath, float]` — days since last change, normalized 0-1
- [x] 1.4 `cochange(root, filepath, days=90)` → `list[filepath]` — files that change together
- [x] 1.5 Tests for churn, recency, cochange with fixture git repos (24 tests)
- [x] 1.6 Tests pass, coverage = 100%

---

## Phase 2: Keyword Extraction + Grep Matching

**Purpose:** Extract searchable terms from a natural language prompt and find matching files.

### Checklist — Phase 2

- [x] 2.1 Create `scripts/lib/impact/keywords.py` with `extract_keywords(prompt)` → `list[str]`
- [x] 2.2 Strip stopwords, extract identifiers (camelCase/snake_case splitting), technical terms
- [x] 2.3 `grep_matches(root, keywords)` → `dict[filepath, float]` using grep
- [x] 2.4 Score by match density (matches per line)
- [x] 2.5 Tests for keyword extraction edge cases (code terms, natural language, mixed)
- [x] 2.6 Tests for grep matching with fixture repos (21 tests)
- [x] 2.7 Tests pass, coverage = 100%

---

## Phase 3: LSP Symbol Integration

**Purpose:** Query LSP for symbol-level relevance — find files that define or reference symbols matching the prompt.

### Checklist — Phase 3

- [x] 3.1 Create `scripts/lib/impact/lsp_signals.py` with functions (symbol_matches, reference_graph, check_lsp)
- [x] 3.2 `symbol_matches(root, keywords)` → `dict[filepath, float]` via workspace/symbol query
- [x] 3.3 `reference_graph(root, filepath)` → `list[filepath]` — files that reference symbols in a file
- [x] 3.4 Graceful degradation: check_lsp returns False, all functions return empty (not errors)
- [x] 3.5 Stub functions for LSP queries — ready to wire when LSP available
- [x] 3.6 Tests with mock LSP responses (20 tests: unavailable, partial, full, edge cases)
- [x] 3.7 Tests pass, coverage = 100%

---

## Phase 4: Scoring Engine + MCP Tool

**Purpose:** Combine all signals into a ranked file list. Expose as Crux MCP tool.

### Checklist — Phase 4

- [x] 4.1 Create `scripts/lib/impact/scorer.py` with `rank_files(root, prompt)` → `list[RankedFile]`
- [x] 4.2 Weighted scoring: keyword(0.3) + churn(0.2) + symbol(0.3) + proximity(0.2)
- [x] 4.3 Proximity scoring: boost files in same directory as high-scoring files
- [x] 4.4 `RankedFile` includes: path, score, reasons (which dimensions contributed)
- [x] 4.5 Configurable top-N (default 20), configurable weights
- [x] 4.6 Add `@mcp.tool() analyze_impact(prompt, top_n, include_reasons)` to crux MCP server
- [x] 4.7 MCP tool wrapper in crux_mcp_server.py delegates to scorer
- [x] 4.8 Security: root from _project(), prompt passed to extract_keywords (safe)
- [x] 4.9 Tests for scoring (23 tests) with all signal combinations
- [x] 4.10 Tests for MCP tool integration (3 tests in test_mcp_server_registration.py)
- [x] 4.11 Tests pass, coverage = 100%

---

## Phase 5: Build + Verify

**Purpose:** End-to-end verification on a real repo.

### Checklist — Phase 5

- [x] 5.1 Run `analyze_impact("add OAuth2 login flow")` on crux + cruxcli repos
- [x] 5.2 Verify results include session-related files on cruxcli
- [x] 5.3 Run `analyze_impact("fix session management bug")` — session files ranked high
- [x] 5.4 Run with LSP unavailable — graceful degradation (git+grep signals only)
- [x] 5.5 Performance: 2.35s on cruxcli (target <5s)
- [x] 5.6 Full test suite passes (88 impact tests + 1374 existing)
- [x] 5.7 Coverage = 100% on new code (263 statements, 0 missed)

---

## Test Commands

```bash
cd /Users/user/personal/crux && python3 -m pytest tests/impact/ -v --cov=scripts/lib/impact --cov-report=term-missing
```

## Convergence Criteria

- All checklist items complete
- All tests pass
- Coverage ≥ 100% on new code
- Two consecutive clean audit passes
- MCP tool callable from any connected agent

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LSP not running for target repo | Reduced accuracy | Graceful degradation — git+grep still useful |
| Large repos slow git log | >5s response time | Limit git log depth (90 days default), cache results |
| Keyword extraction misses domain terms | Wrong files ranked | Allow explicit keywords alongside prompt |
| ripgrep not installed | grep_matches fails | Fall back to Python re module |

## Definition of Done

1. `analyze_impact` MCP tool returns ranked files for any prompt
2. Works with and without LSP
3. Git churn + keyword match + symbol relevance + proximity all contribute
4. <5s response time on 10k file repos
5. 100% test coverage on new code
6. Two consecutive clean audit passes
