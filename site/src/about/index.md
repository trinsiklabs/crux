---
layout: base.njk
title: About Crux
description: The story behind Crux - portable AI coding intelligence that travels with you
---

# About Crux

## The Problem

Every AI coding tool locks your intelligence into their ecosystem. You build up context in Cursor, you lose it when you try Claude Code. You accumulate knowledge in Claude Code, it doesn't transfer to Aider. Your corrections, your learned patterns, your project context — all trapped in vendor-specific directories that die when you switch tools.

## The Solution

Crux is the `.git` for AI coding intelligence. It travels with you, no matter what tool you use.

Your corrections, your knowledge, your session state — all stored in `.crux/`. One directory. Works with every tool. Switches seamlessly.

## How It Works

```
~/.crux/                    # User-level: modes, knowledge, preferences
  modes/                    # 24 specialized modes
  knowledge/                # Accumulated learnings

.crux/                      # Project-level: context, corrections, sessions
  corrections/              # What the AI got wrong and how you fixed it
  knowledge/                # Project-specific patterns
  sessions/                 # State that persists across tools
  context/                  # Project context (auto-generated)
```

The Crux MCP server exposes 37 tools that any compatible AI assistant can use. One server, all logic, every tool connects.

## The Philosophy

**Infrastructure beats prompts.** Instead of telling the AI what to remember, Crux builds the infrastructure that makes forgetting impossible.

**Your intelligence, your control.** The `.crux/` directory is plain files you can read, edit, and version control. No vendor lock-in. No cloud dependency.

**Corrections compound.** Every time you fix an AI mistake, Crux captures it. Next time, the AI knows better. Across every tool.

## Who Built This

Crux is built by a solo developer who uses AI coding tools every day. Every feature exists because it solved a real problem. Every architectural decision comes from actual usage.

The project is open source. The code is the documentation.

## What's Next

- [Get started](/docs/) — Install Crux in 30 seconds
- [See the modes](/modes/) — 24 specialized modes for different work
- [Read the blog](/blog/) — Build-in-public updates
