---
layout: post.njk
title: "Fix deploy-runcrux.io.sh Path Issue"
date: 2026-03-08
tags: [ship, plan-306]
---

# Fix deploy-runcrux.io.sh Path Issue

Small bugs in deployment scripts have outsized impact. Today we fixed a path resolution issue in our automated deploy script that was causing silent failures in CI environments.

## What We Shipped

The fix addressed a path resolution bug in `deploy-runcrux.io.sh` where relative paths broke when the script was invoked from directories other than the repo root. This manifested as successful local deploys but failed automated deploys from CI/CD pipelines. The fix ensures consistent behavior regardless of the working directory at invocation time.

## How It Works

The root cause was using `./` relative paths for the build output directory instead of deriving paths from the script's own location. We replaced relative references with `$(dirname "$0")` resolution, ensuring the script can locate its resources regardless of where it's called from. We also added explicit validation that required directories exist before attempting operations, providing clearer error messages when dependencies are missing.

## Why It Matters

Automated deploys are the foundation of continuous delivery. When they fail silently, you accumulate deploy debt and risk shipping stale content. This was blocking our entire BIP (Build In Public) workflow because blog posts were being generated but never reaching production. With this fix, the full automation chain works end-to-end: event triggers draft, approval publishes, and deploy script pushes to production.

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
