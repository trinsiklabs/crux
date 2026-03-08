# PLAN-332: Eliminate jargon and acronyms from X posts

**Status:** planned
**Group:** GROUP-MKT
**Domain:** crux
**Risk:** 0.15

## Problem

Current posts still use insider language:
- "BIP" - nobody knows this means "build in public"
- "MCP" - meaningless to most people
- "hooks", "daemons", "escalation" - developer jargon
- Even "build in public" needs explanation

Regular people don't know they need crux. They don't even know:
- That AI coding tools trap their learning
- That switching tools means starting over
- That their corrections disappear

## Solution

### 1. Ban All Acronyms

| Banned | Replacement |
|--------|-------------|
| BIP | (remove entirely or "automatic sharing") |
| MCP | (remove - internal detail) |
| API | "connection" or (remove) |
| CLI | "command line" or (remove) |
| PR | "code change" |
| CI/CD | (remove - internal detail) |

### 2. Ban All Jargon

| Jargon | Human |
|--------|-------|
| hooks | "automatic triggers" → "notices when you..." |
| daemon | (remove - internal detail) |
| escalation | "decides what to share" |
| processor | (remove - internal detail) |
| ingest | "import" → "bring in" |
| repo | "project" |
| deploy | "publish" or "go live" |

### 3. Speak to the Pain, Not the Solution

**Before (feature-focused):**
```
shipped: crux session migration

switch AI tools without starting over
```

**After (pain-focused):**
```
ever lose an hour teaching cursor something claude already knew?

that doesn't happen anymore.

crux remembers everything, everywhere.
```

### 4. Updated Hook Templates

**Old:**
```
just shipped: {feature} ✅
new in crux: {feature}
```

**New:**
```
{pain point}?

not anymore.

{simple outcome}
```

### 5. Frame the Problem First

Most people don't know:
1. AI tools don't share what they learn
2. Switching tools = starting from scratch
3. Every correction you make vanishes

Posts should educate on the problem before presenting crux as the solution.

## Examples

### Example 1: Session Migration

**Before:**
```
just shipped: switch AI tools without starting over ✅

switch AI tools without starting over

no jargon. just works.

why: your AI's knowledge shouldn't be trapped in one app
```

**After:**
```
you spend 20 minutes teaching claude your codebase.

then you open cursor.

it knows nothing.

crux fixes this. your AI remembers everything, everywhere.

runcrux.io
```

### Example 2: Analytics

**Before:**
```
shipped: now I know which posts actually work ✅

now I know which posts actually work

no jargon. just works.

why: build in public should feel effortless
```

**After:**
```
sharing your work online shouldn't feel like a second job.

crux tracks what resonates so you can focus on building.

no spreadsheets. no checking. just insights.

runcrux.io
```

### Example 3: Project Awareness

**Before:**
```
shipped: each project gets its own voice ✅
```

**After:**
```
working on multiple projects?

crux knows which one you're in.

each project stays separate. no cross-contamination.

runcrux.io
```

## Implementation

1. Update `FEATURE_TO_HUMAN` with pain-focused language
2. Remove all acronyms from output
3. Add problem-framing templates
4. Regenerate Typefully queue (after rate limit clears)

## Files to Modify

- `/home/key/.crux/scripts/lib/crux_bip_publish.py`

## Success Criteria

- [ ] Zero acronyms in any post
- [ ] Zero unexplained jargon
- [ ] Every post starts with a relatable problem
- [ ] A non-developer can understand and feel the pain
