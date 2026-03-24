---
title: Crux Domain Inventory
last_updated: 2026-03-24
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Domain Inventory

## Repositories

| Repo | Location | Description | Status |
|------|----------|-------------|--------|
| trinsiklabs/crux | GitHub (upstream) | Crux OS — core framework | Active |
| tecto/crux | GitHub (fork) | Development fork | Active |

## Services

| Service | URL | Description | Status |
|---------|-----|-------------|--------|
| runcrux.io | https://runcrux.io | Project website (11ty) | Built, pending deploy |
| Crux MCP Server | stdio (local) | 43-tool FastMCP server | Operational |
| Typefully | API integration | X/Twitter post scheduling (@splntrb) | Configured |

## Code Assets

| Asset | Path | Language | Purpose |
|-------|------|----------|---------|
| MCP Server | scripts/lib/crux_mcp_server.py | Python | 43 tool registrations |
| MCP Handlers | scripts/lib/crux_mcp_handlers.py | Python | Pure handler functions |
| Impact Analysis | scripts/lib/impact/ | Python | 4 modules (git, keywords, LSP, scorer) |
| Python Library | scripts/lib/ | Python | 38+ modules |
| Plugins | plugins/ | JavaScript | 7 OpenCode plugins |
| Custom Tools | tools/ | JavaScript | 9 Zod-validated tools |
| Modes | modes/ | Markdown+YAML | 24 specialized mode prompts |
| Commands | commands/ | Markdown | 12 command definitions |
| Skills | skills/ | Markdown | 2 skill definitions |
| Website | site/ | Nunjucks/CSS | 18 pages, 3 blog posts |
| Installer | setup.sh | Bash | Interactive installer (1500+ lines) |
| Deploy Script | deploy-runcrux.io.sh | Bash | Site build and deploy |
| Tests | tests/ | Python/JS/Bash | 1374+ tests, 100% coverage |

## Documentation Assets

| Document | Path | Type |
|----------|------|------|
| CHARTER.md | Root | Domain charter |
| STRATEGY.md | Root | Domain strategy |
| EXECUTIVE_SUMMARY.md | Root | One-page summary |
| BUSINESS_PLAN.md | Root | Business plan |
| CHANGELOG.md | Root | Release history |
| README.md | Root | Project overview |
| CLAUDE.md | Root | Claude Code context |
| CONTRIBUTING.md | Root | Contribution guide |
| DEPLOYMENT.md | Root | Website deployment |
| DEVELOPMENT_PATTERNS_CRUX.md | Root | Dev patterns |
| docs/architecture.md | docs/ | Architecture (consolidated) |
| docs/API.md | docs/ | MCP API reference (43 tools) |
| docs/TESTING.md | docs/ | Test strategy |
| docs/CONFIGURATION.md | docs/ | Config reference |
| docs/safety-pipeline.md | docs/ | Safety pipeline |
| docs/continuous-learning.md | docs/ | Learning system |
| docs/modes.md | docs/ | Mode design principles |
| docs/manual.md | docs/ | User guide |

## Strategic Documents

| Document | Path | Words | Content |
|----------|------|-------|---------|
| crux-suite-argument.md | crux-roadmap/ | 16.5k | Master strategic document |
| crux-marketing-plan.md | crux-roadmap/ | 9.5k | Marketing playbook |
| crux-market-analysis.md | crux-roadmap/ | 7.9k | Market analysis |
| crux-expanded-architecture-spec.md | crux-roadmap/ | 9.5k | Architecture spec |
| crux-vibe-platform-spec.md | crux-roadmap/ | 7.4k | Platform spec |
| crux-openclaw-integration.md | crux-roadmap/ | 10.2k | OpenClaw integration |
| crux-vibe-mac-premium-tier.md | crux-roadmap/ | 8.2k | Premium tier pricing |
| crux-vibecoding-analysis.md | crux-roadmap/ | 6k | Competitive analysis |
| + 5 additional roadmap docs | crux-roadmap/ | — | See CRUX-DOCUMENT-INDEX.md |

## Migration Artifacts

| File | Purpose |
|------|---------|
| intake-classification.md | Project type classification |
| intake-inventory.md | Detailed 103-item inventory |
| GAPS.md | Gap tracking |
| BUILD_PLAN_003_KEY_MIGRATION.md | Migration build plan |
| BUILD_PLAN_004_CLOSE_GAPS.md | Gap closure build plan |
