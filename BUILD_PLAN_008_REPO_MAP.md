# BUILD_PLAN_008: Repo Map — AST-Based File Ranking

**Created:** 2026-03-26
**Status:** COMPLETE
**Priority:** SHOULD-CLOSE
**Competitive Gap:** Aider's repo map proactively selects relevant files using AST analysis. Crux has analyze_impact (git+grep+LSP stubs) but no AST parsing.
**Goal:** Enhance `analyze_impact` with real AST-based symbol extraction — parse import graphs, function definitions, and class hierarchies to rank files by structural relevance to a prompt. No LSP required.

**Constraint:** TDD, 100% coverage on new code.
**Constraint:** stdlib only — use Python's `ast` module, no external parsers.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

analyze_impact currently uses grep (text matching) and git churn. AST analysis adds structural understanding: "this function calls that function" is a stronger signal than "this file contains the word 'auth'." Aider's repo map is their #1 competitive advantage.

## Architecture

```
analyze_impact(prompt)
    │
    ├── git_signals (existing)
    ├── keywords/grep (existing)
    ├── lsp_signals (stubs, future)
    └── ast_signals (NEW)
            │
            ├── parse_imports(file) → list[module]
            ├── parse_definitions(file) → list[name, type]
            ├── build_import_graph(root) → dict[file, imports]
            └── symbol_relevance(keywords, definitions) → scores
```

---

## Phase 1: Python AST Parser

- [ ] 1.1 Create `scripts/lib/impact/ast_signals.py`
- [ ] 1.2 `parse_imports(filepath)` → `list[str]` — extract import targets using `ast.parse`
- [ ] 1.3 `parse_definitions(filepath)` → `list[dict]` — extract function/class/variable names with line numbers
- [ ] 1.4 Handle syntax errors gracefully (return empty, don't crash)
- [ ] 1.5 Tests with fixture Python files

## Phase 2: Import Graph

- [ ] 2.1 `build_import_graph(root, extensions)` → `dict[str, list[str]]` — map each file to its imports
- [ ] 2.2 Resolve relative imports to file paths
- [ ] 2.3 Cache graph (invalidate on file mtime change)
- [ ] 2.4 Walk only source directories (skip node_modules, .venv, etc.)
- [ ] 2.5 Tests with multi-file fixture repos

## Phase 3: Symbol Relevance Scoring

- [ ] 3.1 `symbol_relevance(root, keywords)` → `dict[filepath, float]` — score files by how many of their definitions match keywords
- [ ] 3.2 Boost files that are imported by many other files (hub score)
- [ ] 3.3 Boost files whose imports match keyword-relevant files (transitive relevance)
- [ ] 3.4 Tests for scoring

## Phase 4: Integration with Scorer

- [ ] 4.1 Add `ast` dimension to `scorer.py` alongside keyword, churn, symbol, proximity
- [ ] 4.2 Update DEFAULT_WEIGHTS: keyword(0.25) + churn(0.15) + ast(0.25) + symbol(0.15) + proximity(0.20)
- [ ] 4.3 analyze_impact returns AST-based results when Python files present
- [ ] 4.4 Graceful degradation for non-Python files (fall back to existing dimensions)
- [ ] 4.5 Performance: <5s on 10k file repos
- [ ] 4.6 Tests for integrated scoring

---

## Convergence Criteria

- AST parsing extracts imports and definitions from Python files
- Import graph built from project structure
- Symbol relevance scoring integrated into analyze_impact
- Works alongside existing git+grep signals
- Graceful degradation for non-Python files
- Two consecutive clean audit passes
