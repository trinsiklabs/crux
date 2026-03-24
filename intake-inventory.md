# Intake Inventory — Crux

> **Date:** 2026-03-24
> **Total assets:** 103
> **Quality:** 73 usable, 6 reference-only, 18 extract-info, 0 obsolete

## Root Authority Docs

| # | File | Format | Description | Template Match | Quality |
|---|------|--------|-------------|----------------|---------|
| 1 | README.md | md | Project overview, architecture, quick start | projects/code README | usable |
| 2 | CLAUDE.md | md | Claude Code context — repo structure, architecture, conventions | projects/code DEVELOPMENT | usable |
| 3 | CONTRIBUTING.md | md | Contribution guidelines by type | projects/code CONTRIBUTING | usable |
| 4 | LICENSE | text | MIT license | legal/license | usable |
| 5 | DEVELOPMENT_PATTERNS_CRUX.md | md | Project-specific patterns and anti-patterns | domains/development-patterns | usable |
| 6 | KEY_OWNERSHIP.md | md | Development ownership delegation (draft) | governance/ownership | reference-only |
| 7 | DEPLOYMENT.md | md | runcrux.io deployment guide | projects/code DEPLOYMENT | usable |
| 8 | competitive-analysis.md | md | Three-product ecosystem competitive analysis | research/competitive-analysis | usable |

## Build Plans

| # | File | Format | Description | Template Match | Quality |
|---|------|--------|-------------|----------------|---------|
| 9 | BUILD_PLAN_001_COVERAGE_CLOSURE.md | md | Completed: 93%→100% coverage (1290→1517 tests) | projects/build-plan | usable |
| 10 | BUILD_PLAN_002_CRUX_SELF_ADOPTION.md | md | Self-adoption per CruxDev methodology, 9 phases | projects/build-plan | usable |
| 11 | BUILD_PLAN_002_IMPACT_ANALYSIS.md | md | Completed: analyze_impact MCP tool, converged | projects/build-plan | usable |

## Architecture & Technical Docs (docs/)

| # | File | Format | Description | Template Match | Quality |
|---|------|--------|-------------|----------------|---------|
| 12 | docs/architecture.md | md | Core architecture — 4 system layers, components | projects/code ARCHITECTURE | usable |
| 13 | docs/modes.md | md | Mode design principles — 4 empirical rules | projects/code custom | usable |
| 14 | docs/safety-pipeline.md | md | Five-gate safety pipeline | projects/code SECURITY | usable |
| 15 | docs/continuous-learning.md | md | Knowledge system and learning architecture | projects/code custom | usable |
| 16 | docs/setup-reference.md | md | Installation and setup reference | projects/code CONFIGURATION | usable |
| 17 | docs/scripts-first.md | md | Scripts-first design pattern | projects/code ARCHITECTURE | usable |
| 18 | docs/tool-hierarchy.md | md | Tool resolution hierarchy (Tier 0-5) | projects/code ARCHITECTURE | usable |
| 19 | docs/manual.md | md | User manual (incomplete) | projects/code USER_GUIDE | reference-only |
| 20 | docs/CLAWHUB-ANALYSIS.md | md | ClawHub integration analysis | research/integration | extract-info |

## Strategy & Planning (crux-roadmap/)

| # | File | Format | Description | Template Match | Quality |
|---|------|--------|-------------|----------------|---------|
| 21 | crux-roadmap/crux-suite-argument.md | md | Master strategic doc (16.5k words) — ecosystem, moat, economics | strategy/BUSINESS_PLAN | usable |
| 22 | crux-roadmap/crux-marketing-plan.md | md | Guerrilla marketing plan (9.5k words) — build-in-public, platforms | strategy/MARKETING_PLAN | usable |
| 23 | crux-roadmap/crux-market-analysis.md | md | Market analysis — 10 segments, TAM, GTM | research/MARKET_RESEARCH | usable |
| 24 | crux-roadmap/crux-vibecoding-analysis.md | md | Vibecoding failure mapping — 11 categories, solutions | research/COMPETITIVE_ANALYSIS | usable |
| 25 | crux-roadmap/crux-openclaw-integration.md | md | OpenClaw integration plan — 5 integration points, 12-week rollout | strategy/integration | usable |
| 26 | crux-roadmap/crux-expanded-architecture-spec.md | md | Formal architecture spec (9.5k words) | projects/code ARCHITECTURE | usable |
| 27 | crux-roadmap/crux-vibe-platform-spec.md | md | Crux Vibe platform spec — deployment, hosting, API | product/PRD | usable |
| 28 | crux-roadmap/crux-vibe-mac-premium-tier.md | md | Mac Mini premium tier pricing analysis | product/PRICING_STRATEGY | usable |
| 29 | crux-roadmap/crux-replit-competitor-plan.md | md | Replit competitor strategy | product/PRD | usable |
| 30 | crux-roadmap/crux-website-plan.md | md | Website development plan — 18 pages | projects/website | extract-info |
| 31 | crux-roadmap/crux-gap-report.md | md | Feature gap analysis (dated 2026-03-06) | research/gap-analysis | extract-info |
| 32 | crux-roadmap/crux-github-action-plan.md | md | GitHub Actions integration | technical/integration | extract-info |
| 33 | crux-roadmap/crux-shipper-mashup.md | md | Shipper mashup analysis | research/analysis | reference-only |
| 34 | crux-roadmap/crux-marketing-plan-addendum-vibe-coding-analysis.md | md | Vibe coding ecosystem competitive analysis | strategy/marketing | extract-info |
| 35 | crux-roadmap/opencode-per-mode-model-routing.md | md | Per-mode model routing strategy | technical/features | extract-info |
| 36 | crux-roadmap/mobile-frontend-plan.md | md | Mobile frontend roadmap | product/roadmap | extract-info |
| 37 | crux-roadmap/crux-openclaw-autonomous-business-guide.md | md | OpenClaw autonomous business model | strategy/business-model | extract-info |
| 38 | crux-roadmap/CRUX-DOCUMENT-INDEX.md | md | Master document index — reading order for all strategic docs | documentation/index | usable |

