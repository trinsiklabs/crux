# PLAN-330: X Post Writing Improvements for Build-in-Public

**Status:** planned (recommendations ready for review)
**Group:** GROUP-MKT
**Domain:** crux
**Risk:** 0.20

## Research Summary

Deep research on X post best practices for build-in-public software products based on 25+ sources including indie hacker communities, Twitter marketing guides, and analysis of 10 successful BIP accounts (@levelsio, @tdinh_me, @arvidkahl, @dvassallo, etc.).

---

## Key Findings

### 1. Thread Structure

**Optimal length:** 5-10 tweets, with **7 tweets being the sweet spot**

**Proven 7-Part Framework:**
1. **Hook** - Compelling insight + specific numbers + curiosity gap
2. **Context** - Background establishing credibility
3. **Core Content (3-4 tweets)** - One key insight per tweet
4. **Engagement Driver** - Question requesting reply
5. **CTA** - Direct next step

**For shipping updates:** 3 tweets is optimal (hook → what → CTA)

### 2. Hooks That Work

| Formula | Example |
|---------|---------|
| **Contrarian** | "You don't need [X]. You need [Y]." |
| **Before/After** | "I went from [X] to [Y] in [time]. Here's how:" |
| **Hard Truth** | "Hard truth about [X]: [uncomfortable reality]" |
| **Numbers + Promise** | "I analyzed [X] [things] and found [insight]" |
| **Vulnerable** | "[Time] ago I [struggle]. Today I [win]. The difference:" |

**Key insight:** Top creators write **10-15 hook versions** before choosing.

### 3. Formatting Standards

| Element | Best Practice |
|---------|---------------|
| **Tweet length** | Under 200 chars (110 optimal for singles) |
| **Emojis** | 1-3 functional only (✅ 🔥 👇 📈) |
| **Hashtags** | 1-2 max (#BuildInPublic + niche) |
| **Line breaks** | Liberal use for readability |
| **Visuals** | Video 10x, GIF 6x, Image 3x engagement boost |

### 4. Timing

**Best times (EST):**
- Primary: 9-11 AM Tuesday-Thursday
- Secondary: 12-2 PM Tuesday-Thursday

**Frequency:**
- Under 5K followers: 3-5 posts/day
- 5K-50K: 1-3 posts/day
- Consistency > volume (no 10-post days then silence)

### 5. Engagement Triggers

| Action | Boost |
|--------|-------|
| Questions | +334% replies |
| "Retweet" spelled out | +311% RTs |
| "Bookmark this" | Increases saves |
| Screenshot/metrics | +300% engagement |

### 6. Content Mix (Weekly)

- 60% Progress/shipping updates
- 20% Learnings/insights
- 10% Challenges/failures (high engagement!)
- 10% Behind-the-scenes

---

## Implementation Recommendations

### Phase 1: Thread Generation (Priority)

**Current:** Single tweet per shipping event
**Change:** 3-tweet thread

```
Tweet 1 (Hook):
just made AI coding tools portable ✅

[what the outcome is, not plan ID]

Tweet 2 (What):
shipped: crux session migration

your claude code learnings now work in cursor, aider, opencode
no more starting over when switching tools

Tweet 3 (CTA + Link):
details on the blog 👇
runcrux.io/blog/[slug]

#BuildInPublic
```

### Phase 2: Hook Templates

Replace generic "shipped PLAN-XXX" with outcome-focused hooks:

```python
HOOK_TEMPLATES = [
    "just {outcome} ✅",
    "{metric} → {new_metric} in {timeframe}",
    "shipped: {feature_name}",
    "day {N} building crux: {highlight}",
    "{problem}? fixed. here's how:",
]
```

### Phase 3: Scheduling Optimization

```python
def get_optimal_slot():
    # Target: Tue-Thu 9-11am or 12-2pm EST
    # If outside window, schedule for next optimal slot
    pass
```

### Phase 4: Visual Support

- Auto-screenshot for applicable features
- Code snippets via ray.so API
- Revenue/metrics dashboards

### Phase 5: Weekly Recap Thread

Auto-generate weekly thread every Friday:
```
This week building Crux:

✅ [Plans implemented count]
📈 [Key metric if available]
🔧 [Feature highlights]

What's working: [auto-extract from plan descriptions]

Thread 🧵
```

---

## Post Templates for BIP

### Daily Progress
```
Day [X] building Crux:

Shipped [feature/fix]
[Single sentence on why it matters]

[Screenshot]

Tomorrow: [next priority]
```

### Feature Launch
```
Just shipped: [feature name]

Before: [problem]
After: [solution]

[Screenshot/GIF]

Took [time]. Worth it.

What feature should I build next?
```

### Learning/Failure (high engagement!)
```
I [messed up] building Crux this week:

[Brief setup]
[What happened]
[What I learned]

Don't [make this mistake].
```

---

## Files to Modify

1. `/home/key/.crux/scripts/lib/crux_typefully.py` - Thread generation
2. `/home/key/.crux/scripts/lib/crux_bip_publish.py` - Hook templates
3. `/home/key/.crux/scripts/lib/crux_bip.py` - Event types for content variety

---

## Questions for Review

1. **Plan IDs in posts?** Research suggests outcomes > identifiers. Drop or keep?
2. **Hashtag count?** Research says 1-2 max. Currently using 0.
3. **Challenge posts?** Auto-generate "failure/learning" posts from blocked plans?
4. **Weekly recap?** Auto-generate Friday summary thread?
5. **Screenshot automation?** Worth the complexity?

---

## Sources

- [Highperformr: Twitter for Indie Hackers](https://www.highperformr.ai/blog/twitter-for-indie-hackers)
- [Wisp CMS: Build in Public Guide](https://www.wisp.blog/blog/how-to-get-started-with-build-in-public-on-x-a-complete-guide)
- [Tweet Archivist: Thread Writing Masterclass 2025](https://www.tweetarchivist.com/twitter-thread-writing-masterclass-2025)
- [The Bootstrapped Founder: How I Use Twitter](https://thebootstrappedfounder.com/how-i-use-twitter/)
- [Failory: How to Build in Public](https://www.failory.com/blog/building-in-public)
- [Buffer: Best Time to Post 2025](https://buffer.com/resources/best-time-to-post-on-twitter-x/)
- Analysis of @levelsio, @tdinh_me, @arvidkahl, @dvassallo patterns
