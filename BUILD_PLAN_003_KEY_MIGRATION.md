# BUILD_PLAN_003: Migrate Crux to Key Management

**Created:** 2026-03-24
**Status:** COMPLETE
**Goal:** Fill all 9 documentation gaps identified in GAPS.md, normalize existing materials into Key template structure, and prepare a complete migration package.

**Constraint:** Documents must be accurate against current codebase state (43 MCP tools, 1290+ tests, 24 modes).
**Constraint:** Follow MIGRATE_TO_KEY.md process (Steps 3-6).
**Rule:** Every factual claim verified against ground truth (code, git, config files).
**Rule:** Two consecutive clean audit passes = convergence.

## Document Alignment

- `MIGRATE_TO_KEY.md` — the migration process, template references, GAPS.md format
- `intake-classification.md` — project types and template categories
- `intake-inventory.md` — 103 assets catalogued
- `GAPS.md` — 9 critical/high gaps, 8 known deficiencies
- `CLAUDE.md` — repo structure, architecture principles, conventions

---

## Architecture

```
Current state:                          Target state:
  docs/ (scattered)                       docs/
  crux-roadmap/ (strategy)                  ARCHITECTURE.md (consolidated)
  crux-specs/ (specs)                       API.md (43 MCP tools)
  README.md                                 TESTING.md
  CLAUDE.md                                 CONFIGURATION.md
  (no charter, no strategy)                 CHANGELOG.md
                                            USER_GUIDE.md (from manual.md)
                                          CHARTER.md (new)
                                          STRATEGY.md (new, consolidated)
                                          BUSINESS_PLAN.md (normalized)
                                          EXECUTIVE_SUMMARY.md (new)
                                          GAPS.md (updated)
                                          README.md (fixed)
```

---

## Phase 1: Domain Foundation

**Purpose:** Create the Key-required domain documents that don't exist yet.

### Checklist — Phase 1

- [x] 1.1 Create CHARTER.md — purpose, scope, ownership, boundaries, success criteria
- [x] 1.2 Create STRATEGY.md — consolidated from 7 crux-roadmap/ strategic docs
- [x] 1.3 Create EXECUTIVE_SUMMARY.md — one-page summary with current state and milestones

---

## Phase 2: Code Documentation

**Purpose:** Fill the projects/code template gaps with accurate, verified documentation.

### Checklist — Phase 2

- [x] 2.1 Consolidated docs/architecture.md — merged architecture, scripts-first, tool-hierarchy, expanded-spec
- [x] 2.2 Created docs/API.md — all 43 MCP tools documented by category
- [x] 2.3 Created docs/TESTING.md — test infrastructure, coverage, patterns, commands
- [x] 2.4 Created docs/CONFIGURATION.md — all config files, env vars, directory structure
- [x] 2.5 Created CHANGELOG.md — milestones from 2026-03-05 through 2026-03-24

---

## Phase 3: Business Documentation

**Purpose:** Normalize existing strategic materials into Key business templates.

### Checklist — Phase 3

- [x] 3.1 Created BUSINESS_PLAN.md — normalized from crux-suite-argument.md (problem, solution, market, model, team, milestones)
- [x] 3.2 Verified claims against current state (43 tools, 1290+ tests, 24 modes, 7 gates)

---

## Phase 4: Fix Known Deficiencies

**Purpose:** Update all documents with outdated numbers and claims.

### Checklist — Phase 4

- [x] 4.1 Fixed README.md — 43 tools, 1374+ tests
- [x] 4.2 Fixed CLAUDE.md — 43 tools, 1374+ tests
- [x] 4.3 All new documents use verified current numbers (43 tools, 24 modes, 1374+ tests)
- [x] 4.4 Updated GAPS.md — all 9 gaps marked DONE, 3 deficiencies fixed

---

## Phase 5: Migration Package Verification

**Purpose:** Verify the complete migration package is ready for Key intake.

### Checklist — Phase 5

- [x] 5.1 All 9 gaps resolved (CHARTER, STRATEGY, EXECUTIVE_SUMMARY, ARCHITECTURE, API, TESTING, CONFIGURATION, BUSINESS_PLAN, CHANGELOG)
- [x] 5.2 Zero content loss — all 103 inventory items accounted for (originals preserved)
- [x] 5.3 Cross-references verified (ARCHITECTURE → API, TESTING, modes, safety-pipeline)
- [x] 5.4 Factual claims verified: 43 MCP tools, 24 modes, 1374+ tests, 7 gates
- [x] 5.5 GAPS.md updated — all critical/high items DONE, migration status: in-progress
- [x] 5.6 intake-classification.md, intake-inventory.md, GAPS.md ready for handoff

---

## Convergence Criteria

- All checklist items complete
- All documents verified against codebase ground truth
- GAPS.md shows all critical/high items resolved
- Two consecutive clean audit passes
- README.md and CLAUDE.md accurate

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Architecture doc too long after consolidation | Unreadable | Keep to key concepts, link to detailed specs |
| MCP tool list changes during migration | API.md outdated immediately | Generate from code, note generation method |
| Business plan claims outpace reality | Credibility | Verify every claim, mark aspirational content clearly |
| Numbers drift between docs | Inconsistency | Single source of truth for counts (grep codebase) |
