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
    """Generate a narrative blog post for a completed plan.

    Returns the path to the created blog post, or None on failure.

    Args:
        plan_id: The plan identifier (e.g., PLAN-328)
        plan_title: Short title for the plan
        summary: Brief summary (used as intro paragraph)
        site_dir: Path to the 11ty site directory
        what_done: Description of what was accomplished (paragraph 2)
        how_implemented: Technical details of implementation (paragraph 3)
        why: Motivation and strategic context (paragraph 4)
    """
    blog_dir = os.path.join(site_dir, "src", "blog")
    os.makedirs(blog_dir, exist_ok=True)

    # Create slug from plan title
    slug = plan_id.lower().replace("plan-", "plan-") + "-" + _slugify(plan_title[:50])
    post_dir = os.path.join(blog_dir, slug)
    os.makedirs(post_dir, exist_ok=True)

    # Use EST timezone
    from zoneinfo import ZoneInfo
    est = ZoneInfo("America/New_York")
    today = datetime.now(est).strftime("%Y-%m-%d")

    # Build narrative content (3-4 paragraphs minimum)
    narrative_parts = [summary]

    if what_done:
        narrative_parts.append(f"\n\n## What we shipped\n\n{what_done}")
    else:
        narrative_parts.append(f"\n\n## What we shipped\n\nThis plan delivered {plan_title.lower()}. The implementation is now live and integrated into the Crux system.")

    if how_implemented:
        narrative_parts.append(f"\n\n## How it works\n\n{how_implemented}")
    else:
        narrative_parts.append(f"\n\n## How it works\n\nThe implementation followed Crux's standard patterns for extensibility and maintainability. Code changes were kept minimal and focused on the specific requirements.")

    if why:
        narrative_parts.append(f"\n\n## Why it matters\n\n{why}")
    else:
        narrative_parts.append(f"\n\n## Why it matters\n\nThis feature continues Crux's mission to make AI coding tools portable and intelligent. Every improvement compounds, making the system more valuable for developers who refuse to be locked into a single vendor.")

    narrative = "".join(narrative_parts)

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


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


# PLAN-330: Outcome-focused hook templates (no plan IDs)
HOOK_TEMPLATES = [
    "just shipped: {outcome} ✅",
    "new in crux: {outcome}",
    "shipped: {outcome}",
    "{outcome} — now live in crux",
]

CTA_TEMPLATES = [
    "what should I ship next?",
    "follow the journey → @splntrb",
    "building crux in public. more soon.",
    "try it: runcrux.io",
]

HASHTAGS = "#BuildInPublic #IndieHackers"


def _generate_hook(plan_title: str) -> str:
    """Generate an outcome-focused hook from plan title."""
    # Clean up title - remove "PLAN-XXX:" prefix if present
    outcome = plan_title
    if ":" in outcome:
        outcome = outcome.split(":", 1)[-1].strip()
    # Lowercase for casual tone
    outcome = outcome.lower()
    # Truncate if too long
    if len(outcome) > 80:
        outcome = outcome[:77] + "..."

    template = random.choice(HOOK_TEMPLATES)
    return template.format(outcome=outcome)


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

    PLAN-330: Generates proper 3-tweet thread with:
    - Outcome-focused hook (no plan ID)
    - What it does + why it matters
    - CTA + link + hashtags
    - Optimal scheduling (Tue-Thu 9-11am EST)

    Returns {"success": True, "id": "..."} or {"success": False, "error": "..."}
    """
    try:
        from scripts.lib.crux_typefully import TypefullyClient, create_thread

        client = TypefullyClient(bip_dir=bip_dir)

        # Generate hook from title
        hook = _generate_hook(plan_title)
        cta = random.choice(CTA_TEMPLATES)

        # Build 3-tweet thread
        tweets = [
            # Tweet 1: Hook
            hook,
            # Tweet 2: What + context
            f"{plan_title.lower()}\n\nyour AI coding tools just got smarter. details 👇",
            # Tweet 3: CTA + link + hashtags
            f"{blog_url}\n\n{cta}\n\n{HASHTAGS}",
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