## Specs (crux-specs/)

| # | File | Format | Description | Template Match | Quality |
|---|------|--------|-------------|----------------|---------|
| 39 | crux-specs/DEVELOPMENT-PLAN.md | md | Complete knowledge transfer document | projects/code DEVELOPMENT | usable |
| 40 | crux-specs/website-marketing-status-report.md | md | Marketing/website implementation status (2026-03-07) | operations/status-report | reference-only |
| 41 | crux-specs/specs/plugins.md | md | Plugin architecture (7 plugins) | projects/code API | usable |
| 42 | crux-specs/specs/custom-tools.md | md | Custom tools (9 tools, Zod schemas) | projects/code API | usable |
| 43 | crux-specs/specs/library-scripts.md | md | Library scripts and promotion rules | projects/code API | usable |
| 44 | crux-specs/specs/continuous-learning.md | md | Continuous learning spec | projects/code custom | usable |
| 45 | crux-specs/specs/mode-audit.md | md | Mode quality audit spec | projects/code custom | usable |
| 46 | crux-specs/specs/model-management.md | md | Model registry spec | projects/code custom | usable |

## Modes (24 mode definitions)

All usable. Each is a Markdown file with YAML frontmatter defining temperature, think/no-think, tool access.

| # | Range | Description |
|---|-------|-------------|
| 47-70 | modes/*.md | 24 specialized mode prompts (build-py, build-ex, test, plan, debug, security, review, infra-architect, design-ui, design-system, design-review, design-responsive, design-accessibility, ai-infra, analyst, explain, writer, marketing, build-in-public, psych, legal, strategist, mac, docker) |

## Commands, Skills, Templates

| # | Range | Description |
|---|-------|-------------|
| 71-82 | commands/*.md | 12 command definitions |
| 83-84 | skills/*/SKILL.md | 2 skill definitions (session-logger, script-builder) |
| 85-87 | templates/*.md + .json | 3 templates (PROJECT.md, AGENTS.md, opencode.json) |

## Configuration

| # | File | Description |
|---|------|-------------|
| 88 | config.json | Project config (default mode, digest cadence) |
| 89 | .mcp.json | MCP server configuration (crux + cruxdev) |
| 90 | package.json | Node.js test config |
| 91 | requirements.txt | Python dependencies |
| 92 | pyproject.toml | Pytest/coverage config |
| 93 | setup.sh | Interactive installer (1500+ lines) |

## Website (site/)

| # | File | Description |
|---|------|-------------|
| 94 | site/src/index.njk | Landing page |
| 95 | site/src/docs/ | 10 doc pages (getting started + 7 tools + MCP + modes) |
| 96 | site/src/blog/ | 3 blog posts |
| 97 | site/src/about/ | Founder story |
| 98 | site/src/architecture/ | Architecture page |
| 99 | site/src/safety-pipeline/ | Safety pipeline page |
| 100 | site/src/switching/ | Tool switching guide |
| 101 | site/src/adopt/ | crux adopt guide |
| 102 | site/src/modes/ | Modes showcase |
| 103 | site/src/changelog/ | Release changelog |

## Marketing (gitignored, local only)

| # | File | Description |
|---|------|-------------|
| -- | .crux/marketing/config.json | BIP config (Typefully, triggers, voice) |
| -- | .crux/marketing/state.json | BIP state (counters, timestamps) |
| -- | .crux/marketing/typefully.key | API key (do not migrate) |
