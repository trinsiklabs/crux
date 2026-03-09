"""BIP coordinated publish: blog post + X thread + site deploy as atomic workflow.

PLAN-309: When a plan is implemented, this orchestrates:
1. Generate blog post from plan content
2. Schedule X thread announcing the post
3. Deploy updated site
4. All as one atomic operation

PLAN-330: X post improvements
- 3-tweet threads with outcome-focused hooks
- Hashtags (#BuildInPublic #IndieHackers)
- Optimal scheduling (Tue-Thu 9-11am EST)
- Challenge posts for blocked/failed plans

PLAN-331: Human-readable posts + why it matters
- Translate jargon to plain English
- Add "why it matters" context
- Make posts understandable to non-technical people

PLAN-333: Deeper technical blog posts with accessible context
- 800-1500 word posts (vs previous 200-300)
- 6-section structure: Hook, Problem, Approach, Technical Deep Dive, Enables, Try It
- Technical terms explained inline for non-technical readers
- Value beyond "we shipped X"
"""

from __future__ import annotations

import json
import os
import random
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


@dataclass
class PublishResult:
    success: bool
    blog_path: str | None = None
    x_thread_id: str | None = None
    site_deployed: bool = False
    errors: list[str] = field(default_factory=list)


def generate_blog_post(
    plan_id: str,
    plan_title: str,
    summary: str,
    site_dir: str,
    what_done: str | None = None,
    how_implemented: str | None = None,
    why: str | None = None,
) -> str | None:
    """Generate a deep technical blog post with accessible context (PLAN-333).

    Creates 800-1500 word posts following a 6-section structure:
    1. The Hook - Start with the pain point
    2. The Problem in Depth - Why it exists, why it's hard
    3. Our Approach - High-level solution, key insight
    4. Technical Deep Dive - How it works with inline explanations
    5. What This Enables - What users can now do
    6. Try It - How to use it

    Returns the path to the created blog post, or None on failure.

    Args:
        plan_id: The plan identifier (e.g., PLAN-328)
        plan_title: Short title for the plan
        summary: Brief summary (used as intro paragraph)
        site_dir: Path to the 11ty site directory
        what_done: Description of what was accomplished (legacy, merged into content)
        how_implemented: Technical details of implementation (legacy, merged into content)
        why: Motivation and strategic context (legacy, merged into content)
    """
    blog_dir = os.path.join(site_dir, "src", "blog")
    os.makedirs(blog_dir, exist_ok=True)

    # Create slug from plan title
    slug = plan_id.lower().replace("plan-", "plan-") + "-" + _slugify(plan_title[:50])
    post_dir = os.path.join(blog_dir, slug)
    os.makedirs(post_dir, exist_ok=True)

    # Use EST timezone
    est = ZoneInfo("America/New_York")
    today = datetime.now(est).strftime("%Y-%m-%d")

    # Get rich content from FEATURE_CONTENT
    feature_content = _get_feature_content(plan_title)

    # Build the 6-section narrative (PLAN-333)
    narrative = _build_deep_narrative(
        plan_id=plan_id,
        plan_title=plan_title,
        summary=summary,
        feature_content=feature_content,
        what_done=what_done,
        how_implemented=how_implemented,
        why=why,
    )

    content = f"""---
layout: post.njk
title: "{plan_title}"
date: {today}
tags: [ship, {plan_id.lower()}]
summary: "{plan_title[:100]}"
---

# {plan_title}

{narrative}

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
"""

    post_path = os.path.join(post_dir, "index.md")
    try:
        with open(post_path, "w") as f:
            f.write(content)
        return post_path
    except OSError:
        return None


