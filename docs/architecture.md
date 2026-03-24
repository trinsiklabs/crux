---
title: Crux Architecture
last_updated: 2026-03-24
source: Consolidated from docs/architecture.md, docs/scripts-first.md, docs/tool-hierarchy.md, crux-roadmap/crux-expanded-architecture-spec.md
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Architecture

## Core Principle

Everything the AI does is enforced by code, not by instructions. Prompts drift. Infrastructure does not.

## System Overview

```
┌─────────────────────────────────────────────┐
│              Crux MCP Server                 │
│         (ALL logic lives here)               │
│  43 tools via FastMCP on stdio               │
│                                              │
│  Knowledge, session, corrections, digest,    │
│  safety, modes, project context, impact      │
│                                              │
│  Reads/writes: ~/.crux/ and .crux/           │
└──────────────┬──────────────────────────────┘
               │ MCP protocol (stdio)
    ┌──────────┼──────────────────┐
    │          │                  │
    ▼          ▼                  ▼
┌────────┐ ┌────────┐    ┌──────────────┐
│ Claude │ │OpenCode│    │Cursor/Cline/ │
│  Code  │ │        │    │Roo Code/etc  │
│        │ │        │    │              │
│ hooks: │ │plugins:│    │  MCP only    │
│ ~10 LOC│ │~10 LOC │    │ (no hooks)   │
│  each  │ │ each   │    │              │
└────────┘ └────────┘    └──────────────┘
```

## System Layers

### Layer 1: Lean Core (~50 tokens)

Global behavioral rules baked into the model's system role via Modelfile. Narration, directness, numbered lists. Never changes between interactions.

### Layer 2: Mode Prompts (~120-155 tokens)

24 specialized modes loaded one at a time. Each defines persona, domain rules, and tool access. Total system overhead: ~170-205 tokens = 99.4% of context available for work.

### Layer 3: MCP Server (43 tools)

All Crux logic lives in `scripts/lib/crux_mcp_server.py`. Handler functions in separate files for testability. Tools cover: knowledge, sessions, corrections, safety pipeline, design validation, BIP, analytics, model routing, and impact analysis.

### Layer 4: Hooks and Plugins

Tool-specific shims that forward events to the MCP server:
- **Claude Code:** 4 hooks (SessionStart, PostToolUse, UserPromptSubmit, Stop)
- **OpenCode:** 7 plugins (session-logger, think-router, correction-detector, compaction-hook, token-budget, tool-enforcer, crux-bridge)

## Three-Tier Scope

| Scope | Location | Content |
|-------|----------|---------|
| Project | `.crux/` | Knowledge, corrections, sessions, scripts, context for one project |
| User | `~/.crux/` | Cross-project knowledge, modes, analytics, templates |
| Public | This repo | Canonical modes, plugins, tools, scripts, MCP server |

Artifacts promote upward as they prove value: project → user → public.

## Scripts-First Principle

All filesystem modifications go through scripts. The AI writes scripts, scripts modify files. This enables: pre-flight validation, adversarial auditing by a separate model, human approval gate, DRY_RUN capability, and full audit trail.

## Tool Hierarchy

| Tier | Source | Example | Preference |
|------|--------|---------|------------|
| 0 | LSP | Language Server completions | Always prefer |
| 1 | Custom Tools | Zod-validated tools (OpenCode) | Next best |
| 2 | MCP Server | 43 FastMCP tools | Universal access |
| 3 | Library Scripts | `scripts/lib/` Python modules | Proven, promoted |
| 4 | New Scripts | Session scripts | One-time use |
| 5 | Raw Bash | Direct commands | Trend toward zero |

## Safety Pipeline (7 Gates)

| Gate | Name | Description | Triggered |
|------|------|-------------|-----------|
| 1 | Preflight | Static validation (header, risk, banned patterns) | All scripts |
| 2 | TDD | Test-first enforcement (plan → red → green → complete) | Build modes |
| 3 | Security Audit | Recursive audit loop (CWE/OWASP classification) | Medium+ risk |
| 4 | 8B Adversarial | Small model reviews large model's output | Medium+ risk |
| 5 | 32B Second Opinion | Large model re-reviews for structural issues | High risk |
| 6 | Human Approval | Manual review and approval | All scripts |
| 7 | DRY_RUN | Execute without side effects | Configurable |

## Continuous Learning

```
User corrects AI → correction logged to .crux/corrections/
    → corrections clustered by pattern
    → knowledge entries generated from clusters
    → entries promoted: project → user → public
    → modes and responses improve over time
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/lib/crux_mcp_server.py` | MCP server — 43 tool registrations |
| `scripts/lib/crux_mcp_handlers.py` | Pure handler functions (no MCP deps) |
| `scripts/lib/crux_hooks.py` | Claude Code hook handlers |
| `scripts/lib/crux_session.py` | Session state management |
| `scripts/lib/crux_sync.py` | Tool adapter layer |
| `scripts/lib/crux_paths.py` | Path resolution utilities |
| `scripts/lib/crux_security_audit.py` | Recursive security audit engine |
| `scripts/lib/crux_tdd_gate.py` | TDD/BDD enforcement |
| `scripts/lib/impact/scorer.py` | File relevance ranking |
| `modes/*.md` | 24 mode definitions with YAML frontmatter |

## See Also

- `docs/modes.md` — mode design principles and categories
- `docs/safety-pipeline.md` — detailed gate specifications
- `docs/continuous-learning.md` — knowledge system details
- `docs/API.md` — all 43 MCP tools documented
