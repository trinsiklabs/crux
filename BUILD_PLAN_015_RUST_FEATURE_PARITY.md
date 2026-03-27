# BUILD_PLAN_015: Complete Rust Feature Parity — Close All 36 Missing Modules

**Created:** 2026-03-27
**Status:** IN PROGRESS
**Goal:** Port every missing Python module to Rust. Zero stubs. Every MCP tool does real work. The Rust binary is the complete replacement — not a partial port.

**Constraint:** TDD — tests before implementation.
**Constraint:** Each phase must compile and pass all tests before moving to next.
**Rule:** Two consecutive clean audit passes = convergence.

## Audit Summary (from Python→Rust gap analysis)

- **PORTED (7 modules):** paths, init, session, hooks, security, memory, preflight
- **STUBBED (11 modules):** partial implementations returning hardcoded/minimal data
- **MISSING (36 modules):** no Rust implementation at all

---

## Phase 1: Hook Runner — Claude Code Hook Execution Engine

**Gap:** crux_hook_runner.py — hooks are configured in .claude/settings.local.json but the Rust binary has no `crux hook` subcommand to execute them.

### Checklist — Phase 1

- [ ] 1.1 Add `crux hook <event> [--json <stdin>]` CLI subcommand
- [ ] 1.2 `SessionStart` handler: load and inject mode prompt + session state + pending tasks
- [ ] 1.3 `PostToolUse` handler: auto-capture files (Edit/Write), decisions (git commit), BIP events
- [ ] 1.4 `UserPromptSubmit` handler: correction detection (10 regex patterns), conversation logging
- [ ] 1.5 `Stop` handler: auto_handoff, update timestamps, TDD compliance check
- [ ] 1.6 JSON stdin parsing (Claude Code sends hook data as JSON on stdin)
- [ ] 1.7 Generate `.claude/settings.local.json` hook config pointing to Rust binary
- [ ] 1.8 Tests for each hook handler

---

## Phase 2: Project Context Generation

**Gap:** update_project_context.py — no auto-generated PROJECT.md from repo structure.

### Checklist — Phase 2

- [ ] 2.1 `generate_project_context(project_dir)` — scan repo: file tree, dependencies, tech stack detection
- [ ] 2.2 Detect tech stack from: Cargo.toml (Rust), package.json (JS/TS), mix.exs (Elixir), pyproject.toml (Python)
- [ ] 2.3 Detect test framework from: tests/ structure, test commands in config
- [ ] 2.4 Write `.crux/context/PROJECT.md` with structured sections
- [ ] 2.5 MCP tool: `get_project_context` reads generated PROJECT.md (currently returns "not found")
- [ ] 2.6 Auto-generate on `crux adopt` and on `restore_context` if stale (>24h)
- [ ] 2.7 Tests

---

## Phase 3: Impact Analysis Completion — AST + Proximity + Symbol

**Gap:** ast_signals.py, lsp_signals.py — scorer only uses keyword + churn (2/5 signals).

### Checklist — Phase 3

- [ ] 3.1 Port `ast_signals.py` to Rust using `tree-sitter` crate (Python, TS, JS, Elixir, Rust parsing)
- [ ] 3.2 `parse_imports(path)`, `parse_definitions(path)`, `build_import_graph(root)`
- [ ] 3.3 `symbol_relevance(root, keywords)` — hub boost for heavily-imported files
- [ ] 3.4 Add proximity scoring to scorer.rs — boost files in same directory as matches
- [ ] 3.5 Update scorer weights: keyword(0.25) + churn(0.15) + ast(0.25) + symbol(0.15) + proximity(0.20)
- [ ] 3.6 Tests with multi-language fixture repos

---

## Phase 4: Codebase Indexing

**Gap:** crux_index.py — no persistent symbol index for fast search.

### Checklist — Phase 4

- [ ] 4.1 `build_catalog(root)` — scan files, record mtime/language/lines/symbols
- [ ] 4.2 Multi-language symbol extraction via tree-sitter
- [ ] 4.3 `search_index(query, root)` — ranked search across file paths + symbol names
- [ ] 4.4 Persistent index in `.crux/index/catalog.json` with incremental updates
- [ ] 4.5 MCP tools: `search_code` does real search (not grep), `index_codebase` builds/refreshes
- [ ] 4.6 Tests

