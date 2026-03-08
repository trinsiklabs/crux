---
layout: base.njk
title: Tool Switching
description: Switch between AI coding tools without losing context - crux switch
---

# Tool Switching

## The Problem

You're deep in a coding session with Claude Code. You want to try Cursor for its multi-file editing. But switching means losing your context — session state, corrections, mode settings, everything.

## The Solution

```bash
crux switch cursor
```

That's it. Your context transfers. Pick up exactly where you left off.

## What Transfers

| Context Type | Transfers? | How |
|--------------|------------|-----|
| Session state | Yes | `.crux/sessions/state.json` |
| Mode settings | Yes | `~/.crux/modes/` synced to tool config |
| Corrections | Yes | `.crux/corrections/` persists |
| Knowledge | Yes | `.crux/knowledge/` persists |
| Project context | Yes | `.crux/context/PROJECT.md` |
| Files touched | Yes | Listed in session state |
| Pending tasks | Yes | Listed in session state |
| Key decisions | Yes | Listed in session state |

## Supported Tools

| Tool | MCP Support | Hooks Support | Adapter |
|------|-------------|---------------|---------|
| Claude Code | Yes | Yes (native) | Full |
| OpenCode | Yes | Via plugins | Full |
| Cursor | Yes | Via rules | MCP-only |
| Windsurf | Yes | Via rules | MCP-only |
| Aider | Yes | Limited | MCP-only |
| Roo Code | Yes | Limited | MCP-only |
| Qwen-Agent | Yes | Limited | MCP-only |

## How It Works

```
crux switch <target-tool>
      │
      ▼
┌─────────────────────────────────────────┐
│ 1. Save current session state           │
│    - working_on, key_decisions, pending │
│    - files_touched, mode, timestamps    │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 2. Sync adapters for target tool        │
│    - Copy modes to tool-specific format │
│    - Generate tool-specific config      │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 3. Update active tool marker            │
│    - session.active_tool = target       │
│    - Ready for next session             │
└─────────────────────────────────────────┘
```

## Example Workflow

```bash
# Working in Claude Code on auth feature
# Session state: mode=security, working_on="OAuth2 flow"

# Want to try Cursor's multi-file editing
crux switch cursor

# Start Cursor - it connects to same MCP server
# Session state loads automatically
# Continue exactly where you left off

# Done with Cursor, back to Claude Code
crux switch claude-code

# Seamless
```

## What Doesn't Transfer

- **Tool-specific UI state** — Window positions, tabs, etc.
- **Tool-specific history** — Each tool has its own conversation history
- **Tool-specific plugins** — Plugins are tool-specific
- **In-flight operations** — Pending edits, uncommitted changes remain local

The `.crux/` directory is the canonical state. Tools are interchangeable consumers.

## Limitations

`crux switch` cannot:

- **Migrate conversation memory** — Each tool starts fresh conversation. Use handoff for critical context.
- **Transfer tool-specific state** — Cursor's multi-file selection, Windsurf's workflow state, etc.
- **Guarantee feature parity** — Not all tools support all Crux features (see support matrix above)
- **Run tools simultaneously** — Switch is point-in-time; tools don't share live state

**Best practice**: Write a handoff before switching for complex sessions.

## The Handoff System

For complex transitions, use the handoff file:

```bash
# Write detailed context for the next tool
crux handoff "Implementing OAuth2 flow. Using python-jose for JWT.
Current state: refresh token endpoint done, need access token rotation.
Key pattern: all tokens go through TokenService.validate().
Next step: implement rotation in /auth/rotate endpoint."

# Switch tools
crux switch opencode

# In OpenCode, read the handoff
crux restore  # Loads handoff context
```

## See Also

- [crux adopt](/adopt/) — Onboard an existing session into Crux
- [Architecture](/architecture/) — How the system works
- [Modes](/modes/) — Available modes for different work types