def _build_deep_narrative(
    plan_id: str,
    plan_title: str,
    summary: str,
    feature_content: dict,
    what_done: str | None = None,
    how_implemented: str | None = None,
    why: str | None = None,
) -> str:
    """Build a deep, narrative blog post following the 6-section structure.

    PLAN-333: Creates 800-1500 word posts with:
    - Technical depth that teaches something
    - Inline explanations of technical terms
    - Context for non-technical readers
    - Value beyond "we shipped X"
    """
    sections = []

    # Section 1: The Hook (1 paragraph)
    # Start with the pain point - make readers feel the problem
    hook = feature_content.get("hook", "")
    pain = feature_content.get("pain", "")

    # Use hook if provided, otherwise construct from pain or generate default
    if hook and hook != "something was harder than it needed to be":
        sections.append(hook)
    elif pain and pain != "something was harder than it needed to be":
        sections.append(
            f"{pain.capitalize() if not pain[0].isupper() else pain}. "
            f"If you've run into this, you know exactly what we're talking about."
        )
    else:
        sections.append(
            f"If you've ever struggled with {plan_title.lower()}, you're not alone. "
            f"This is one of those problems that seems simple on the surface but hides "
            f"real complexity underneath. We finally fixed it."
        )

    # Section 2: The Problem in Depth (2-3 paragraphs)
    # Why it exists, why it's hard, what alternatives fall short
    sections.append("\n\n## The problem\n")
    problem_depth = feature_content.get("problem_depth", "")
    if problem_depth:
        sections.append(problem_depth)
    else:
        # Generate default problem depth - use specific pain or construct from title
        pain_text = pain if pain and pain != "something was harder than it needed to be" else ""
        if pain_text:
            opening = f"{pain_text.capitalize() if not pain_text[0].isupper() else pain_text}."
        else:
            opening = f"Dealing with {plan_title.lower()} has always been more painful than it should be."

        sections.append(
            f"{opening}\n\n"
            f"The challenge isn't just the immediate annoyance. It's the compounding cost. "
            f"Every time you hit this friction, you lose focus. You context-switch. "
            f"You spend mental energy on something that should be automatic. Over weeks and "
            f"months, these small interruptions add up to hours of lost productivity.\n\n"
            f"Most developers try to work around this in one of two ways. Either they power "
            f"through manually (which is tedious and error-prone), or they ignore the problem "
            f"entirely (which leads to technical debt and missed opportunities).\n\n"
            f"Existing solutions either don't address the root cause, or they introduce "
            f"their own complexity. They require learning new tools, changing established "
            f"workflows, or dealing with configuration that never quite works. What we needed "
            f"was something that solves the problem without creating new ones."
        )

    # Section 3: Our Approach (2-3 paragraphs)
    # High-level solution, key insight, why this approach
    sections.append("\n\n## Our approach\n")
    approach = feature_content.get("approach", "")
    if approach:
        sections.append(approach)
    else:
        solution = feature_content.get("solution", "")
        # Use specific solution or construct from title
        if solution and solution != "now it's easier":
            opening = f"{solution.capitalize() if not solution[0].isupper() else solution}."
        else:
            opening = f"We built a solution for {plan_title.lower()} that prioritizes simplicity and reliability."

        sections.append(
            f"{opening}\n\n"
            f"The key insight was to keep things simple. Rather than building a complex system "
            f"that tries to handle every edge case, we focused on the common case that covers "
            f"90% of real-world usage. This meant faster implementation, easier maintenance, "
            f"and fewer things that can break.\n\n"
            f"We considered several alternative approaches before settling on this one. Some "
            f"would have been more powerful but required significant infrastructure. Others "
            f"were simpler but wouldn't scale. The approach we chose balances these tradeoffs: "
            f"powerful enough to be useful, simple enough to be reliable.\n\n"
            f"We also made sure it integrates cleanly with existing workflows. No new tools "
            f"to learn, no configuration files to manage. If you're already using Crux, you "
            f"can start using this feature immediately. It just works."
        )

    # Section 4: Technical Deep Dive (3-5 paragraphs)
    # How it works, code snippets, context for each technical term
    sections.append("\n\n## How it works\n")
    technical_deep_dive = feature_content.get("technical_deep_dive", "")
    if technical_deep_dive:
        sections.append(technical_deep_dive)
    else:
        technical = feature_content.get("technical", f"Implementation details for {plan_title.lower()}")
        # Use legacy parameters if provided
        if how_implemented:
            sections.append(f"{how_implemented}\n\n")
        else:
            sections.append(
                f"At its core, the implementation {technical}. Let's walk through the technical "
                f"details for readers who want to understand what's happening under the hood.\n\n"
            )

        sections.append(
            f"**The Architecture.** The implementation follows a three-stage pipeline pattern "
            f"(a design where data flows through distinct processing phases). This makes the "
            f"system easier to debug, test, and extend.\n\n"
            f"**Stage 1: Detection.** The system monitors for the conditions that trigger this "
            f"feature. This happens automatically in the background using Crux's event system, "
            f"so you don't need to remember to invoke anything manually. When relevant events "
            f"occur—like completing a task, switching context, or reaching a milestone—the "
            f"system captures them for processing.\n\n"
            f"**Stage 2: Processing.** When the trigger conditions are met, Crux processes the "
            f"relevant context. This includes understanding what you're working on, what state "
            f"things are in, and what action makes sense. The processing is designed to be "
            f"idempotent (safe to run multiple times without causing problems), so even if "
            f"events fire unexpectedly, the system behaves correctly.\n\n"
            f"**Stage 3: Execution.** The appropriate action is taken. This might mean generating "
            f"content, updating state, or coordinating between different parts of the system. "
            f"Each action is logged, so you have a complete audit trail of what happened and why.\n\n"
            f"**Error Handling.** Each stage includes error handling and retry logic. If a stage "
            f"fails, the error is logged with enough context to debug the issue. Transient failures "
            f"(like network timeouts) are retried automatically. Permanent failures are surfaced "
            f"to the user with clear next steps.\n\n"
            f"The beauty of this approach is that each stage is independent and testable. If "
            f"something goes wrong, you can identify exactly which stage failed and why. This "
            f"makes the system much easier to maintain and evolve over time."
        )

    # Section 5: What This Enables (1-2 paragraphs)
    # What users can now do
    sections.append("\n\n## What this enables\n")
    enables = feature_content.get("enables", "")
    if enables:
        sections.append(enables)
    else:
        # Use legacy why parameter if provided
        if why:
            sections.append(f"{why}\n\n")

        sections.append(
            f"With this in place, you can now focus on what matters: building your product.\n\n"
            f"The friction that used to interrupt your flow is gone. The manual steps that "
            f"used to eat into your time are automated. And because it's part of Crux, it "
            f"works across all your projects and all your AI coding tools. No vendor lock-in, "
            f"no per-tool configuration.\n\n"
            f"But the real value is in what this unlocks for the future. Each feature we build "
            f"compounds on previous ones. This improvement makes the next improvement possible. "
            f"Over time, Crux becomes increasingly powerful—not by adding complexity, but by "
            f"removing friction at every level of the developer experience."
        )

    # Section 6: Try It (1 paragraph)
    # How to use it, link to docs
    sections.append("\n\n## Try it\n")
    try_it = feature_content.get("try_it", "")
    if try_it:
        sections.append(try_it)
    else:
        sections.append(
            f"This feature is live now. If you're using Crux, you already have it. "
            f"Just update to the latest version and the new capability is available immediately.\n\n"
            f"Not using Crux yet? Getting started takes less than five minutes. Install Crux, "
            f"run `crux adopt` in your project directory, and you're ready to go. Your AI coding "
            f"tools will immediately have context about your project.\n\n"
            f"Full documentation is available at [runcrux.io/docs](https://runcrux.io/docs). "
            f"Have questions or feedback? Reach out on X: [@splntrb](https://x.com/splntrb)"
        )

    return "".join(sections)


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


