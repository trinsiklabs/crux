---
title: Crux Domain Charter
last_updated: 2026-03-24
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Domain Charter

## Purpose

Crux is a self-improving AI operating system — an open-source framework that wraps any LLM and any agentic tool to maximize effectiveness through specialized modes, continuous learning, and infrastructure-enforced reliability.

The `.crux/` directory is the product. It stores all AI-assisted development intelligence: corrections, knowledge entries, session state, mode definitions, and security audit results. Tools are disposable; intelligence is sovereign.

## Scope

### In Scope

- **Crux OS** (this repo): open-source intelligence framework — 24 modes, 43 MCP tools, 7-gate safety pipeline, continuous learning, tool-agnostic session management
- **runcrux.io**: project website — 18 pages, 11ty static site, docs for 7 AI tools
- **Build-in-public system**: automated content pipeline — Typefully integration, trigger-based draft generation, voice rules
- **Cross-tool adapters**: Claude Code (hooks + MCP), OpenCode (plugins + MCP), Cursor/Windsurf/Aider/Roo Code/Qwen-Agent (MCP only)

### Out of Scope

- **Crux Vibe** (commercial platform): separate domain when built
- **CruxCLI**: separate domain (trinsiklabs/opencode fork)
- **CruxDev**: separate domain (convergence engine)
- Model training or fine-tuning
- Hosting or cloud infrastructure

## Ownership

- **Owner:** Bryan (solo founder, Trinsik Labs)
- **Repository:** trinsiklabs/crux (upstream), tecto/crux (fork)
- **License:** MIT

## Boundaries

### Technical Boundaries

- Python stdlib + mcp package only (no heavy dependencies)
- All filesystem modifications through scripts (scripts-first principle)
- 100% test coverage enforced on scripts/lib/
- Security validation on all file paths (PLAN-166)
- Symlink-based installation (git pull = instant update)

### Organizational Boundaries

- Crux does not own any AI model — it wraps them
- Crux does not own any agentic tool — it enhances them
- Crux does not store secrets (API keys in gitignored files only)
- Cross-project knowledge promotes upward: project → user → public

## Success Criteria

### Current (Maturity Level 2 — Growing)

- 1290+ tests passing, 100% coverage on core
- 43 MCP tools operational
- 24 specialized modes
- Claude Code and OpenCode fully integrated
- Website built (18 pages), pending deployment
- Build-in-public pipeline functional

### Next Milestone (Maturity Level 3 — Production)

- runcrux.io deployed and live
- First Show HN launch
- 100+ GitHub stars
- 5+ active users running Crux daily
- Background processor for continuous learning operational
- All documentation gaps filled (per GAPS.md)

## Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| Python 3.10+ | Runtime | Core scripts and MCP server |
| mcp package | Library | MCP protocol support |
| Claude Code | Tool | Primary development tool (hooks + MCP) |
| OpenCode | Tool | Secondary tool (plugins + MCP) |
| Ollama | Optional | Local LLM for adversarial auditing |
| 11ty | Build | Website static site generator |
| Typefully | Service | X/Twitter post scheduling |

## Key Decisions

1. MCP server as universal adapter — all logic lives in one place, tools connect via protocol
2. Symlink-based installation — git pull updates everything instantly
3. Positive instruction framing only in mode prompts (research-backed)
4. Separate auditor model (8B audits 32B's work) for structural adversarial review
5. Daily digest cadence, not weekly (multi-project developer workflow)
6. Infrastructure over instructions — enforce behavior through code, not prompts
