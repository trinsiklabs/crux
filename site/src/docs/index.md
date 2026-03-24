---
layout: base.njk
title: Documentation
description: Get started with Crux - installation, setup, and tool integration
---

# Getting Started with Crux

## Quick Install

```bash
# Clone the repo
git clone https://github.com/yourusername/crux.git ~/.crux

# Run setup
cd ~/.crux && ./setup.sh

# Restart your AI tool to load the MCP server
```

## What You Get

- **43 MCP tools** — Knowledge, sessions, modes, safety, corrections
- **24 specialized modes** — build-py, security, debug, design-ui, and more
- **Session persistence** — State survives across sessions and tools
- **Correction detection** — Learn from AI mistakes automatically
- **Safety pipeline** — 7-gate validation for code changes

## Tool-Specific Setup

Choose your AI coding tool:

- [Claude Code](/docs/claude-code/) — Full integration with native hooks
- [OpenCode](/docs/opencode/) — Full integration via plugins
- [Cursor](/docs/cursor/) — MCP integration via rules
- [Windsurf](/docs/windsurf/) — MCP integration via rules
- [Aider](/docs/aider/) — MCP integration
- [Roo Code](/docs/roo-code/) — MCP integration
- [Qwen-Agent](/docs/qwen-agent/) — MCP integration

## Core Concepts

### The .crux Directory

All Crux state lives in `.crux/` directories:

```
~/.crux/          # User-level (modes, preferences)
.crux/            # Project-level (corrections, knowledge, sessions)
```

### Modes

Modes are specialized prompts that shape AI behavior:

```bash
# List available modes
crux modes

# See mode prompt
crux mode security
```

[See all 24 modes →](/modes/)

### Sessions

Session state persists across restarts:

```bash
# Check current session
crux status

# Update session
crux session --working-on "Building OAuth2 flow"
```

### Corrections

When you correct the AI, Crux captures it:

```
You: "No, use python-jose not PyJWT"
Crux: [Correction logged: library preference]
```

Future sessions know to use python-jose.

## Next Steps

1. [Run setup](#quick-install) for your environment
2. [Choose your tool](/docs/claude-code/) and complete tool-specific setup
3. [Explore modes](/modes/) for your work type
4. [Read the architecture](/architecture/) to understand how it works

## Reference

- [MCP Server](/docs/mcp-server/) — All 37 tools documented
- [Modes System](/docs/modes/) — How to create and customize modes
- [Safety Pipeline](/safety-pipeline/) — The 7-gate validation system
- [Tool Switching](/switching/) — Switch between tools seamlessly
- [crux adopt](/adopt/) — Onboard existing sessions
