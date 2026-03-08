---
layout: post.njk
title: "Website Page: crux switch"
date: 2026-03-08
tags: [ship, plan-319]
---

# Website Page: crux switch

Knowing what a tool cannot do is as important as knowing what it can. Today we shipped the documentation page for `crux switch`, including clear guidance on limitations and alternatives.

## What We Shipped

The new `/switch/` page documents the `crux switch` command: what it does (transitions between Crux tool configurations), when to use it (changing modes, swapping tool versions, project context switching), and critically, what it cannot do (migrate data, change project ownership, undo adopt). The page includes comparison with `crux adopt` to prevent user confusion between these related but distinct commands.

## How It Works

The page follows a "do / don't" structure that immediately clarifies scope. A comparison table shows `switch` vs `adopt` side by side. Each use case gets a dedicated section with the exact command and expected outcome. The "What Switch Cannot Do" section is prominent, preventing users from expecting functionality that doesn't exist. Error messages users might encounter are documented with explanations and solutions.

## Why It Matters

Command confusion causes support load and user frustration. By explicitly documenting `switch` alongside `adopt` with clear differentiation, we prevent the "I ran the wrong command" failure mode. The limitations section is especially important because undocumented limitations become reported bugs. By being upfront about scope, we set correct expectations and build trust. Users know they can rely on our docs to tell them what works and what doesn't.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