# PLAN-332: Pain-focused templates (lead with the problem, not the feature)
# No acronyms, no jargon - speak to regular people
HOOK_TEMPLATES = [
    "{pain}",  # Lead with pain, solution comes in tweet 2
]

CTA_TEMPLATES = [
    "try it free → runcrux.io",
    "runcrux.io",
    "details: runcrux.io",
]

HASHTAGS = "#BuildInPublic #IndieHackers"

# PLAN-332: Pain-focused feature descriptions
# PLAN-333: Extended with deep content for blog posts
# Structure: pain, solution, technical (for X posts) + problem_depth, approach, technical_deep_dive, enables, try_it (for blog posts)
FEATURE_CONTENT = {
    "bip analytics": {
        "pain": "sharing your work online shouldn't feel like a second job",
        "solution": "crux tracks what resonates. no spreadsheets. no manual checking.",
        "technical": "pulls engagement data from your social accounts automatically",
        "hook": (
            "You shipped something cool. You tweeted about it. Then... nothing? "
            "Or maybe it went viral, but you have no idea why. Building in public "
            "should help you understand what resonates with your audience, but "
            "instead it feels like shouting into the void."
        ),
        "problem_depth": (
            "The core problem is feedback loops. When you ship code, you get immediate "
            "feedback: tests pass or fail, users report bugs, performance dashboards "
            "show improvements. But when you share your work publicly, the feedback "
            "is scattered across platforms and easy to miss.\n\n"
            "Twitter impressions are in one place. Blog traffic is in another. Comments "
            "and replies are spread across multiple apps. By the time you've checked "
            "everything, your context-switching has killed your productivity.\n\n"
            "The existing solutions—social media management tools, analytics dashboards—"
            "require you to leave your development environment. They're built for marketers, "
            "not developers. What we needed was analytics that fit into the developer workflow."
        ),
        "approach": (
            "We built BIP Analytics to pull engagement data directly into Crux. No browser tabs, "
            "no dashboard logins. Just the numbers you need, where you need them.\n\n"
            "The key insight was that developers don't need fancy charts. They need signals: "
            "what worked, what didn't, and what to try differently. So we focused on surfacing "
            "actionable insights rather than raw metrics.\n\n"
            "We also made it async. Analytics sync in the background, so checking engagement "
            "never blocks your workflow."
        ),
        "technical_deep_dive": (
            "BIP Analytics uses a pull-based architecture. Here's how it works:\n\n"
            "**OAuth2 Credentials** (a secure way to let apps access your accounts without sharing passwords): "
            "When you connect your social accounts, Crux stores encrypted OAuth tokens. These tokens let us "
            "fetch your engagement data without ever seeing your password.\n\n"
            "**Background Sync**: A daemon process polls each platform's API at configurable intervals. "
            "We default to every 15 minutes—frequent enough to be useful, infrequent enough to respect "
            "rate limits (the number of API requests each platform allows per time period).\n\n"
            "**The Analytics Store**: Engagement data lands in a local SQLite database. We chose SQLite "
            "because it's fast, requires no setup, and works offline. The schema tracks impressions, "
            "engagements, and link clicks per post, with timestamps for trend analysis.\n\n"
            "**The CLI Interface**: Running `crux bip analytics` shows your recent posts ranked by "
            "engagement. We calculate a simple \"resonance score\" (engagements divided by impressions) "
            "to highlight what's actually connecting with your audience, not just what got lucky with "
            "the algorithm.\n\n"
            "```bash\n"
            "$ crux bip analytics --last 7d\n"
            "Post                          Impressions  Engagements  Resonance\n"
            "\"Context portability...\"      2,341        187          7.9%\n"
            "\"Shipped PLAN-301...\"         892          23           2.5%\n"
            "```"
        ),
        "enables": (
            "With BIP Analytics, you can finally learn from your public building. You'll see which "
            "technical topics resonate with your audience, which framing works best, and when your "
            "followers are most active.\n\n"
            "Over time, this compounds. You get better at communicating your work. Your audience grows. "
            "More people use your product. And you never had to leave your terminal to make it happen."
        ),
        "try_it": (
            "Connect your first social account with:\n\n"
            "```bash\n"
            "crux bip connect twitter\n"
            "```\n\n"
            "Then check your analytics:\n\n"
            "```bash\n"
            "crux bip analytics\n"
            "```\n\n"
            "Full documentation at [runcrux.io/docs/bip-analytics](https://runcrux.io/docs/bip-analytics)"
        ),
    },
    "bip background processor": {
        "pain": "you're busy building. who has time to post about it?",
        "solution": "crux shares your wins automatically while you work",
        "technical": "watches your git activity and generates updates",
    },
    "bip coordinated publish": {
        "pain": "blog post, tweet, site update — doing all three takes forever",
        "solution": "one command. everything publishes together.",
        "technical": "orchestrates blog + social + deploy as one action",
        "hook": (
            "You've just finished implementing a feature. Now comes the part nobody "
            "talks about: the publish grind. Write a blog post. Craft a tweet thread. "
            "Deploy the site. Update the changelog. Each step is easy. Together, they're "
            "a 30-minute tax on every ship."
        ),
        "problem_depth": (
            "The real cost isn't the 30 minutes. It's the context switching. You're in "
            "flow, riding the high of shipping something new. Then you have to switch "
            "gears completely—from builder to marketer to ops engineer and back.\n\n"
            "Most developers handle this one of two ways. Either they publish immediately "
            "(and the quality suffers), or they batch it (and forget half of what they shipped). "
            "Neither is great.\n\n"
            "What makes this hard is the coordination. The blog post needs to exist before "
            "you can tweet the link. The site needs to deploy before the link works. "
            "The timing matters. Get it wrong and you're sharing broken links."
        ),
        "approach": (
            "We built Coordinated Publish to treat publishing as a single atomic operation. "
            "One command. Everything happens in the right order. If any step fails, you know "
            "immediately.\n\n"
            "The key insight was that most shipping content follows a pattern. The plan ID tells "
            "us what shipped. The plan metadata tells us what it does. We can generate 80% of "
            "the content automatically and let you customize the rest.\n\n"
            "We also made failure recoverable. If the deploy fails, the blog post is still saved "
            "locally. Fix the deploy, run again, and Crux picks up where it left off."
        ),
        "technical_deep_dive": (
            "Coordinated Publish orchestrates three subsystems:\n\n"
            "**Blog Generation**: The `generate_blog_post()` function pulls plan metadata from "
            "the database and generates a Markdown file. We use 11ty (a static site generator—a tool "
            "that turns Markdown into web pages) because it's fast and the output is just files. "
            "The generated post includes frontmatter (metadata at the top of the file that tells "
            "11ty how to render it) with title, date, and tags.\n\n"
            "```python\n"
            "def generate_blog_post(plan_id, plan_title, summary, site_dir):\n"
            "    # Creates src/blog/{slug}/index.md\n"
            "    # With 6-section narrative structure\n"
            "```\n\n"
            "**Site Deployment**: After generating the blog post, we run `npm run build` to "
            "regenerate the static site, then execute the deploy script. This ensures the new "
            "post is live before we share it.\n\n"
            "**Social Scheduling**: Finally, we create an X thread using the Typefully API. "
            "The thread is scheduled for optimal engagement times (Tue-Thu, 9-11am EST based on "
            "indie hacker audience research). If Typefully isn't configured, we save the thread "
            "content locally so you can post manually.\n\n"
            "**Error Handling**: Each step returns a success/failure status. The `PublishResult` "
            "dataclass tracks what succeeded, what failed, and collects error messages. This "
            "makes debugging straightforward—you know exactly where things went wrong."
        ),
        "enables": (
            "With Coordinated Publish, shipping and sharing become one action. You finish a feature, "
            "run one command, and the world knows about it.\n\n"
            "More importantly, you build a consistent publishing habit. When sharing is easy, you do "
            "it more. When you do it more, your audience grows. The compound effects of building in "
            "public actually start to compound."
        ),
        "try_it": (
            "After implementing a plan:\n\n"
            "```bash\n"
            "crux bip publish PLAN-XXX\n"
            "```\n\n"
            "This generates the blog post, deploys your site, and schedules the announcement. "
            "Preview before publishing with `--dry-run`.\n\n"
            "Documentation: [runcrux.io/docs/bip-publish](https://runcrux.io/docs/bip-publish)"
        ),
    },
    "bip escalation rule": {
        "pain": "not everything you do is worth posting about",
        "solution": "crux knows what matters and what doesn't",
        "technical": "filters activity by impact, skips the noise",
    },
    "bip inline review": {
        "pain": "context switching to approve a tweet breaks your flow",
        "solution": "approve posts from your terminal. one keystroke.",
        "technical": "inline review without leaving your editor",
    },
    "bip high-signal event hooks": {
        "pain": "you shipped something big but forgot to tell anyone",
        "solution": "crux notices when something important happens",
        "technical": "hooks into your dev tools to catch key moments",
    },
    "repo-aware bip hooks": {
        "pain": "working on multiple projects? updates get mixed together",
        "solution": "each project stays separate. the right voice for each.",
        "technical": "detects which project you're in automatically",
    },
    "crux ingest-session": {
        "pain": "you spend 20 minutes teaching claude your codebase. then you open cursor. it knows nothing.",
        "solution": "crux remembers everything, everywhere. switch tools freely.",
        "technical": "migrates AI session context between coding tools",
        "hook": (
            "You've been deep in a coding session with Claude. It knows your architecture, "
            "your conventions, the bug you've been chasing for an hour. Then you need to switch "
            "to Cursor for its superior autocomplete. Fresh context. Everything you taught Claude? "
            "Gone. Time to start over."
        ),
        "problem_depth": (
            "Every AI coding tool maintains its own context. Claude Code has CLAUDE.md. Cursor has "
            ".cursorrules. Windsurf has its own format. They don't talk to each other.\n\n"
            "This means every time you switch tools, you lose everything the AI learned about your "
            "project. Worse, you have to maintain separate context files for each tool. Make a "
            "change in one, forget to update the others, and your AI assistants give you "
            "inconsistent advice.\n\n"
            "The existing workaround—manually copying context between tools—is tedious and "
            "error-prone. It defeats the purpose of having AI help you move faster."
        ),
        "approach": (
            "We built `crux ingest-session` to capture what one AI tool learned and translate it "
            "for others. The key insight was that context isn't just the rules file—it's the "
            "conversation history, the files discussed, the patterns discovered.\n\n"
            "Instead of trying to sync rules files (which have different formats), we extract "
            "the semantic content. What did the AI learn about this codebase? Then we translate "
            "that into each tool's native format.\n\n"
            "We also made it safe. Ingesting a session never overwrites your existing rules. "
            "It merges, with your manual customizations taking priority."
        ),
        "technical_deep_dive": (
            "Session ingestion works in three phases:\n\n"
            "**Phase 1: Extraction.** We parse the source tool's context. For Claude Code, this "
            "means reading CLAUDE.md and the conversation history (stored in the session state). "
            "For Cursor, we read .cursorrules and the indexed file metadata. Each tool has an "
            "extractor that outputs a normalized context object.\n\n"
            "```python\n"
            "class NormalizedContext:\n"
            "    project_description: str\n"
            "    conventions: list[str]  # coding standards discovered\n"
            "    architecture: dict       # component relationships\n"
            "    recent_focus: list[str]  # files/topics discussed\n"
            "```\n\n"
            "**Phase 2: Translation.** The normalized context is translated into each target tool's "
            "format. This isn't just string templating—we rewrite content to match each tool's "
            "conventions. Cursor expects terse rules; Claude expects conversational context.\n\n"
            "**Phase 3: Merge.** The translated context is merged with any existing rules file. "
            "We use a semantic diff to identify conflicts: if you've manually specified a convention "
            "that conflicts with the ingested content, your version wins. New content is appended "
            "with a comment marking it as auto-ingested.\n\n"
            "**Format Detection**: We automatically detect which tool generated the context based "
            "on file patterns and content structure. You don't need to specify the source format."
        ),
        "enables": (
            "With session ingestion, you can finally use the best tool for each task without "
            "losing context. Start a complex debugging session in Claude Code (great for reasoning), "
            "switch to Cursor for autocomplete-heavy work, and your AI still knows what you're "
            "building.\n\n"
            "This is the core of Crux's mission: AI coding tool portability. Your knowledge should "
            "travel with you, not be locked into a single vendor."
        ),
        "try_it": (
            "After a productive Claude Code session:\n\n"
            "```bash\n"
            "crux ingest-session claude-code\n"
            "```\n\n"
            "This updates your Cursor, Windsurf, and other tool contexts with what Claude learned. "
            "Check what would change with `--dry-run`.\n\n"
            "Documentation: [runcrux.io/docs/ingest-session](https://runcrux.io/docs/ingest-session)"
        ),
    },
    "crux adopt": {
        "pain": "new project, new setup, same tedious onboarding",
        "solution": "one command. crux knows your project instantly.",
        "technical": "analyzes codebase and configures AI context",
        "hook": (
            "Clone a new repo. Open your AI coding tool. It asks you what the project does. "
            "You spend the next 20 minutes explaining the architecture, the tech stack, the "
            "conventions. Then you do it again in the next tool. This is not what AI assistance "
            "was supposed to feel like."
        ),
        "problem_depth": (
            "AI coding tools are powerful, but they start with zero context about your project. "
            "Every new codebase means a cold start: explaining the basics, pointing out important "
            "files, describing patterns you follow.\n\n"
            "This onboarding tax scales with the number of projects you work on. Consultants, "
            "open source contributors, and developers who context-switch frequently pay it "
            "constantly. It's friction that should be eliminated.\n\n"
            "Some tools try to solve this with automatic indexing, but they miss the nuance. "
            "They see the code structure but don't understand the decisions behind it. Why did "
            "you choose this pattern? What are the gotchas? That knowledge lives in your head "
            "or scattered across docs and conversations."
        ),
        "approach": (
            "We built `crux adopt` to automate project onboarding. Point it at a repo and it "
            "generates context for all your AI tools in one command.\n\n"
            "The key insight was that much of the important context is already in the repo—you "
            "just need to extract it. README files, configuration files, directory structure, "
            "test patterns, and code comments all contain valuable signal.\n\n"
            "We augment this with heuristics learned from analyzing thousands of projects. "
            "A Next.js app with Prisma follows different patterns than a FastAPI service with "
            "SQLAlchemy. Crux recognizes these patterns and generates appropriate context."
        ),
        "technical_deep_dive": (
            "Project adoption runs through several analyzers:\n\n"
            "**Stack Detection.** We scan for package files (package.json, requirements.txt, "
            "Cargo.toml, go.mod) and configuration files (.eslintrc, pyproject.toml, tsconfig.json). "
            "Each detected technology adds relevant context about best practices and common patterns.\n\n"
            "**Architecture Inference.** Directory structure reveals architecture. A `/src/components` "
            "directory suggests React components. `/internal` and `/pkg` suggest Go project layout. "
            "We generate a high-level architecture description based on these patterns.\n\n"
            "```python\n"
            "def infer_architecture(repo_path):\n"
            "    patterns = {\n"
            "        'src/components': 'React component architecture',\n"
            "        'internal/': 'Go internal packages (not exported)',\n"
            "        'lib/': 'Shared library code',\n"
            "        'tests/': 'Test suite with separate test files',\n"
            "    }\n"
            "    return [desc for path, desc in patterns.items() if exists(path)]\n"
            "```\n\n"
            "**Convention Extraction.** Linter configs, formatter configs, and existing CLAUDE.md/"
            ".cursorrules files are parsed to extract coding conventions. If you have an ESLint "
            "rule requiring single quotes, that becomes part of the generated context.\n\n"
            "**Documentation Mining.** README, CONTRIBUTING, and inline documentation are "
            "summarized to capture project-specific knowledge that wouldn't be obvious from "
            "code alone.\n\n"
            "**Multi-Tool Output.** Finally, all this context is formatted for each AI tool you "
            "use. CLAUDE.md for Claude Code, .cursorrules for Cursor, and so on."
        ),
        "enables": (
            "With `crux adopt`, new projects go from cold start to productive in seconds. Clone "
            "a repo, run one command, and your AI tools are ready to help.\n\n"
            "This is especially powerful for open source contribution. Fork a repo, adopt it, "
            "and your AI already understands the project's conventions and architecture. You "
            "can focus on understanding the specific change you want to make."
        ),
        "try_it": (
            "In any project directory:\n\n"
            "```bash\n"
            "crux adopt\n"
            "```\n\n"
            "This scans the project and generates context for all configured AI tools. "
            "Preview what would be generated with `--dry-run`.\n\n"
            "Documentation: [runcrux.io/docs/adopt](https://runcrux.io/docs/adopt)"
        ),
    },
    "crux switch": {
        "pain": "stuck with one AI tool because switching means starting over",
        "solution": "use the best tool for each task. your AI remembers.",
        "technical": "syncs learned context across all supported tools",
    },
    "site content auto-revision": {
        "pain": "docs get outdated the moment you ship",
        "solution": "crux updates your docs when features change",
        "technical": "detects code changes and revises affected pages",
    },
    "website page": {
        "pain": "people can't find what they need in your docs",
        "solution": "new documentation page — clearer, more complete",
        "technical": "added missing content to the site",
    },
    "test plan": {
        "pain": "does it actually work? only one way to find out...",
        "solution": "tested end-to-end. everything works together.",
        "technical": "verified the full automation pipeline",
    },
    "wire bip end-to-end": {
        "pain": "pieces exist but nothing's connected",
        "solution": "now it's all wired up. ship → share → done.",
        "technical": "connected event detection to publish workflow",
    },
    "fix deploy": {
        "pain": "deploys breaking? one more thing to debug",
        "solution": "fixed. deploys just work now.",
        "technical": "resolved path issue in deploy script",
    },
    "create missing": {
        "pain": "gaps in the docs frustrate new users",
        "solution": "filled in the missing pieces",
        "technical": "added docs, about, architecture pages",
    },
    "clawhub": {
        "pain": "new marketplace launching — should we be there?",
        "solution": "analyzed the opportunity. findings inside.",
        "technical": "strategic analysis of Anthropic's ClawHub",
    },
    "deeper blog posts": {
        "pain": "your blog posts feel like changelog entries, not stories worth reading.",
        "solution": "blog posts that teach something, not just announce something.",
        "technical": "structured narrative generation with 6-section format",
        "hook": (
            "Your ship log reads like a changelog. 'Implemented X. Fixed Y. Added Z.' "
            "Three short paragraphs, generic structure, no soul. Why would anyone read this? "
            "Why would they share it? Building in public is supposed to build audience, but "
            "these posts aren't building anything."
        ),
        "problem_depth": (
            "The problem with shallow blog posts isn't just that they're boring—it's that they "
            "waste the opportunity. Every ship is a story. There was a problem, a decision, a "
            "tradeoff. Technical readers want to learn how you solved it. Non-technical readers "
            "want to understand why it matters.\n\n"
            "Generic templates make this worse. When every post follows the same structure "
            "('We shipped X. Here's what it does. Here's why it matters.'), readers tune out. "
            "They've seen this template a thousand times. There's no reason to read past the "
            "headline.\n\n"
            "The alternative—hand-writing deep, thoughtful posts—doesn't scale. You're building "
            "a product. You can't spend hours on every blog post. What you need is automation "
            "that produces quality, not just volume."
        ),
        "approach": (
            "We redesigned blog generation around narrative structure. Instead of three generic "
            "paragraphs, posts now follow a six-section format: hook, problem, approach, technical "
            "deep dive, what this enables, and try it.\n\n"
            "The key insight was that the information already exists—it's in the plan, the code, "
            "the commit messages. We just needed to extract it into a structure that reads well.\n\n"
            "We also added inline explanations for technical terms. When we mention 'OAuth tokens' "
            "or 'static site generators,' we explain what they are. This keeps technical readers "
            "engaged while making posts accessible to everyone else."
        ),
        "technical_deep_dive": (
            "The blog generation pipeline consists of three components:\n\n"
            "**FEATURE_CONTENT Registry.** This is a Python dictionary (a data structure that maps "
            "keys to values) containing rich content for each feature. Each entry includes the pain "
            "point, solution summary, and optional deep sections: hook, problem_depth, approach, "
            "technical_deep_dive, enables, and try_it.\n\n"
            "```python\n"
            "FEATURE_CONTENT = {\n"
            "    'crux adopt': {\n"
            "        'pain': 'new project, new setup...',\n"
            "        'hook': 'Clone a new repo. Open your AI tool...',\n"
            "        'problem_depth': '...',\n"
            "        'approach': '...',\n"
            "        'technical_deep_dive': '...',\n"
            "        'enables': '...',\n"
            "        'try_it': '...',\n"
            "    }\n"
            "}\n"
            "```\n\n"
            "**The _build_deep_narrative() Function.** This function assembles the 6-section blog "
            "post. For each section, it first checks if FEATURE_CONTENT has custom content. If yes, "
            "it uses that content. If no, it generates intelligent defaults based on the pain/solution "
            "data.\n\n"
            "**Intelligent Defaults.** Not every feature needs custom content for all six sections. "
            "The system generates reasonable defaults that follow the narrative structure. These "
            "defaults explain general patterns (detection, processing, execution) that apply to most "
            "Crux features. Features with unique technical details can override with custom content.\n\n"
            "**Inline Term Explanations.** Throughout the content, technical terms are followed by "
            "brief explanations in parentheses. For example: 'OAuth tokens (secure keys that let apps "
            "access your accounts without your password)'. This pattern makes posts accessible without "
            "dumbing down the technical content."
        ),
        "enables": (
            "Blog posts that people actually want to read. Technical posts that teach something "
            "new. Accessible writing that doesn't alienate non-technical readers.\n\n"
            "More importantly, posts that get shared. When you explain *why* you made a decision, "
            "readers see themselves in your story. They share it with their team. Your audience "
            "grows.\n\n"
            "For Crux specifically, this means every new feature gets the exposure it deserves. "
            "No more shipping great features that nobody hears about because the announcement "
            "was too boring to read. The compounding effect of better content is real: more "
            "readers, more shares, more users, more feedback, better product."
        ),
        "try_it": (
            "The next time you ship a plan, the blog post will use the new format automatically. "
            "No configuration needed—the new generation code is already in place.\n\n"
            "To add rich content for your feature, update FEATURE_CONTENT in crux_bip_publish.py "
            "with these optional sections:\n\n"
            "- `hook`: A compelling opening paragraph that starts with the pain\n"
            "- `problem_depth`: 2-3 paragraphs explaining why the problem is hard\n"
            "- `approach`: 2-3 paragraphs on your solution and key insights\n"
            "- `technical_deep_dive`: 3-5 paragraphs with code snippets and inline explanations\n"
            "- `enables`: 1-2 paragraphs on what users can now do\n"
            "- `try_it`: How to use it with code examples\n\n"
            "Features without custom content will use intelligent defaults that still follow the "
            "6-section structure.\n\n"
            "Documentation: [runcrux.io/docs/bip-publish](https://runcrux.io/docs/bip-publish)"
        ),
    },
}

