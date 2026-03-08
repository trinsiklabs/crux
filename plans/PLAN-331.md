# PLAN-331: X posts - human-readable language + why it matters

**Status:** planned
**Group:** GROUP-MKT
**Domain:** crux
**Risk:** 0.20

## Problem

Current X posts are too technical:
- "BIP background processor daemon" → meaningless to most people
- "Wire hooks to fire triggers" → developer jargon
- Missing the "so what?" — why should anyone care?

## Solution

### 1. Translate Technical → Human

| Technical | Human-Readable |
|-----------|----------------|
| "BIP background processor daemon" | "auto-posts your wins while you work" |
| "crux ingest-session" | "picks up where you left off in any tool" |
| "repo-aware hooks" | "knows which project you're in" |
| "escalation rules" | "decides what's worth sharing" |
| "coordinated publish" | "blog + tweet + deploy in one click" |

### 2. Add "Why It Matters" Context

Every post needs a human benefit statement:

**Before:**
```
shipped: bip analytics - engagement tracking from typefully api
```

**After:**
```
shipped: now I can see which posts resonate ✅

no more guessing what content works.
crux tracks engagement automatically.

why it matters: build in public without the busywork
```

### 3. Thread Structure Update

**Tweet 1 (Hook):** Outcome in plain English
**Tweet 2 (What):** Simple explanation + human benefit
**Tweet 3 (Why + CTA):** Why it matters + link + hashtags

### 4. Translation Mapping

Create a mapping layer that converts plan titles to human-readable versions:

```python
HUMAN_TRANSLATIONS = {
    "BIP": "build-in-public automation",
    "daemon": "background worker",
    "hooks": "automatic triggers",
    "MCP": "AI tool connector",
    "ingest": "import",
    "escalation": "priority routing",
    "coordinated publish": "one-click publishing",
}

WHY_IT_MATTERS = {
    "analytics": "know what content works without manual tracking",
    "session migration": "never lose your AI's context when switching tools",
    "background processor": "ship updates while you focus on building",
    "inline review": "approve posts without leaving your terminal",
    "repo-aware": "each project gets its own voice automatically",
}
```

## Examples

### Example 1: BIP Analytics

**Before:**
```
shipped: bip analytics: engagement tracking from typefully api

your AI coding tools just got smarter. details 👇

https://runcrux.io/blog/...

#BuildInPublic #IndieHackers
```

**After:**
```
shipped: now I know which posts actually work ✅

crux tracks likes, RTs, and replies automatically.
no more spreadsheets or manual checking.

why: build in public should feel effortless, not like a second job

https://runcrux.io/blog/...

#BuildInPublic #IndieHackers
```

### Example 2: Session Migration

**Before:**
```
shipped: crux ingest-session - background daemon for claude code session migration

your AI coding tools just got smarter. details 👇
```

**After:**
```
shipped: switch AI tools without starting over ✅

worked in claude code all morning?
now continue in cursor or aider.
your AI remembers everything.

why: your intelligence shouldn't be trapped in one app

https://runcrux.io/blog/...

#BuildInPublic #IndieHackers
```

### Example 3: Coordinated Publish

**Before:**
```
shipped: bip coordinated publish: blog post + scheduled x thread + site deploy
```

**After:**
```
shipped: one command publishes everywhere ✅

finish a feature → crux writes the blog post,
schedules the tweet, and deploys the site.
all automatic.

why: shipping is hard enough without the marketing busywork

https://runcrux.io/blog/...

#BuildInPublic #IndieHackers
```

## Implementation

1. Add `HUMAN_TRANSLATIONS` dict to `crux_bip_publish.py`
2. Add `WHY_IT_MATTERS` context generator
3. Update `_generate_hook()` to use translations
4. Update thread generation to include "why" in tweet 3
5. Regenerate queued Typefully drafts

## Files to Modify

- `/home/key/.crux/scripts/lib/crux_bip_publish.py`

## Success Criteria

- [ ] Non-developer can understand what was shipped
- [ ] Every post answers "why should I care?"
- [ ] No unexplained acronyms (BIP, MCP, etc.)
- [ ] Benefits are concrete and relatable