---

## Phase 5: Safety Gates 2-7

**Gap:** crux_tdd_gate.py, crux_security_audit.py, crux_llm_audit.py — only Gate 1 (preflight) is real.

### Checklist — Phase 5

- [ ] 5.1 Gate 2 TDD: phase tracking (plan → red → green → complete), file in `.crux/tdd/state.json`
- [ ] 5.2 Gate 3 Security Audit: recursive audit loop — scan for CWE/OWASP patterns, iterate until convergence
- [ ] 5.3 Gate 4 (8B) + Gate 5 (32B): LLM audit backends — HTTP clients for Ollama/Anthropic/OpenAI
- [ ] 5.4 Gate 6 Human Approval: state tracking (pending → approved → rejected)
- [ ] 5.5 Gate 7 DRY_RUN: execution mode flag in pipeline config
- [ ] 5.6 MCP tools return real state (not stubs): start_tdd_gate, check_tdd_status, start_security_audit, security_audit_summary
- [ ] 5.7 Tests for each gate

---

## Phase 6: External API Clients

**Gap:** crux_ollama.py, crux_typefully.py, crux_figma.py, crux_audit_backend.py — no HTTP clients.

### Checklist — Phase 6

- [ ] 6.1 Add `reqwest` dependency for HTTP client
- [ ] 6.2 Ollama client: `generate(model, prompt)`, `check_running()`, `list_models()`
- [ ] 6.3 Typefully client: `create_draft(text)`, `list_drafts()`, `delete_draft(id)`
- [ ] 6.4 Figma client: `get_tokens(file_key, token)`, `get_components(file_key, token)`
- [ ] 6.5 Audit backend: `audit_8b(script, model)`, `audit_32b(script, model)` — call Ollama or cloud API
- [ ] 6.6 Backend selection: Ollama → Anthropic → OpenAI → disabled (same priority as Python)
- [ ] 6.7 MCP tools: figma_get_tokens, figma_get_components do real API calls
- [ ] 6.8 Tests with mock HTTP responses

---

## Phase 7: BIP System — Build-in-Public Pipeline

**Gap:** crux_bip.py + 5 modules — entire BIP pipeline non-functional.

### Checklist — Phase 7

- [ ] 7.1 BIP config: load `.crux/bip/config.json` (Typefully account, triggers, voice rules)
- [ ] 7.2 BIP state: load/save `.crux/bip/state.json` (counters, cooldown, last_queued)
- [ ] 7.3 Trigger evaluation: commit threshold, token threshold, high-signal events, cooldown gate
- [ ] 7.4 Content gathering: git log, corrections, knowledge, session state since last post
- [ ] 7.5 `bip_generate` returns real gathered context (not stub)
- [ ] 7.6 `bip_approve` saves draft + queues to Typefully via API client
- [ ] 7.7 `bip_status` returns real counters
- [ ] 7.8 `bip_get_analytics` queries Typefully for engagement data
- [ ] 7.9 Tests

---

## Phase 8: Knowledge Management — Clustering, Staleness, Categories

**Gap:** crux_knowledge_clustering.py, crux_knowledge_staleness.py, crux_knowledge_categories.py

### Checklist — Phase 8

- [ ] 8.1 Correction clustering: group similar corrections by pattern (keyword overlap)
- [ ] 8.2 Knowledge generation from clusters: when N corrections share a pattern, generate knowledge entry
- [ ] 8.3 Staleness detection: flag knowledge entries not used in 30+ days
- [ ] 8.4 Category taxonomy: organize entries into predefined categories (architecture, patterns, conventions, security)
- [ ] 8.5 Three-tier promotion: project → user → public (with threshold tracking)
- [ ] 8.6 Tests

---

## Phase 9: Model Quality + Routing

**Gap:** crux_model_quality.py, crux_model_tiers.py, model_auto_evaluate.py, model_registry_update.py

### Checklist — Phase 9

- [ ] 9.1 Model tier definitions: micro/fast/local/standard/frontier with model mappings
- [ ] 9.2 Quality tracking: success rate per model per task type (JSONL log)
- [ ] 9.3 Auto-escalation: when success rate < 70%, recommend higher tier
- [ ] 9.4 Ollama model discovery: query localhost:11434/api/tags for available models
- [ ] 9.5 MCP tools: get_model_for_task, get_available_tiers, get_mode_model, get_model_quality_stats return real data
- [ ] 9.6 Tests

