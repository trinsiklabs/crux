---
title: Crux Changelog
last_updated: 2026-03-24
migration_date: 2026-03-24
migration_status: normalized
---

# Changelog

## 2026-03-24

- **PLAN-002:** `analyze_impact` MCP tool — rank files by relevance to prompt using git history, keywords, and LSP (88 tests, 100% coverage)
- **Key Migration:** intake classification, inventory, GAPS.md, CHARTER.md, STRATEGY.md created
- Removed leaked API key from git history; added `.crux/analytics/` and `.crux/bip/` to `.gitignore`

## 2026-03-23

- **PLAN-182:** Flexible API backend support — Anthropic API, OpenAI API, or local Ollama for adversarial auditing
- **PLAN-170:** Require audit backend for OpenCode mode (no silent skipping)
- **PLAN-169:** Audit backend abstraction with fallback chain (Ollama → Anthropic → OpenAI → subagent → disabled)
- **PLAN-168:** Automated MCP server setup in `setup.sh` — venv, MCP config, verification
- Fixed MCP loadable test to mock subprocess
- Fixed `.mcp.json` location for Claude Code MCP discovery

## 2026-03-22

- **Phase A:** Knowledge self-improvement — 43 new tests (1684 total)
- Consolidation: docs, tests, self-adoption, security hardening, and build plans
- Quality feedback loop: adaptive model routing from history (80 tests)
- Escalation logic: tier_up on failure, provider fallback (61 tests)
- Model tier system: shared vocabulary for mixed model routing (45 tests)
- Claude Code slash commands for Crux workflows

## 2026-03-21

- **PLAN-166:** Security audit — fix 60 vulnerabilities (path traversal, credential redaction, input length limits, atomic file ops, shell injection prevention)
- Fix test compatibility with PLAN-166 security changes
- Python venv for cross-platform dependencies
- Requirements.txt with mcp package

## 2026-03-20

- **GROUP-MKT:** Build-in-public infrastructure complete (14 plans)
- **PLAN-324:** Wire BIP end-to-end (detection → publish via Typefully)
- **PLAN-327:** BIP backfill — 16 blog posts + fixes
- **PLAN-328:** Blog quality upgrade — pagination, narrative posts, link enforcement
- **PLAN-329, 330:** Mandate auto-clear + X post improvements
- **PLAN-331, 332:** Human-readable X posts, pain-focused content

## 2026-03-19

- **PLAN-299:** Update website content for accuracy
- **PLAN-214:** Key takes over Crux development

## 2026-03-06

- Website: 18 pages built (landing, docs for 7 tools, architecture, safety, modes, about, blog, changelog)
- Deploy script: `deploy-runcrux.io.sh` with --build, --dry-run, --force
- 3 blog posts: day-1, crux-adopt, mcp-server-is-product

## 2026-03-05

- Full-text conversation logging (Claude Code via hooks, OpenCode via MCP)
- 23 modes operational (24th added later: build-in-public)
- Safety pipeline: 7-gate system operational
- Initial public release structure
