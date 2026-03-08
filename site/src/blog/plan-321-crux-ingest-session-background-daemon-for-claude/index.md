---
layout: post.njk
title: "crux ingest-session Daemon"
date: 2026-03-08
tags: [ship, plan-321]
---

# crux ingest-session Daemon

Migrating Claude Code sessions should be invisible. Today we shipped the `ingest-session` background daemon that handles comprehensive session capture with full resilience.

## What We Shipped

The `crux ingest-session` daemon runs in the background, migrating Claude Code session data into Crux's format. It handles comprehensive capture of conversation history, tool invocations, and file changes. The daemon is idempotent (safe to restart), restartable (picks up where it left off after crashes), and auto-restarts if killed unexpectedly. Progress logging keeps users informed without requiring attention.

## How It Works

The daemon monitors Claude Code's session storage directory and incrementally processes new session data as it appears. Each session chunk is assigned a unique ID for idempotency; reprocessing the same chunk is a no-op. State is persisted to disk after each chunk, enabling restart from any point. A watchdog process monitors the main daemon and restarts it if it exits unexpectedly. All of this runs in a single lightweight process that consumes minimal resources while maintaining continuous sync.

## Why It Matters

Session data is the foundation of Crux's value proposition. If session capture is unreliable, everything built on top (BIP events, project context, safety analysis) becomes unreliable too. The daemon's resilience guarantees ensure that session data is never lost, even during system crashes or restarts. Users can trust that their work is captured without needing to think about it. Background reliability enables foreground focus.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
