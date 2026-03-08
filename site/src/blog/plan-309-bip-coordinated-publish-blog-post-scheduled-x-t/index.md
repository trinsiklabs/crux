---
layout: post.njk
title: "BIP Coordinated Publish"
date: 2026-03-08
tags: [ship, plan-309]
---

# BIP Coordinated Publish

Publishing across multiple channels manually is error-prone and time-consuming. Today we shipped atomic coordinated publishing that ensures blog posts, X threads, and site deploys happen together or not at all.

## What We Shipped

BIP coordinated publish combines three previously separate actions into a single atomic workflow: generating and committing a blog post, scheduling an X thread via Typefully, and triggering a site deploy. When you approve a BIP draft, all three happen in sequence with rollback if any step fails. No more orphaned tweets pointing to 404 blog posts.

## How It Works

The coordinated publish workflow uses a transaction-style approach. First, the blog post is committed to the site repo. Then the X thread is scheduled via the Typefully API with a delay matching our deploy time. Finally, the deploy script is triggered. If the deploy fails, we cancel the scheduled tweet and revert the blog commit. Success is all-or-nothing. The implementation leverages our existing event system to chain these operations with proper error boundaries.

## Why It Matters

Building in public means consistent presence across channels. When a follower sees a tweet about a new feature and clicks through, they need to land on a live blog post. Coordinated publish eliminates the coordination overhead that makes multi-channel publishing feel like a chore. It turns what was a five-minute manual process into a single keystroke approval, making consistent publishing sustainable even during intense shipping sprints.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
