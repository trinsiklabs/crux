---
title: Crux Development Guide
last_updated: 2026-03-24
source: Normalized from CLAUDE.md and DEVELOPMENT_PATTERNS_CRUX.md
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Development Guide

## Prerequisites

- Python 3.10+ (macOS: Homebrew, Linux: system or pyenv)
- Node.js 18+ (for plugins, tools, website)
- Git

## Setup

```bash
git clone https://github.com/trinsiklabs/crux.git
cd crux
chmod +x setup.sh
./setup.sh
```

Setup will ask which tool you use (Claude Code / OpenCode / Both) and configure accordingly. For Claude Code, it creates a `.venv/`, installs dependencies, generates MCP config, and verifies the server loads.

## Running Tests

```bash
# Full suite with coverage enforcement
python3 -m pytest tests/ --tb=short --cov=scripts/lib --cov-fail-under=100

# Single module
python3 -m pytest tests/test_crux_hooks.py -v

# Impact analysis
python3 -m pytest tests/impact/ --cov=scripts.lib.impact

# JavaScript plugins
node --test plugins/*.test.js

# Bash tests
bats tests/*.bats
```

100% coverage is enforced. PRs that drop below 100% will not merge.

## Development Workflow

1. TDD: write tests before implementation
2. Run tests: verify they fail (red)
3. Implement: write the code
4. Run tests: verify they pass (green)
5. Coverage: verify 100% with `--cov-report=term-missing`

## Code Conventions

### Python (scripts/lib/)

- Type hints on all functions
- Context managers for resources (files, DB connections, locks)
- Security-first: validate inputs, sanitize paths, escape user data
- Handler functions separate from MCP decorators for testability
- All filesystem modifications through scripts (scripts-first principle)

### Adding MCP Tools

1. Write handler function in the appropriate module (or `crux_mcp_handlers.py`)
2. Write tests (100% coverage required)
3. Add `@mcp.tool()` wrapper in `crux_mcp_server.py`
4. Update `tests/test_mcp_server_registration.py` expected tool set
5. Update `docs/API.md` with the new tool

### Adding Modes

1. Copy `modes/TEMPLATE.txt` to `modes/<name>.md`
2. Add YAML frontmatter (temperature, think, tool_access)
3. Follow research conventions: positive framing, 150-200 words, critical rules at start/end
4. Add to the modes table in `CLAUDE.md`

## Architecture Patterns

### MCP Server as Universal Adapter

All Crux logic is exposed via the MCP server. Handler logic in separate files (pure functions, no MCP deps). Server file is thin wiring only. New capabilities go into handlers first, then get wired into the server.

### Three-Tier Scope

- **Project** (`.crux/`): knowledge, corrections, sessions for one project
- **User** (`~/.crux/`): cross-project knowledge, modes, analytics
- **Public** (this repo): canonical modes, tools, scripts

### Tool Hierarchy

Prefer higher tiers: LSP (0) > Custom Tools (1) > MCP (2) > Library Scripts (3) > New Scripts (4) > Raw Bash (5). Tier 5 should trend toward zero.

## Contribution Workflow

This repo is owned by `trinsiklabs`. Edits come as PRs from the `tecto` fork:

```bash
git checkout -b feature/whatever
# make changes
git push -u origin feature/whatever
gh pr create --repo trinsiklabs/crux --title "Title" --body "Description"
```

See `CONTRIBUTING.md` for what types of contributions are accepted.

## Key Files

| File | What to Know |
|------|-------------|
| `scripts/lib/crux_mcp_server.py` | 43 tools — add new tools here |
| `scripts/lib/crux_mcp_handlers.py` | Handler functions — business logic here |
| `scripts/lib/crux_hooks.py` | Claude Code hook handlers |
| `scripts/lib/crux_paths.py` | Path resolution — `get_crux_repo()`, `get_crux_python()` |
| `modes/*.md` | Mode definitions with YAML frontmatter |
| `pyproject.toml` | Test and coverage config |
| `.mcp.json` | MCP server config for Claude Code |
