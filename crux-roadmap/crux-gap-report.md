# Crux Gap Report

> **Superseded by GAPS.md as of 2026-03-24.** This document reflects the state on 2026-03-06. Current state: 1374+ tests, 43 MCP tools, 24 modes. See GAPS.md for the live gap tracker.

**Generated:** 2026-03-06
**Codebase State:** 904 tests passing, 25 MCP tools, 23 modes, 7-gate pipeline

---

## Critical (Core Functionality)

### 1. Gates 4-5: LLM Adversarial Audit

**Location:** `tools/run_script.js` lines 92-98
**Status:** Stubbed with placeholder comments

Gate 4 (8B adversarial audit) and Gate 5 (32B second-opinion audit) are hardcoded to `{ skipped: true, reason: 'LLM integration pending' }`. Need actual Ollama REST API calls to:

- Spin up an 8B model (e.g., Qwen:7B) to review scripts written by the main model (Gate 4, medium/high risk)
- Have the main 32B model re-review its own script for structural issues (Gate 5, high risk only)

**Blocked on:** Live Ollama instance with specific model availability.

### 2. Background Processor (Threshold-Triggered)

**Location:** No file exists. Described in CLAUDE.md and architecture spec.
**Status:** Not built

The core engine that ties continuous learning together. Should wake on data thresholds (queue size, interaction count, token usage) — not cron, not session events — and automatically run:

- Correction extraction and clustering (`extract_corrections.py`)
- Knowledge entry generation from correction clusters
- Daily digest generation (`generate_digest.py`)
- Mode effectiveness scoring (`audit_modes.py`)
- Tool usage analysis and promotion candidates

**Current behavior:** All of the above works but only when manually invoked. Learning is not truly continuous.

### 3. Cross-Project Aggregation

**Location:** `scripts/lib/promote_knowledge.py` handles project→user promotion only.
**Status:** Not built

Missing:
- User-level analytics digest that spans all projects
- Cross-project correction pattern detection (same mistake in multiple projects)
- Aggregated mode effectiveness scoring across projects
- User-scope digest generation (currently only project-scope)

---

## Medium (Feature Gaps)

### 4. `manage_models.js` Pull Action

**Location:** `tools/manage_models.js` line 88
**Status:** Placeholder

The `pull` action in the model management tool is stubbed. Needs Ollama REST API integration (`POST /api/pull`) to actually download models.

### 5. Figma API Backend

**Location:** Not built. Design modes reference Figma but no API integration exists.
**Status:** Not built

Design modes (`design-ui`, `design-system`, etc.) are fully implemented with prompts, validation, and handoff protocols. But there's no:
- Figma REST API client for importing design tokens, components, or specs
- Image generation backend for design mockups
- Automated design-to-code asset pipeline

### 6. Cursor/Windsurf Adapters

**Location:** `scripts/lib/crux_sync.py` has adapters for OpenCode and Claude Code only.
**Status:** Not built

The MCP server provides universal access for any MCP-compatible tool, but there are no tool-specific sync adapters (config generation, symlinks, mode routing) for Cursor, Windsurf, or other editors. These tools can use Crux via MCP but don't get the deep integration that OpenCode and Claude Code have.

---

## Low (Organizational / Future)

### 7. Vibe Organizational Layer

**Location:** Spec exists in `crux-roadmap/crux-vibe-platform-spec.md`. No code.
**Status:** Designed, not built

Central knowledge base, multi-organization aggregation, org-wide model orchestration, shared learning across teams. This is a significant architecture expansion beyond single-user scope.

---

## What's Fully Built

Everything not listed above is implemented and tested:

- **MCP Server:** 25 tools, all with handler functions and tests
- **Safety Pipeline:** Gate 1 (preflight), Gate 2 (TDD), Gate 3 (security audit), Gate 6 (human approval), Gate 7 (dry run) — all real implementations
- **Continuous Learning:** Correction detection (real-time), session logging, correction extraction/clustering, knowledge promotion (3-tier), daily digest generation, model evaluation, mode auditing
- **Tool Adapters:** OpenCode (per-mode routing, symlinks, AGENTS.md merge), Claude Code (4 hooks, context injection), MCP server (universal)
- **CLI:** `crux status` (runtime status + 13 health/liveness checks), `crux setup`, `crux update`, `crux doctor`, `crux version`
- **Plugins:** 6 OpenCode JS plugins (session-logger, think-router, correction-detector, compaction-hook, token-budget, tool-enforcer)
- **Tools:** 9 OpenCode JS tools (run_script, promote_script, list_scripts, project_context, lookup_knowledge, suggest_handoff, manage_models, marketing_generate, marketing_update_state)
- **Hooks:** 4 Claude Code hooks (SessionStart, PostToolUse, UserPromptSubmit, Stop) with conversation logging
- **Modes:** 23 modes with YAML frontmatter, all targeting 150-200 words
- **Design System:** 5 design modes, design validation (WCAG/contrast/touch targets), design-to-code handoff, cross-domain knowledge flows
- **TDD Gate:** Full phase tracking (plan→red→green→complete), 4 enforcement levels, coverage tracking
- **Security Audit:** 7 categories, convergence detection, CWE/OWASP classification
- **Session Management:** State persistence, crash recovery, handoff context, freshness checks
- **Test Suite:** 904 tests across Python (pytest), JavaScript (node:test), and Bash (bats)
- **Documentation:** 8 doc files covering architecture, modes, safety, learning, setup, tools, scripts