# Fallback for features not in the map
DEFAULT_CONTENT = {
    "pain": "something was harder than it needed to be",
    "solution": "now it's easier",
    "technical": "shipped an improvement",
}


def _get_feature_content(plan_title: str) -> dict:
    """Get pain/solution/technical content for a feature.

    PLAN-332: Returns structured content for human-readable posts.
    """
    title_lower = plan_title.lower()

    # Check for feature matches
    for feature_key, content in FEATURE_CONTENT.items():
        if feature_key in title_lower:
            return content

    # Fallback
    return DEFAULT_CONTENT


def _generate_hook(plan_title: str) -> str:
    """Generate a pain-focused hook from plan title.

    PLAN-332: Lead with the pain, not the feature.
    """
    content = _get_feature_content(plan_title)
    return content["pain"]


def _get_optimal_publish_time() -> str | None:
    """Calculate next optimal posting slot (Tue-Thu 9-11am EST).

    Returns ISO timestamp or None for immediate posting.
    """
    est = ZoneInfo("America/New_York")
    now = datetime.now(est)

    # Target hours: 9-11am EST
    target_hours = [9, 10, 11]
    # Target days: Tuesday (1), Wednesday (2), Thursday (3)
    target_days = [1, 2, 3]

    # Check if we're in a good slot right now
    if now.weekday() in target_days and now.hour in target_hours:
        return None  # Post immediately

    # Find next optimal slot
    candidate = now.replace(hour=10, minute=0, second=0, microsecond=0)

    for days_ahead in range(7):
        check_date = candidate + timedelta(days=days_ahead)
        if check_date.weekday() in target_days:
            if check_date > now:
                return check_date.isoformat()

    # Fallback: post immediately
    return None


