---
layout: post.njk
title: "Repo-Aware BIP Hooks"
date: 2026-03-08
tags: [ship, plan-317]
---

# Repo-Aware BIP Hooks

One developer, many projects. Today we shipped repo-aware BIP hooks that route shipping events to the correct project's build-in-public pipeline.

## What We Shipped

Repo-aware BIP hooks add project detection to the event pipeline. When a shipping event fires, the system identifies which adopted project the affected files belong to and routes logging to that project's BIP configuration. Non-adopted repositories are automatically ignored, preventing noise from personal experiments or one-off scripts. Each project maintains its own pending queue, escalation rules, and publishing credentials.

## How It Works

Project detection uses a hierarchy: first check if the file path is within a known adopted project root, then fall back to git remote origin analysis, finally check for a `.crux/project.json` marker. Once identified, the event metadata is enriched with project context and routed to the appropriate BIP instance. This enables running a single Crux installation across multiple projects while maintaining separation. The routing layer is also extensible for future multi-account X publishing.

## Why It Matters

Developers working on multiple projects need BIP to "just work" without manual project switching. Repo awareness makes the system context-aware, publishing updates to the right audience through the right channel. It also prevents embarrassing cross-posts where a personal project update goes to a professional account. The system respects boundaries automatically, making multi-project BIP practical rather than a configuration nightmare.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
