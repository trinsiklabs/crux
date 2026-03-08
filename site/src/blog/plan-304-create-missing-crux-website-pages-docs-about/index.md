---
layout: post.njk
title: "Create Missing Crux Website Pages"
date: 2026-03-08
tags: [ship, plan-304]
---

# Create Missing Crux Website Pages

A product without documentation is a product nobody uses. Today we filled the critical gaps in runcrux.io by shipping the missing core pages that visitors need to understand and adopt Crux.

## What We Shipped

We created six essential pages that were completely absent from the website: `/docs/` for technical documentation, `/about/` explaining the project and team, `/architecture/` detailing how Crux works under the hood, `/safety-pipeline/` covering our AI safety approach, `/switching/` for migration guidance, and `/adopt/` explaining the adoption workflow. Each page follows our existing design system and is fully integrated into the site navigation.

## How It Works

Each page is built as an Eleventy template using Nunjucks, pulling content from structured markdown where appropriate. The architecture page includes interactive diagrams generated from Mermaid definitions. The safety pipeline page links directly to the crux-safety repository for those who want to dive into code. All pages are mobile-responsive and integrate with our existing header/footer components.

## Why It Matters

Conversion happens when visitors can quickly understand what a product does, how it works, and how to get started. The missing pages were creating a significant drop-off in our user journey. A developer landing from a Twitter link would hit the homepage, click "Learn More," and find a 404. Now they find comprehensive documentation that guides them from curiosity to installation to productive use.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