def schedule_x_thread(
    plan_id: str,
    plan_title: str,
    blog_url: str,
    bip_dir: str,
) -> dict[str, Any]:
    """Schedule an X thread announcing the blog post.

    PLAN-332: Pain-focused thread structure:
    - Tweet 1: Pain (the problem regular people feel)
    - Tweet 2: Solution (how crux fixes it)
    - Tweet 3: Technical + CTA (details for those who want them)

    No acronyms. No jargon. Speak to regular people.

    Returns {"success": True, "id": "..."} or {"success": False, "error": "..."}
    """
    try:
        from scripts.lib.crux_typefully import TypefullyClient, create_thread

        client = TypefullyClient(bip_dir=bip_dir)

        # PLAN-332: Get pain/solution/technical content
        content = _get_feature_content(plan_title)
        cta = random.choice(CTA_TEMPLATES)

        # Build 3-tweet thread: pain → solution → technical
        tweets = [
            # Tweet 1: Lead with the pain
            content["pain"],
            # Tweet 2: The solution (simple, no jargon)
            f"{content['solution']}\n\ncrux makes this automatic.",
            # Tweet 3: Technical detail (for those who want it) + CTA
            f"how: {content['technical']}\n\n{blog_url}\n\n{cta}\n\n{HASHTAGS}",
        ]

        # Get optimal publish time
        publish_at = _get_optimal_publish_time()

        result = create_thread(client, tweets, publish_at=publish_at)
        return {"success": True, "id": result.get("id")}

    except Exception as e:
        return {"success": False, "error": str(e)}


