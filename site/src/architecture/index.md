---
layout: base.njk
title: Architecture
description: How Crux works - MCP server, hooks, modes, and the .crux directory
---

# Crux Architecture

## The Core Insight

Most AI coding tools treat intelligence as ephemeral. Session ends, context disappears. Crux treats intelligence as infrastructure — persistent, portable, and composable.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your AI Tool                             │
│         (Claude Code, OpenCode, Cursor, Aider, etc.)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Crux MCP Server                            │
│                    (37 tools, one server)                       │
│                                                                 │
│  Knowledge │ Session │ Corrections │ Modes │ Safety Pipeline   │
│  Lookup    │ State   │ Detection   │       │ (7 gates)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Reads/Writes
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        .crux/ Directory                         │
│                                                                 │
│  ~/.crux/              │  .crux/ (per-project)                 │
│  ├── modes/            │  ├── corrections/                     │
│  ├── knowledge/        │  ├── knowledge/                       │
│  └── config.json       │  ├── sessions/                        │
│                        │  └── context/                         │
└─────────────────────────────────────────────────────────────────┘
```

## The MCP Server

The MCP server is the brain. It exposes 37 tools that any MCP-compatible AI assistant can call:

- **Knowledge tools** — lookup, promote, search
- **Session tools** — state, handoff, restore
- **Safety tools** — audit, validate, gate checks
- **Mode tools** — get prompt, list modes, switch
- **Correction tools** — log, detect, apply

One server. Works with Claude Code, OpenCode, Cursor, Aider, Roo Code, Windsurf, Qwen-Agent — any tool that speaks MCP.

## The Directory Structure

### User-level (`~/.crux/`)

```
~/.crux/
├── modes/                  # 24 specialized modes
│   ├── build-py.md        # Python development
│   ├── security.md        # Security audit
│   ├── debug.md           # Debugging
│   └── ...
├── knowledge/             # Cross-project learnings
└── config.json            # User preferences
```

### Project-level (`.crux/`)

```
.crux/
├── corrections/           # AI mistakes and fixes
│   └── corrections.jsonl  # Append-only log
├── knowledge/             # Project-specific patterns
│   ├── api-conventions.md
│   └── test-patterns.md
├── sessions/              # Session state
│   └── state.json         # Current mode, tool, pending work
├── context/               # Auto-generated context
│   └── PROJECT.md         # Directory structure, tech stack
└── bip/                   # Build-in-public state
    ├── config.json
    └── state.json
```

## Hooks Integration

For Claude Code (native hooks):

```
SessionStart  → Inject mode prompt, session state, pending tasks
PostToolUse   → Track files touched, log interactions
UserPrompt    → Detect corrections in user messages
Stop          → Update session, check TDD compliance
```

For other tools: MCP tools provide equivalent functionality.

## The Safety Pipeline

Every code action can pass through up to 7 gates:

1. **Gate 0** — Static validation (syntax, linting)
2. **Gate 1** — TDD check (test coverage)
3. **Gate 2** — Security audit (vulnerability scan)
4. **Gate 3** — Design review (UI/UX validation)
5. **Gate 4** — Deep audit (8B model review)
6. **Gate 5** — Expert audit (32B model review)
7. **Gate 6** — Human review

Gates activate based on mode and risk level. Low-risk code skips expensive gates. High-risk code gets full pipeline.

## Why This Architecture

**Single source of truth.** The `.crux/` directory is the canonical state. Tools are interchangeable consumers.

**No vendor lock-in.** Plain files. No proprietary formats. Version control friendly.

**Incremental adoption.** Start with just MCP tools. Add hooks later. Enable safety pipeline when ready.

**Local-first.** Everything runs on your machine. No cloud dependency. Your data stays yours.
