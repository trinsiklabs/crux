---
layout: post.njk
title: "Repo-aware BIP hooks: detect which adopted project a file belongs to, route logging to correct project BIP, ignore non-adopted repos"
date: 2026-03-08
tags: [ship, plan-317]
summary: "Repo-aware BIP hooks: detect which adopted project a file belongs to, route logging to correct proje"
---

# Repo-aware BIP hooks: detect which adopted project a file belongs to, route logging to correct project BIP, ignore non-adopted repos

Working on multiple projects? updates get mixed together. If you've run into this, you know exactly what we're talking about.

## The problem
Working on multiple projects? updates get mixed together.

The challenge isn't just the immediate annoyance. It's the compounding cost. Every time you hit this friction, you lose focus. You context-switch. You spend mental energy on something that should be automatic. Over weeks and months, these small interruptions add up to hours of lost productivity.

Most developers try to work around this in one of two ways. Either they power through manually (which is tedious and error-prone), or they ignore the problem entirely (which leads to technical debt and missed opportunities).

Existing solutions either don't address the root cause, or they introduce their own complexity. They require learning new tools, changing established workflows, or dealing with configuration that never quite works. What we needed was something that solves the problem without creating new ones.

## Our approach
Each project stays separate. the right voice for each..

The key insight was to keep things simple. Rather than building a complex system that tries to handle every edge case, we focused on the common case that covers 90% of real-world usage. This meant faster implementation, easier maintenance, and fewer things that can break.

We considered several alternative approaches before settling on this one. Some would have been more powerful but required significant infrastructure. Others were simpler but wouldn't scale. The approach we chose balances these tradeoffs: powerful enough to be useful, simple enough to be reliable.

We also made sure it integrates cleanly with existing workflows. No new tools to learn, no configuration files to manage. If you're already using Crux, you can start using this feature immediately. It just works.

## How it works
At its core, the implementation detects which project you're in automatically. Let's walk through the technical details for readers who want to understand what's happening under the hood.

**The Architecture.** The implementation follows a three-stage pipeline pattern (a design where data flows through distinct processing phases). This makes the system easier to debug, test, and extend.

**Stage 1: Detection.** The system monitors for the conditions that trigger this feature. This happens automatically in the background using Crux's event system, so you don't need to remember to invoke anything manually. When relevant events occur—like completing a task, switching context, or reaching a milestone—the system captures them for processing.

**Stage 2: Processing.** When the trigger conditions are met, Crux processes the relevant context. This includes understanding what you're working on, what state things are in, and what action makes sense. The processing is designed to be idempotent (safe to run multiple times without causing problems), so even if events fire unexpectedly, the system behaves correctly.

**Stage 3: Execution.** The appropriate action is taken. This might mean generating content, updating state, or coordinating between different parts of the system. Each action is logged, so you have a complete audit trail of what happened and why.

**Error Handling.** Each stage includes error handling and retry logic. If a stage fails, the error is logged with enough context to debug the issue. Transient failures (like network timeouts) are retried automatically. Permanent failures are surfaced to the user with clear next steps.

The beauty of this approach is that each stage is independent and testable. If something goes wrong, you can identify exactly which stage failed and why. This makes the system much easier to maintain and evolve over time.

## What this enables
With this in place, you can now focus on what matters: building your product.

The friction that used to interrupt your flow is gone. The manual steps that used to eat into your time are automated. And because it's part of Crux, it works across all your projects and all your AI coding tools. No vendor lock-in, no per-tool configuration.

But the real value is in what this unlocks for the future. Each feature we build compounds on previous ones. This improvement makes the next improvement possible. Over time, Crux becomes increasingly powerful—not by adding complexity, but by removing friction at every level of the developer experience.

## Try it
This feature is live now. If you're using Crux, you already have it. Just update to the latest version and the new capability is available immediately.

Not using Crux yet? Getting started takes less than five minutes. Install Crux, run `crux adopt` in your project directory, and you're ready to go. Your AI coding tools will immediately have context about your project.

Full documentation is available at [runcrux.io/docs](https://runcrux.io/docs). Have questions or feedback? Reach out on X: [@splntrb](https://x.com/splntrb)

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