---

## Phase 10: Background Processors + Digest

**Gap:** crux_background_processor.py, generate_digest.py, extract_corrections.py

### Checklist — Phase 10

- [ ] 10.1 Threshold checking: corrections queue size, interaction count, token usage
- [ ] 10.2 Correction extraction from analytics/conversations JSONL
- [ ] 10.3 Daily digest generation: corrections, knowledge, mode usage, tool stats
- [ ] 10.4 Processor state tracking in `.crux/analytics/processor_state.json`
- [ ] 10.5 MCP tools: check_processor_thresholds, run_background_processors, get_processor_status return real data
- [ ] 10.6 Tests

---

## Phase 11: Cross-Domain + Cross-Project

**Gap:** crux_cross_domain.py, crux_cross_project.py

### Checklist — Phase 11

- [ ] 11.1 Project registry: register projects in `~/.crux/projects/registry.json` with real metadata
- [ ] 11.2 Cross-project digest: aggregate corrections/knowledge/activity across registered projects
- [ ] 11.3 Cross-domain knowledge flows: detect knowledge applicable across domains
- [ ] 11.4 MCP tools: register_project, get_cross_project_digest return real aggregated data
- [ ] 11.5 Tests

---

## Phase 12: Design Validation + Handoff

**Gap:** crux_design_validation.py, crux_design_handoff.py

### Checklist — Phase 12

- [ ] 12.1 WCAG contrast checking: real luminance calculation (already implemented in check_contrast)
- [ ] 12.2 Touch target validation: minimum 44x44px
- [ ] 12.3 Design-to-code handoff: structured handoff document with tokens, components, spacing
- [ ] 12.4 MCP tools: start_design_validation, design_validation_summary return real results
- [ ] 12.5 Tests

---

## Phase 13: Prompt Quality

**Gap:** crux_prompt_bloat.py, crux_prompt_improvement.py

### Checklist — Phase 13

- [ ] 13.1 Prompt bloat detection: measure token count of mode prompts, flag > 200 words
- [ ] 13.2 Prompt improvement suggestions: check positive framing, critical rules at start/end
- [ ] 13.3 Mode audit: verify all 24 modes follow research-backed conventions
- [ ] 13.4 Tests

---

## Phase 14: Status + Health Enhancements

**Gap:** crux_status.py had comprehensive health checks — Rust version is minimal.

### Checklist — Phase 14

- [ ] 14.1 Static checks: session state, hooks, interaction logging, correction capture, knowledge base, MCP server, modes
- [ ] 14.2 Liveness checks: hook completeness, conversation logging, log consistency, MCP loadable, session freshness
- [ ] 14.3 Findings generation: actionable recommendations from health check results
- [ ] 14.4 `crux status` shows full status + health + findings (like Python version)
- [ ] 14.5 MCP tool: verify_health returns comprehensive report
- [ ] 14.6 Tests

---

## Phase 15: Site Revision Tracking

**Gap:** crux_site_revision.py — detect when code changes make website content stale.

### Checklist — Phase 15

- [ ] 15.1 Track tool/mode/test counts and compare against site content
- [ ] 15.2 Flag stale pages when counts change
- [ ] 15.3 Tests

---

## Phase 16: Remove All Stubs — Replace with Real Implementations

**Purpose:** Every MCP tool that currently returns hardcoded data gets replaced with real logic.

### Checklist — Phase 16

- [ ] 16.1 Audit all `serde_json::json!({...})` returns in server.rs — identify remaining stubs
- [ ] 16.2 Replace each stub with call to real implementation from phases 1-15
- [ ] 16.3 Integration tests: every tool returns data from actual `.crux/` state, not hardcoded
- [ ] 16.4 Full test suite passes

---

## Convergence Criteria

- All 36 missing modules ported to Rust
- Zero stub MCP tools — every tool does real work
- All external API clients implemented (Ollama, Typefully, Figma)
- Full safety pipeline (7 gates) operational
- BIP pipeline functional end-to-end
- Knowledge clustering and staleness detection active
- Background processors running on thresholds
- Hook runner working for Claude Code
- 100+ Rust tests
- Two consecutive clean audit passes
