---
layout: post.njk
title: "crux ingest-session - background daemon for Claude Code session migration. Comprehensive capture, idempotent, restartable, auto-restart on kill. Runs until complete with progress logging."
date: 2026-03-08
tags: [ship, plan-321]
summary: "crux ingest-session - background daemon for Claude Code session migration. Comprehensive capture, id"
---

# crux ingest-session - background daemon for Claude Code session migration. Comprehensive capture, idempotent, restartable, auto-restart on kill. Runs until complete with progress logging.

You've been deep in a coding session with Claude. It knows your architecture, your conventions, the bug you've been chasing for an hour. Then you need to switch to Cursor for its superior autocomplete. Fresh context. Everything you taught Claude? Gone. Time to start over.

## The problem
Every AI coding tool maintains its own context. Claude Code has CLAUDE.md. Cursor has .cursorrules. Windsurf has its own format. They don't talk to each other.

This means every time you switch tools, you lose everything the AI learned about your project. Worse, you have to maintain separate context files for each tool. Make a change in one, forget to update the others, and your AI assistants give you inconsistent advice.

The existing workaround—manually copying context between tools—is tedious and error-prone. It defeats the purpose of having AI help you move faster.

## Our approach
We built `crux ingest-session` to capture what one AI tool learned and translate it for others. The key insight was that context isn't just the rules file—it's the conversation history, the files discussed, the patterns discovered.

Instead of trying to sync rules files (which have different formats), we extract the semantic content. What did the AI learn about this codebase? Then we translate that into each tool's native format.

We also made it safe. Ingesting a session never overwrites your existing rules. It merges, with your manual customizations taking priority.

## How it works
Session ingestion works in three phases:

**Phase 1: Extraction.** We parse the source tool's context. For Claude Code, this means reading CLAUDE.md and the conversation history (stored in the session state). For Cursor, we read .cursorrules and the indexed file metadata. Each tool has an extractor that outputs a normalized context object.

```python
class NormalizedContext:
    project_description: str
    conventions: list[str]  # coding standards discovered
    architecture: dict       # component relationships
    recent_focus: list[str]  # files/topics discussed
```

**Phase 2: Translation.** The normalized context is translated into each target tool's format. This isn't just string templating—we rewrite content to match each tool's conventions. Cursor expects terse rules; Claude expects conversational context.

**Phase 3: Merge.** The translated context is merged with any existing rules file. We use a semantic diff to identify conflicts: if you've manually specified a convention that conflicts with the ingested content, your version wins. New content is appended with a comment marking it as auto-ingested.

**Format Detection**: We automatically detect which tool generated the context based on file patterns and content structure. You don't need to specify the source format.

## What this enables
With session ingestion, you can finally use the best tool for each task without losing context. Start a complex debugging session in Claude Code (great for reasoning), switch to Cursor for autocomplete-heavy work, and your AI still knows what you're building.

This is the core of Crux's mission: AI coding tool portability. Your knowledge should travel with you, not be locked into a single vendor.

## Try it
After a productive Claude Code session:

```bash
crux ingest-session claude-code
```

This updates your Cursor, Windsurf, and other tool contexts with what Claude learned. Check what would change with `--dry-run`.

Documentation: [runcrux.io/docs/ingest-session](https://runcrux.io/docs/ingest-session)

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
