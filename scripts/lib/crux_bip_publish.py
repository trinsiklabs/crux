"""BIP coordinated publish: blog post + X thread + site deploy as atomic workflow.

PLAN-309: When a plan is implemented, this orchestrates:
1. Generate blog post from plan content
2. Schedule X thread announcing the post
3. Deploy updated site
4. All as one atomic operation
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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
) -> str | None:
    """Generate a blog post for a completed plan.

    Returns the path to the created blog post, or None on failure.
    """
    blog_dir = os.path.join(site_dir, "src", "blog")
    os.makedirs(blog_dir, exist_ok=True)

    # Create slug from plan title
    slug = plan_id.lower().replace("plan-", "plan-") + "-" + _slugify(plan_title[:50])
    post_dir = os.path.join(blog_dir, slug)
    os.makedirs(post_dir, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content = f"""---
layout: post.njk
title: "{plan_title}"
date: {today}
tags: [ship, {plan_id.lower()}]
---

# {plan_title}

{summary}

---

*Shipped as part of [{plan_id}](https://github.com/someuser/crux/issues/{plan_id.replace('PLAN-', '')})*
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


def schedule_x_thread(
    plan_id: str,
    plan_title: str,
    blog_url: str,
    bip_dir: str,
) -> dict[str, Any]:
    """Schedule an X thread announcing the blog post.

    Returns {"success": True, "thread_id": "..."} or {"success": False, "error": "..."}
    """
    try:
        from scripts.lib.crux_typefully import TypefullyClient, queue_draft

        client = TypefullyClient(bip_dir=bip_dir)

        # Thread format: 3 tweets
        thread_content = f"""just shipped {plan_id}: {plan_title}

details in the blog post 👇

---

{blog_url}

---

build in public. ship every day. crux makes it automatic."""

        result = queue_draft(client, thread_content)
        return result

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
