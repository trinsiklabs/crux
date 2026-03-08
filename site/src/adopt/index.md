---
layout: base.njk
title: crux adopt
description: Onboard an existing AI coding session into Crux without starting over
---

# crux adopt

## The Problem

You're 3 hours into a coding session. You've built up context, made decisions, touched dozens of files. Now you want Crux features — correction detection, session persistence, modes. But starting over means losing everything.

## The Solution

```bash
crux adopt
```

Crux captures your existing session and onboards it. No restart needed.

## What Gets Captured

| Context | How It's Captured |
|---------|-------------------|
| Files touched | Git history (last 50 commits) |
| Decisions made | Commit messages parsed |
| Project structure | Directory tree analyzed |
| Tech stack | Package files detected |
| Existing CLAUDE.md | Imported to `.crux/context/` |

## What You Provide

After running `crux adopt`, the LLM asks you to fill in what git can't know:

- **What are you working on?** — Current task/feature
- **Key decisions made?** — Technical choices this session
- **What's pending?** — Next steps, blockers
- **Knowledge worth saving?** — Patterns, gotchas, conventions

This becomes your session state, immediately available to any Crux-compatible tool.

## What Gets Set Up

```
.crux/                        # Created
├── sessions/
│   └── state.json            # Your session state
├── context/
│   ├── PROJECT.md            # Auto-generated project context
│   └── CLAUDE.md.imported    # Your existing CLAUDE.md
├── corrections/              # Ready for correction detection
├── knowledge/                # Ready for knowledge capture
└── bip/                      # Build-in-public if enabled
    ├── config.json           # BIP settings
    └── state.json            # Trigger counters

.claude/                      # Created (for Claude Code)
├── mcp.json                  # MCP server config
└── settings.local.json       # Hooks config
```

## Hooks Setup

`crux adopt` installs hooks into `.claude/settings.local.json`:

```json
{
  "SessionStart": [{
    "hooks": [{ "type": "command", "command": "crux session start" }]
  }],
  "PostToolUse": [{
    "hooks": [
      { "type": "command", "command": "crux detect correction" },
      { "type": "command", "command": "crux bip check" }
    ]
  }],
  "Stop": [{
    "hooks": [{ "type": "command", "command": "crux session save" }]
  }]
}
```

These hooks enable:
- **Session persistence** — State saved across sessions
- **Correction detection** — Auto-capture when you correct the AI
- **BIP triggers** — Shipping activity logged for build-in-public
- **TDD enforcement** — Source files require test files (optional)

## Example

```bash
# You've been coding for hours. Want Crux.
cd /path/to/your/project

# Run adopt
crux adopt

# Output:
# Initialized .crux/ directories
# Discovered 87 files from git history
# Created session state
# Imported CLAUDE.md
# Generated PROJECT.md
# Created .claude/mcp.json
# Created .claude/settings.local.json (hooks)

# LLM asks: "What are you working on?"
# You: "Building OAuth2 flow with refresh tokens"

# LLM asks: "Key decisions?"
# You: "Using python-jose, Redis for session store"

# Done. Session captured. Crux active.
# Next session picks up with full context.
```

## When to Use adopt vs switch

| Scenario | Use |
|----------|-----|
| New project, haven't used Crux | `crux adopt` |
| Existing session, want Crux features | `crux adopt` |
| Already using Crux, changing tools | `crux switch` |
| Already using Crux, same tool | Neither (already active) |

**adopt** = Onboard into Crux for the first time
**switch** = Move between tools within Crux

## Build-in-Public Integration

When you run `crux adopt`, it's a high-signal event. If you have build-in-public enabled:

- Event fires: `crux_adopt`
- BIP system detects the event
- Draft generated: "just onboarded a 3-hour session into crux. 87 files, full context captured. the cold-start problem is solved."

Your adoption becomes content.

## The Cold-Start Problem

Most developer tools suffer from cold-start: you have to configure everything before you get value. Crux inverts this:

1. Start coding with any tool
2. Build up context naturally
3. Run `crux adopt` when you want Crux features
4. Context captures instantly
5. Full Crux features active immediately

No upfront investment. Value from minute one.

## See Also

- [Tool Switching](/switching/) — Switch between tools after adoption
- [Architecture](/architecture/) — How Crux captures and persists context
- [Modes](/modes/) — Specialized modes available after adoption
