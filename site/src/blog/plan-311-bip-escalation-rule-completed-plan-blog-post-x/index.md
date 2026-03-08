---
layout: post.njk
title: "BIP Escalation Rule"
date: 2026-03-08
tags: [ship, plan-311]
---

# BIP Escalation Rule

Not everything deserves a tweet, and nobody wants timeline spam. Today we shipped the escalation rule system that determines which shipping events warrant which type of public announcement.

## What We Shipped

The BIP escalation rule creates a clear policy for what gets published where. Completed plans automatically generate blog posts. X posts are rate-limited to maximum one per 15 minutes to prevent follower fatigue. Small fixes might only get a blog entry. Major features get the full treatment: blog, X thread, and potentially a longer-form announcement. The rules are configurable per project and event type.

## How It Works

Every shipping event passes through the escalation evaluator before triggering any public action. The evaluator considers event type (plan completion, bug fix, feature launch), recency of last publication, current queue depth, and project-specific overrides. The output is an escalation level: silent (log only), blog (blog post, no social), or full (blog plus X thread). Rate limiting uses a sliding window to ensure we never exceed the configured post frequency regardless of how fast we're shipping.

## Why It Matters

Building in public is a balance between visibility and noise. Post too little and you're invisible. Post too much and followers mute you. The escalation rule automates this judgment, ensuring consistent presence without manual decision-making for each event. It also prevents the "batch problem" where a productive day generates a dozen tweets in an hour. Steady, sustainable visibility is better than spiky overload.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
