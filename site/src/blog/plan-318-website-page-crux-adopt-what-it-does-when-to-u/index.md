---
layout: post.njk
title: "Website Page: crux adopt"
date: 2026-03-08
tags: [ship, plan-318]
---

# Website Page: crux adopt

Users need to understand commands before they run them. Today we shipped the comprehensive documentation page for `crux adopt`, explaining everything from basic usage to BIP integration.

## What We Shipped

The new `/adopt/` page covers the complete `crux adopt` workflow: what it does (registers a project for Crux management), when to use it (starting a new project or adding Crux to existing work), how it integrates with BIP (automatic session capture and event hooks), and how it differs from `crux switch`. The page includes command examples, configuration options, and troubleshooting for common issues.

## How It Works

The page is structured as a progressive disclosure document. Quick-start users get the essential command and common flags immediately. Those who want to understand the system can read deeper sections on session capture mechanics, hook setup, and the underlying file structures Crux creates. Interactive examples show the terminal output users should expect. Links connect to related pages (switch, architecture, safety) for comprehensive navigation.

## Why It Matters

`crux adopt` is the entry point for new users. If this command is confusing or undocumented, adoption stalls at the first step. A dedicated page with clear examples reduces support burden and improves conversion from "interested" to "installed and using." It also establishes Crux as a professional tool with proper documentation, not a weekend hack. First impressions matter, and `adopt` is often the first command users encounter.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
