---
layout: post.njk
title: "BIP Inline Review Flow"
date: 2026-03-08
tags: [ship, plan-313]
---

# BIP Inline Review Flow

Review friction kills publishing momentum. Today we shipped inline review flow with single-keystroke approval directly in your terminal.

## What We Shipped

The BIP inline review flow presents pending drafts between work sessions with simple keyboard controls: `a` to approve and publish, `e` to edit before publishing, `s` to skip and review later. Drafts render directly in the terminal with proper formatting. No context switch to a browser, no separate app to check. Review happens where you already are.

## How It Works

When the BIP processor detects terminal idle time (configurable threshold, default 30 seconds), it checks for pending drafts. If any exist, it renders the highest-priority draft inline with a minimal UI showing the content preview and action hints. Keystroke capture is handled via raw terminal input, so a single keypress triggers the action. Approval fires the coordinated publish workflow. Edit opens your configured `$EDITOR` with the draft. Skip moves to the next draft or returns to shell prompt.

## Why It Matters

Every click and context switch between draft generation and publication is an opportunity to abandon the process. "I'll review those drafts later" becomes "I have 47 pending drafts I'll never look at." Inline review removes the gap between work and publication. When review is one keystroke away from your natural workflow, the default flips from "defer" to "approve." Publication happens at the speed of shipping.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
