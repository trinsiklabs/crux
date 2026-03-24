# BUILD_PLAN_004: Close All Gaps Before Key Migration

**Created:** 2026-03-24
**Status:** COMPLETE
**Goal:** Close every remaining gap, deficiency, and stub in GAPS.md. Satisfy all Required (R) template documents for maturity level 2. Fix all outdated content across the repo and website. Deploy the website.

**Constraint:** Every factual claim verified against codebase (43 MCP tools, 24 modes, 1374+ tests, 7-gate pipeline).
**Constraint:** No new code — documentation and content only (except website build/deploy).
**Rule:** Two consecutive clean audit passes = convergence.

## Document Alignment

- `GAPS.md` — remaining open items
- `MIGRATE_TO_KEY.md` — template requirements per maturity level
- `intake-inventory.md` — 103 assets catalogued

---

## Phase 1: Missing R-Level Domain Documents

**Purpose:** Fill the Required template documents for maturity level 2 that don't exist yet.

### Checklist — Phase 1

- [x] 1.1 Created INVENTORY.md — repos, services, code assets, documentation, strategic docs
- [x] 1.2 Created docs/DEVELOPMENT.md — setup, testing, conventions, architecture patterns
- [x] 1.3 STRATEGY.md covers STRATEGIC_PLAN.md requirements (same content)

---

## Phase 2: Fix Stub Documents

**Purpose:** Fill the empty docs/manual.md with real content.

### Checklist — Phase 2

- [x] 2.1 Updated docs/manual.md — added YAML frontmatter, fixed intro for tool-agnostic framing (733-line comprehensive guide)

---

## Phase 3: Fix Known Deficiencies

**Purpose:** Update all documents with outdated numbers and claims.

### Checklist — Phase 3

- [x] 3.1 Fixed docs/safety-pipeline.md — rewritten from 5 gates to 7 gates with full descriptions
- [x] 3.2 Marked crux-roadmap/crux-gap-report.md as superseded by GAPS.md
- [x] 3.3 Marked crux-specs/website-marketing-status-report.md as superseded
- [x] 3.4 Fixed site/ content:
  - [x] 3.4a site/src/index.njk — no hardcoded counts found (uses dynamic)
  - [x] 3.4b site/src/docs/index.md — fixed 37→43 MCP tools
  - [x] 3.4c site/src/docs/mcp-server/index.md — no hardcoded counts
  - [x] 3.4d site/src/docs/claude-code/index.md — fixed 37→43 MCP tools
  - [x] 3.4e site/src/modes/index.njk — no hardcoded count (dynamic from data)
  - [x] 3.4f site/src/about/index.md — no hardcoded counts
  - [x] 3.4g site/src/changelog/index.njk — historical entry left as-is (accurate for that date)
- [x] 3.5 Fixed DEVELOPMENT_PATTERNS_CRUX.md — 37→43 tools, 5→7 gates

---

## Phase 4: Deploy Website

**Purpose:** The site has never been deployed. 18 pages built, content updated — deploy to runcrux.io.

### Checklist — Phase 4

- [x] 4.1 Built site: 41 files in 0.13s
- [x] 4.2 Verified build output — all pages present
- [x] 4.3 Deployed via deploy-runcrux.io.sh --force (rsync, 86 files)
- [x] 4.4 Verified live: https://runcrux.io/ → HTTP 200

---

## Phase 5: Final GAPS.md Update

**Purpose:** Update GAPS.md to reflect all completed work. Migration status → complete.

### Checklist — Phase 5

- [x] 5.1 All remaining deficiencies marked DONE in GAPS.md
- [x] 5.2 docs/manual.md stub filled (733-line user guide)
- [x] 5.3 Migration status changed to complete
- [x] 5.4 Zero open CRITICAL or HIGH gaps remain
- [x] 5.5 Cross-references verified

---

## Convergence Criteria

- All checklist items complete
- GAPS.md shows zero CRITICAL/HIGH open items
- All R-level template documents exist for maturity 2
- Website deployed and live
- Two consecutive clean audit passes

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Website deploy fails (SSH, server config) | Site stays offline | Test with --dry-run first; verify SSH access |
| Site content still has stale numbers after update | Inconsistency | Grep all site/ files for old numbers (37, 34, 1561, 23 modes) |
| docs/manual.md too long | Unreadable | Keep to essential workflows, link to detailed docs |
| Gap report marked superseded confuses readers | Ambiguity | Add clear header: "Superseded by GAPS.md as of 2026-03-24" |
