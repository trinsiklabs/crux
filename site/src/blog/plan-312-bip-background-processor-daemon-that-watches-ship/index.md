---
layout: post.njk
title: "BIP Background Processor"
date: 2026-03-08
tags: [ship, plan-312]
---

# BIP Background Processor

Shipping and publishing should be decoupled. Today we shipped the BIP background processor, a daemon that watches for shipping activity and handles draft generation asynchronously.

## What We Shipped

The BIP background processor is a long-running daemon that monitors shipping events and triggers draft generation without blocking your development workflow. When you complete a plan or merge a PR, the processor picks up the event, generates a blog draft and X thread proposal, and queues them for your review. You keep working; drafts appear in the background.

## How It Works

The daemon runs as a lightweight process that watches the `.crux/events/` directory for new shipping events. When an event file appears, the processor reads the metadata, applies escalation rules, and if publication is warranted, invokes Claude to generate appropriate content. Generated drafts land in `.crux/bip/pending/` with a notification sent to the terminal. The processor handles its own lifecycle: graceful shutdown, restart on crash, and idempotent processing to avoid duplicate drafts.

## Why It Matters

Context switching is expensive. Stopping mid-code to write a blog post breaks flow state. The background processor eliminates this friction by moving content generation to idle time. When you finish a focused coding session and look up, draft content is waiting for a quick review and approval. Publishing becomes a five-second task instead of a fifteen-minute interruption. This makes building in public sustainable for people who actually need to build.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
