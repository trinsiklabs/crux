---
title: "day 1: starting crux"
date: 2026-03-05T12:00:00
tags: [shipping, philosophy]
summary: "building crux because every AI coding tool traps your intelligence. here's the plan."
---

day 1 of building crux. been thinking about this for a while.

the problem: every AI coding tool creates its own silo. cursor rules don't transfer to claude code. claude code sessions don't work in aider. your corrections, your context, your learned patterns — all locked in vendor-specific directories that don't talk to each other.

so i built `.crux/`.

it's a directory that lives in your project (and globally at `~/.crux/`) that stores everything your AI learns:
- corrections (every time you tell it "no, wrong, actually do it this way")
- knowledge entries (patterns that transcend any single project)
- session state (what you were working on, files touched, decisions made)
- mode definitions (21 specialized prompts for different tasks)
- safety rules (learned from your corrections)

the killer feature: `crux switch <tool>`.

start a project in claude code at work. come home, run `crux switch opencode`. opencode picks up exactly where you left off. same knowledge. same corrections. same context.

the MCP server is the brain. all logic lives in one place. every tool connects via standard MCP protocol.

tools with hooks (claude code, opencode) add paper-thin shims (5-10 lines) that forward events for correction detection. tools without hooks (cursor, cline, roo code) connect via MCP alone and get knowledge, session state, modes, and safety validation.

adding support for a new tool = one line in the tool's MCP config. not a full adapter. one line.

this is the `.git` for AI coding intelligence.

i'll be posting updates as i ship. follow along: [@splntrb](https://x.com/splntrb)

github: https://github.com/trinsiklabs/crux
