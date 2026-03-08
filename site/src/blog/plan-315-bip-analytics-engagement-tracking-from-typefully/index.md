---
layout: post.njk
title: "BIP Analytics"
date: 2026-03-08
tags: [ship, plan-315]
---

# BIP Analytics

You cannot improve what you do not measure. Today we shipped BIP analytics that tracks engagement across all publishing channels in one unified view.

## What We Shipped

BIP analytics aggregates engagement data from Typefully (X metrics), blog traffic (page views, time on page), and GitHub signals (stars, forks, issues from blog referrals). The data flows into a lightweight dashboard that shows which content resonates, which topics drive adoption, and where attention is coming from. All metrics are tied back to the original shipping event that generated the content.

## How It Works

The analytics system pulls data from three APIs on a configurable schedule. Typefully provides impressions, engagements, and link clicks for X threads. Our Cloudflare analytics provide blog traffic with referrer breakdown. GitHub API provides star/fork events with timestamps we can correlate to publishing events. The aggregator normalizes these into a common schema and stores time-series data locally. A simple terminal UI renders sparklines and top performers on demand.

## Why It Matters

Building in public without feedback is shouting into the void. Analytics close the loop, showing what kinds of updates drive engagement and adoption. Over time, patterns emerge: maybe architecture posts outperform bug fix announcements, or threads with code snippets get more clicks. This data informs content strategy without requiring dedicated marketing effort. The analytics are a byproduct of the publishing system, not a separate initiative.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
