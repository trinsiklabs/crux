---
layout: post.njk
title: "Site Content Auto-Revision"
date: 2026-03-08
tags: [ship, plan-310]
---

# Site Content Auto-Revision

Documentation that drifts from reality is worse than no documentation. Today we shipped automatic content revision that detects feature changes in the codebase and updates affected website pages without manual intervention.

## What We Shipped

Site content auto-revision monitors the Crux codebase for changes to tools, modes, and test coverage, then automatically updates the corresponding website pages. When you add a new CLI tool, the docs page updates. When you change a mode's behavior, the reference updates. When test coverage changes, the safety pipeline page reflects the new numbers. All automatic, all accurate.

## How It Works

The system works in three phases. First, a file watcher monitors key directories (tools, modes, tests) for changes. Second, a mapping layer associates code locations with documentation sections. Third, a revision engine uses Claude to generate updated documentation that accurately reflects the new code state while maintaining the existing prose style. The output goes to a review queue where a human can approve or edit before publishing.

## Why It Matters

Documentation maintenance is the silent killer of developer products. Teams start with great docs, then ship features faster than they update pages, and soon the docs become a liability rather than an asset. Auto-revision breaks this cycle by making documentation updates a byproduct of shipping code. The cognitive load of "remember to update the docs" disappears. Fresh docs become the default, not the exception.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
