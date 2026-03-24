# Documentation Gaps

> Last updated: 2026-03-24
> Migration status: complete
> Project types: software-existing, product-saas, website, business-new
> Template categories: domains, projects/code, projects/business, product, projects/website, projects/marketing, operations, financial, research
> Maturity level: 2 (growing)

## Critical Gaps (must fill before migration is complete)

| # | Gap Description | Template Reference | Priority | Status |
|---|---|---|---|---|
| 1 | ~~No CHARTER.md~~ | templates/domains/docs/CHARTER.md | CRITICAL | DONE 2026-03-24 |
| 2 | ~~No consolidated ARCHITECTURE.md~~ | templates/projects/code/docs/ARCHITECTURE.md | HIGH | DONE 2026-03-24 |
| 3 | ~~No API.md for MCP server~~ | templates/projects/code/docs/API.md | HIGH | DONE 2026-03-24 |
| 4 | ~~No TESTING.md~~ | templates/projects/code/docs/TESTING.md | HIGH | DONE 2026-03-24 |
| 5 | ~~No CONFIGURATION.md~~ | templates/projects/code/docs/CONFIGURATION.md | HIGH | DONE 2026-03-24 |
| 6 | ~~No BUSINESS_PLAN.md~~ | templates/projects/business/docs/BUSINESS_PLAN.md | HIGH | DONE 2026-03-24 |
| 7 | ~~No EXECUTIVE_SUMMARY.md~~ | templates/projects/business/docs/EXECUTIVE_SUMMARY.md | HIGH | DONE 2026-03-24 |
| 8 | ~~No STRATEGY.md~~ | templates/domains/docs/STRATEGY.md | HIGH | DONE 2026-03-24 |
| 9 | ~~No CHANGELOG.md~~ | templates/projects/code/docs/CHANGELOG.md | HIGH | DONE 2026-03-24 |

## Stub Documents (created with TODO markers)

| # | Document | Sections Complete | Sections TODO | Path |
|---|---|---|---|---|
| 1 | docs/manual.md | ~~empty~~ — filled with 733-line user guide | DONE | docs/manual.md |

## Known Deficiencies (content exists but is weak)

| # | Document | Issue | Severity |
|---|---|---|---|
| 1 | README.md | ~~Tool count outdated~~ — fixed to 43 MCP tools, 1374+ tests | DONE |
| 2 | docs/architecture.md | ~~Outdated tool count~~ — consolidated and updated | DONE |
| 3 | docs/safety-pipeline.md | ~~5 gates~~ — rewritten to 7 gates | DONE |
| 4 | crux-roadmap/crux-gap-report.md | ~~outdated~~ — marked superseded by GAPS.md | DONE |
| 5 | crux-specs/website-marketing-status-report.md | ~~outdated~~ — marked superseded | DONE |
| 6 | CLAUDE.md | ~~Outdated counts~~ — fixed to 43 tools, 1374+ tests | DONE |
| 7 | site/ content | ~~outdated counts~~ — fixed 37→43 tools across site pages | DONE |
| 8 | deploy-runcrux.io.sh | ~~never deployed~~ — deployed 2026-03-24, live at runcrux.io | DONE |

## Not Applicable

Templates that do not apply to this project (with justification):

| # | Template Category | Reason |
|---|---|---|
| 1 | people | Solo founder, no employees |
| 2 | customer | No direct customer interaction yet (pre-launch) |
| 3 | campaigns | No marketing campaigns planned (build-in-public only) |
| 4 | communications | No external press or formal comms yet |
| 5 | legal (beyond license) | MIT license covers it; no contracts, no ToS needed yet |
| 6 | financial | Pre-revenue, no projections formalized yet |
| 7 | governance (beyond CONTRIBUTING.md) | Solo founder, no governance framework needed |

## Migration Priority Order

1. CHARTER.md — defines the domain, required for Key migration
2. Consolidate ARCHITECTURE.md — merge docs/architecture.md + crux-roadmap/crux-expanded-architecture-spec.md
3. API.md — document all 43 MCP tools
4. STRATEGY.md — consolidate from crux-roadmap/ strategic docs
5. Normalize BUSINESS_PLAN.md from crux-suite-argument.md
6. TESTING.md — document test infrastructure
7. CONFIGURATION.md — document all config files and setup
8. CHANGELOG.md — generate from git history
9. EXECUTIVE_SUMMARY.md — derive from business plan
10. Fix all known deficiencies (outdated numbers)
