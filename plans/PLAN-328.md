# PLAN-328: Blog quality upgrade: pagination, narrative posts, broken link enforcement

**Status:** planned
**Group:** GROUP-MKT
**Domain:** crux
**Risk:** 0.25

## Summary

Improve runcrux.io blog quality with proper pagination, substantive narrative content, and broken link prevention.

## Requirements

### 1. Sorting & Pagination
- Posts displayed most recent to oldest (verify current implementation)
- Pagination: 10 posts per page
- Prev/next navigation links
- Page URLs: `/blog/`, `/blog/page/2/`, `/blog/page/3/`, etc.

### 2. Narrative Blog Posts
- Minimum 3-4 paragraphs per post
- Structure each post with:
  - **What was done** - Feature/fix summary
  - **How it was implemented** - Technical approach, files changed
  - **Why** - Motivation, user benefit, strategic context
- Replace current stub posts with substantive content
- Update `crux_bip_publish.py` blog generation to produce narrative format

### 3. Broken Link Removal
- Remove hardcoded plan links (e.g., `github.com/someuser/crux/issues/XXX`)
- These are placeholder links that don't exist
- Replace with internal references or remove entirely
- Fix all 19 existing blog posts

### 4. Deploy-time Link Enforcement
- Add link checker to `deploy-runcrux.io.sh`
- Check internal links (relative paths exist)
- Check external links (HTTP 200 response)
- Fail deploy if any broken links detected
- Provide clear error output showing which links are broken

## Implementation

### Phase 1: 11ty Pagination
- Modify `.eleventy.js` to configure pagination
- Create `src/blog/index.njk` with pagination logic
- Add prev/next navigation partial

### Phase 2: Fix Existing Posts
- Remove broken plan links from all 19 posts
- Regenerate narrative content for each post

### Phase 3: Update Blog Generation
- Modify `crux_bip_publish.py` `generate_blog_post()` function
- Template for narrative structure (what/how/why)
- Pull context from plan metadata for substantive content

### Phase 4: Link Checker
- Install/use `linkchecker` or `htmltest` tool
- Add pre-deploy check to `deploy-runcrux.io.sh`
- Exit non-zero on broken links

## Affected Files

- `/home/key/.crux/site/.eleventy.js`
- `/home/key/.crux/site/src/blog/index.njk` (new)
- `/home/key/.crux/site/src/blog/*.md` (19 files)
- `/home/key/.crux/scripts/lib/crux_bip_publish.py`
- `/home/key/.crux/scripts/deploy-runcrux.io.sh`

## Success Criteria

- [ ] Blog index shows 10 posts per page with pagination nav
- [ ] All posts have 3-4 paragraphs with what/how/why structure
- [ ] No broken links on any page
- [ ] Deploy fails if broken link introduced
- [ ] BIP auto-generates narrative posts for new plans
