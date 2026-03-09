---
layout: post.njk
title: "BIP coordinated publish: blog post + scheduled X thread + site deploy as atomic workflow"
date: 2026-03-08
tags: [ship, plan-309]
summary: "BIP coordinated publish: blog post + scheduled X thread + site deploy as atomic workflow"
---

# BIP coordinated publish: blog post + scheduled X thread + site deploy as atomic workflow

You've just finished implementing a feature. Now comes the part nobody talks about: the publish grind. Write a blog post. Craft a tweet thread. Deploy the site. Update the changelog. Each step is easy. Together, they're a 30-minute tax on every ship.

## The problem
The real cost isn't the 30 minutes. It's the context switching. You're in flow, riding the high of shipping something new. Then you have to switch gears completely—from builder to marketer to ops engineer and back.

Most developers handle this one of two ways. Either they publish immediately (and the quality suffers), or they batch it (and forget half of what they shipped). Neither is great.

What makes this hard is the coordination. The blog post needs to exist before you can tweet the link. The site needs to deploy before the link works. The timing matters. Get it wrong and you're sharing broken links.

## Our approach
We built Coordinated Publish to treat publishing as a single atomic operation. One command. Everything happens in the right order. If any step fails, you know immediately.

The key insight was that most shipping content follows a pattern. The plan ID tells us what shipped. The plan metadata tells us what it does. We can generate 80% of the content automatically and let you customize the rest.

We also made failure recoverable. If the deploy fails, the blog post is still saved locally. Fix the deploy, run again, and Crux picks up where it left off.

## How it works
Coordinated Publish orchestrates three subsystems:

**Blog Generation**: The `generate_blog_post()` function pulls plan metadata from the database and generates a Markdown file. We use 11ty (a static site generator—a tool that turns Markdown into web pages) because it's fast and the output is just files. The generated post includes frontmatter (metadata at the top of the file that tells 11ty how to render it) with title, date, and tags.

```python
def generate_blog_post(plan_id, plan_title, summary, site_dir):
    # Creates src/blog/{slug}/index.md
    # With 6-section narrative structure
```

**Site Deployment**: After generating the blog post, we run `npm run build` to regenerate the static site, then execute the deploy script. This ensures the new post is live before we share it.

**Social Scheduling**: Finally, we create an X thread using the Typefully API. The thread is scheduled for optimal engagement times (Tue-Thu, 9-11am EST based on indie hacker audience research). If Typefully isn't configured, we save the thread content locally so you can post manually.

**Error Handling**: Each step returns a success/failure status. The `PublishResult` dataclass tracks what succeeded, what failed, and collects error messages. This makes debugging straightforward—you know exactly where things went wrong.

## What this enables
With Coordinated Publish, shipping and sharing become one action. You finish a feature, run one command, and the world knows about it.

More importantly, you build a consistent publishing habit. When sharing is easy, you do it more. When you do it more, your audience grows. The compound effects of building in public actually start to compound.

## Try it
After implementing a plan:

```bash
crux bip publish PLAN-XXX
```

This generates the blog post, deploys your site, and schedules the announcement. Preview before publishing with `--dry-run`.

Documentation: [runcrux.io/docs/bip-publish](https://runcrux.io/docs/bip-publish)

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
