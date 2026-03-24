---
title: Crux Testing Strategy
last_updated: 2026-03-24
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Testing Strategy

## Overview

Crux enforces 100% test coverage on all core modules (`scripts/lib/`). Tests are written before code (TDD).

## Test Infrastructure

| Runner | Scope | Files | Count |
|--------|-------|-------|-------|
| pytest | Python modules (`scripts/lib/`) | 41+ test files in `tests/` | ~1300+ |
| node:test | JavaScript plugins (`plugins/`) | 7 test files | ~100+ |
| bats | Bash scripts (`setup.sh`, `bin/crux`) | 8 test files | ~50+ |

## Running Tests

```bash
# Full Python suite with coverage enforcement
python3 -m pytest tests/ --tb=short --cov=scripts/lib --cov-fail-under=100

# Specific module
python3 -m pytest tests/test_crux_hooks.py -v

# Impact analysis only
python3 -m pytest tests/impact/ --cov=scripts.lib.impact --cov-report=term-missing

# JavaScript plugins
node --test plugins/*.test.js

# Bash tests
bats tests/*.bats
```

## Coverage Enforcement

Configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["scripts/lib"]

[tool.coverage.report]
fail_under = 100
```

Every PR must pass `--cov-fail-under=100`. No exceptions.

## Test Patterns

- **Fixture repos:** Tests that need git history create temporary repos with `tmp_path` fixture
- **Environment fixtures:** Tests that need `.crux/` create full environments with `init_user()` and `init_project()`
- **MCP tool tests:** Call wrapper functions directly (no MCP protocol overhead)
- **Security tests:** All paths must be within project dir (PLAN-166), API keys need 0o600 permissions
- **Mock strategy:** Mock external services (Ollama, Typefully, Figma) but use real filesystems and git repos

## Test File Layout

```
tests/
├── test_crux_*.py          # Core module tests (1 file per module)
├── test_mcp_*.py           # MCP server and handler tests
├── impact/                 # Impact analysis tests
│   ├── test_git_signals.py
│   ├── test_keywords.py
│   ├── test_lsp_signals.py
│   └── test_scorer.py
└── *.bats                  # Bash test files
```