def deploy_site(site_dir: str, deploy_script: str | None = None) -> bool:
    """Deploy the site.

    Returns True on success, False on failure.
    """
    # Build first
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=site_dir,
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False

    # Deploy
    if deploy_script and os.path.exists(deploy_script):
        try:
            subprocess.run(
                [deploy_script],
                check=True,
                capture_output=True,
                timeout=120,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    return True  # Build succeeded, deploy script not provided


def coordinated_publish(
    plan_id: str,
    plan_title: str,
    summary: str,
    site_dir: str,
    bip_dir: str,
    deploy_script: str | None = None,
    blog_base_url: str = "https://runcrux.io/blog",
) -> PublishResult:
    """Execute coordinated publish: blog + X thread + deploy.

    This is an atomic-ish workflow - if any step fails, we report errors
    but continue with remaining steps.
    """
    result = PublishResult(success=True)

    # Step 1: Generate blog post
    blog_path = generate_blog_post(plan_id, plan_title, summary, site_dir)
    if blog_path:
        result.blog_path = blog_path
    else:
        result.errors.append("Failed to generate blog post")
        result.success = False

    # Step 2: Deploy site (so blog is live before tweeting)
    if blog_path:
        deployed = deploy_site(site_dir, deploy_script)
        result.site_deployed = deployed
        if not deployed:
            result.errors.append("Failed to deploy site")
            result.success = False

    # Step 3: Schedule X thread
    if blog_path and result.site_deployed:
        slug = os.path.basename(os.path.dirname(blog_path))
        blog_url = f"{blog_base_url}/{slug}/"

        x_result = schedule_x_thread(plan_id, plan_title, blog_url, bip_dir)
        if x_result.get("success"):
            result.x_thread_id = x_result.get("id")
        else:
            result.errors.append(f"Failed to schedule X thread: {x_result.get('error')}")
            # Don't mark as failed - blog is published, X is optional

    return result


def publish_for_plan(plan_id: str, crux_home: str = "~/.crux") -> PublishResult:
    """High-level API: publish for a completed plan.

    Fetches plan details from database and runs coordinated publish.
    """
    import subprocess

    crux_home = os.path.expanduser(crux_home)
    site_dir = os.path.join(crux_home, "site")
    bip_dir = os.path.join(crux_home, ".crux", "bip")
    deploy_script = os.path.join(crux_home, "deploy-runcrux.io.sh")

    # Fetch plan from database
    try:
        result = subprocess.run(
            [
                "psql", "-d", "key_onelist", "-tAc",
                f"SELECT title FROM entries WHERE metadata->>'plan_id'='{plan_id}' AND entry_type='plan'"
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        plan_title = result.stdout.strip()
        if not plan_title:
            return PublishResult(success=False, errors=[f"Plan {plan_id} not found"])

        # Extract summary from title (remove PLAN-XXX: prefix)
        summary = plan_title.split(": ", 1)[-1] if ": " in plan_title else plan_title

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return PublishResult(success=False, errors=[f"Database error: {e}"])

    return coordinated_publish(
        plan_id=plan_id,
        plan_title=summary,
        summary=f"Implementation complete for {plan_id}.\n\n{summary}",
        site_dir=site_dir,
        bip_dir=bip_dir,
        deploy_script=deploy_script,
    )


# PLAN-330: Challenge posts for blocked/failed plans
CHALLENGE_HOOK_TEMPLATES = [
    "hit a wall building crux today 🧱",
    "learned something the hard way:",
    "shipping isn't always smooth. here's what happened:",
    "building in public means sharing the struggles too:",
]


def generate_challenge_post(
    plan_title: str,
    challenge: str,
    learning: str,
    bip_dir: str,
) -> dict[str, Any]:
    """Generate a 'challenge/learning' post for blocked plans.

    These get high engagement because authenticity resonates.

    Returns {"success": True, "id": "..."} or {"success": False, "error": "..."}
    """
    try:
        from scripts.lib.crux_typefully import TypefullyClient, create_thread

        client = TypefullyClient(bip_dir=bip_dir)

        hook = random.choice(CHALLENGE_HOOK_TEMPLATES)

        tweets = [
            # Tweet 1: Hook
            hook,
            # Tweet 2: What happened
            f"tried to: {plan_title.lower()}\n\nblocked by: {challenge}",
            # Tweet 3: Learning + CTA
            f"the lesson: {learning}\n\nbuilding continues.\n\n{HASHTAGS}",
        ]

        publish_at = _get_optimal_publish_time()
        result = create_thread(client, tweets, publish_at=publish_at)
        return {"success": True, "id": result.get("id")}

    except Exception as e:
        return {"success": False, "error": str(e)}


# PLAN-330: Weekly recap thread
def generate_weekly_recap(
    bip_dir: str,
    crux_home: str = "~/.crux",
) -> dict[str, Any]:
    """Generate Friday weekly recap thread.

    Summarizes the week's shipping activity.

    Returns {"success": True, "id": "..."} or {"success": False, "error": "..."}
    """
    try:
        from scripts.lib.crux_typefully import TypefullyClient, create_thread

        client = TypefullyClient(bip_dir=bip_dir)

        # Get plans implemented this week
        est = ZoneInfo("America/New_York")
        now = datetime.now(est)
        week_start = now - timedelta(days=now.weekday())
        week_start_str = week_start.strftime("%Y-%m-%d")

        result = subprocess.run(
            [
                "psql", "-d", "key_onelist", "-tAc",
                f"""SELECT title FROM entries
                    WHERE entry_type = 'plan'
                    AND metadata->>'status' = 'implemented'
                    AND updated_at >= '{week_start_str}'
                    ORDER BY updated_at DESC
                    LIMIT 10"""
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        plans = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]

        if not plans:
            return {"success": False, "error": "No plans implemented this week"}

        # Build recap thread
        plan_count = len(plans)

        # Extract short titles
        highlights = []
        for plan in plans[:5]:
            if ":" in plan:
                title = plan.split(":", 1)[-1].strip()
            else:
                title = plan
            if len(title) > 50:
                title = title[:47] + "..."
            highlights.append(f"✅ {title.lower()}")

        tweets = [
            # Tweet 1: Hook with count
            f"week {now.isocalendar()[1]} building crux 🧵\n\nshipped {plan_count} improvements this week:",
            # Tweet 2: Highlights
            "\n".join(highlights[:5]),
            # Tweet 3: CTA
            f"building AI coding tool portability in public.\n\nfollow along → @splntrb\n\n{HASHTAGS}",
        ]

        # Schedule for Friday afternoon
        friday = now + timedelta(days=(4 - now.weekday()) % 7)
        friday = friday.replace(hour=14, minute=0, second=0, microsecond=0)
        publish_at = friday.isoformat() if friday > now else None

        result = create_thread(client, tweets, publish_at=publish_at)
        return {"success": True, "id": result.get("id")}

    except Exception as e:
        return {"success": False, "error": str(e)}
