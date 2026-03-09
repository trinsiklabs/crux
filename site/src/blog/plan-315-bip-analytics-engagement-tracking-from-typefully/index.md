---
layout: post.njk
title: "BIP analytics: engagement tracking from Typefully API, blog traffic, star/fork counts"
date: 2026-03-08
tags: [ship, plan-315]
summary: "BIP analytics: engagement tracking from Typefully API, blog traffic, star/fork counts"
---

# BIP analytics: engagement tracking from Typefully API, blog traffic, star/fork counts

You shipped something cool. You tweeted about it. Then... nothing? Or maybe it went viral, but you have no idea why. Building in public should help you understand what resonates with your audience, but instead it feels like shouting into the void.

## The problem
The core problem is feedback loops. When you ship code, you get immediate feedback: tests pass or fail, users report bugs, performance dashboards show improvements. But when you share your work publicly, the feedback is scattered across platforms and easy to miss.

Twitter impressions are in one place. Blog traffic is in another. Comments and replies are spread across multiple apps. By the time you've checked everything, your context-switching has killed your productivity.

The existing solutions—social media management tools, analytics dashboards—require you to leave your development environment. They're built for marketers, not developers. What we needed was analytics that fit into the developer workflow.

## Our approach
We built BIP Analytics to pull engagement data directly into Crux. No browser tabs, no dashboard logins. Just the numbers you need, where you need them.

The key insight was that developers don't need fancy charts. They need signals: what worked, what didn't, and what to try differently. So we focused on surfacing actionable insights rather than raw metrics.

We also made it async. Analytics sync in the background, so checking engagement never blocks your workflow.

## How it works
BIP Analytics uses a pull-based architecture. Here's how it works:

**OAuth2 Credentials** (a secure way to let apps access your accounts without sharing passwords): When you connect your social accounts, Crux stores encrypted OAuth tokens. These tokens let us fetch your engagement data without ever seeing your password.

**Background Sync**: A daemon process polls each platform's API at configurable intervals. We default to every 15 minutes—frequent enough to be useful, infrequent enough to respect rate limits (the number of API requests each platform allows per time period).

**The Analytics Store**: Engagement data lands in a local SQLite database. We chose SQLite because it's fast, requires no setup, and works offline. The schema tracks impressions, engagements, and link clicks per post, with timestamps for trend analysis.

**The CLI Interface**: Running `crux bip analytics` shows your recent posts ranked by engagement. We calculate a simple "resonance score" (engagements divided by impressions) to highlight what's actually connecting with your audience, not just what got lucky with the algorithm.

```bash
$ crux bip analytics --last 7d
Post                          Impressions  Engagements  Resonance
"Context portability..."      2,341        187          7.9%
"Shipped PLAN-301..."         892          23           2.5%
```

## What this enables
With BIP Analytics, you can finally learn from your public building. You'll see which technical topics resonate with your audience, which framing works best, and when your followers are most active.

Over time, this compounds. You get better at communicating your work. Your audience grows. More people use your product. And you never had to leave your terminal to make it happen.

## Try it
Connect your first social account with:

```bash
crux bip connect twitter
```

Then check your analytics:

```bash
crux bip analytics
```

Full documentation at [runcrux.io/docs/bip-analytics](https://runcrux.io/docs/bip-analytics)

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
