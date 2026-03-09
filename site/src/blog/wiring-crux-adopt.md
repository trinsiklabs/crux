---
title: "wiring crux adopt for mid-session onboarding"
date: 2026-03-05T12:00:00
tags: [shipping, architecture, mcp]
summary: "two-phase onboarding so you can start using crux on an existing project without losing context"
---

shipped `crux adopt` today — the feature that solves the cold-start problem.

here's the scenario: you're 3 hours into a project in claude code. you've built up context, made decisions, had corrections. then you discover crux. do you:
a) start over with crux and lose all that context, or
b) keep using claude code and never try crux?

neither. you run `crux adopt`.

**phase 1: mechanical capture**
- parses git log for files touched, commit messages as decisions
- detects tech stack from package.json, requirements.txt, etc.
- generates PROJECT.md from the codebase structure
- imports existing CLAUDE.md if present

**phase 2: brain dump**
- the current session's LLM writes its own handoff context
- session state: what you were working on, what's pending
- knowledge entries: patterns discovered during this session
- corrections: what you taught the AI during this session
- this is the key insight: the LLM knows things git log doesn't

after `crux adopt`, the next session starts with full crux MCP server + hooks active, seeded with rich context from the previous session.

this is the single most compelling demo you can create. screen recording of running it on a real project, then showing the new session picking up exactly where you left off.

demo coming soon. for now, `crux adopt` is live in the repo.
