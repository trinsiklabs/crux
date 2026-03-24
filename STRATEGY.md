---
title: Crux Domain Strategy
last_updated: 2026-03-24
source: Consolidated from crux-roadmap/crux-suite-argument.md, crux-marketing-plan.md, crux-market-analysis.md
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Domain Strategy

## Strategic Position

Crux occupies a unique position: the only tool-agnostic intelligence layer for AI coding. While every other tool traps knowledge in vendor-specific directories (.cursor/, .claude/, .opencode/), Crux stores intelligence in `.crux/` — portable across all tools.

**One-liner:** "Crux is the `.git` for AI coding intelligence — it travels with you, no matter what tool you use."

## Messaging Pillars

1. **Tool-agnostic intelligence** — works with Claude Code, OpenCode, Cursor, Aider, Roo Code. Switch freely, lose nothing.
2. **Self-improving safety** — seven-stage pipeline that learns from corrections and gets smarter over time.
3. **Sovereign development** — your knowledge, your corrections, your infrastructure. No vendor lock-in.
4. **Seamless switching** — `crux switch` carries session state, knowledge, and context between tools.

## Market Context

The AI coding tool market in 2026 exceeds $35B with 150M+ developers on GitHub. Key dynamics:

- Cursor: $2B+ ARR, $1.2B valuation — locked ecosystem
- Lovable: $100M ARR in 8 months — code quality crisis (2.74x more vulnerabilities in AI-generated code)
- Replit: $9B valuation — agent platform, mass market
- Every tool traps intelligence in vendor directories

Crux's differentiator: we don't compete with any tool. We make all of them better.

## Three-Product Ecosystem

| Layer | Product | What | Status |
|-------|---------|------|--------|
| Intelligence (open source) | **Crux OS** | 24 modes, 43 MCP tools, safety pipeline, learning | Active development |
| CLI (open source) | **CruxCLI** | Hard fork of OpenCode with LSP, TUI, impact analysis | Separate domain |
| Platform (commercial) | **Crux Vibe** | Full vibe coding platform — web IDE, hosting, marketplace | Planned |

## Go-to-Market Strategy

### Phase 1: Build-in-Public (Current)

- Ship daily, post continuously via BIP pipeline
- Target: X (@splntrb), Reddit (r/LocalLLaMA, r/SideProject), Hacker News
- Zero budget — authentic technical content only
- Voice: all lowercase, technical, direct, no hype

### Phase 2: Launch (Next)

- Deploy runcrux.io
- Show HN post (draft ready in marketing plan)
- Product Hunt launch
- Target: 100+ stars, 5+ daily active users

### Phase 3: OpenClaw Integration

- Publish crux-safety skill on ClawHub (250K+ potential users)
- Position as security layer for OpenClaw ecosystem
- Bridge to Crux Vibe premium tier

### Phase 4: Crux Vibe (Future)

- Commercial platform: $9-29/month + cloud costs
- Mac Mini premium tier: $125-349/month
- Revenue target: 50-100 subscribers from OpenClaw alone = $6K-35K MRR

## Competitive Moat

1. **Network effect:** corrections and knowledge shared across projects compound value
2. **Tool-agnostic lock-in:** switching away from Crux means losing your accumulated intelligence
3. **Open source foundation:** MIT license builds trust, community contributions improve the product
4. **Safety pipeline:** no competitor has 7-gate infrastructure-enforced safety

## Current Priorities (Q1-Q2 2026)

1. Deploy website and launch publicly
2. Start continuous BIP posting
3. Fill all documentation gaps (this migration)
4. Build background processor for truly continuous learning
5. Show HN launch
6. Begin OpenClaw integration

## Source Documents

Detailed strategic analysis lives in `crux-roadmap/`:

| Document | Content |
|----------|---------|
| crux-suite-argument.md | Master strategic document (16.5k words) — ecosystem vision, moat, economics |
| crux-marketing-plan.md | Guerrilla marketing plan (9.5k words) — platform playbooks, content templates |
| crux-market-analysis.md | Market analysis (7.9k words) — 10 segments, TAM, GTM |
| crux-vibecoding-analysis.md | Competitive failure mapping — 11 categories, gaps |
| crux-openclaw-integration.md | OpenClaw integration plan — 5 integration points, 12-week rollout |
| crux-vibe-platform-spec.md | Platform spec — deployment, hosting tiers, API |
| crux-vibe-mac-premium-tier.md | Mac Mini premium tier pricing analysis |
