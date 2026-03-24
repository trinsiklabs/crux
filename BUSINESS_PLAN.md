---
title: Crux Business Plan
last_updated: 2026-03-24
source: Normalized from crux-roadmap/crux-suite-argument.md (16.5k words)
migration_date: 2026-03-24
migration_status: normalized
---

# Crux Business Plan

## Problem

The AI coding tools market ($29.5B in 2023, projected $91.3B by 2032) faces a trust crisis:

- 62% of AI-generated code contains security vulnerabilities (NIST, 2024)
- Only 33% of developers trust AI-generated code for production (Stack Overflow 2024)
- Every tool traps developer intelligence in vendor-specific directories
- No tool learns from corrections — same mistakes repeated across users and sessions
- Safety is an afterthought, not a structural requirement

## Solution

Crux is a self-improving AI operating system — the intelligence layer that sits underneath all AI coding tools.

**Core insight:** Infrastructure beats prompts. Enforce behavior through code (safety pipelines, mode routing, correction detection), not through prompt instructions that drift.

**The `.crux/` directory** stores all AI development intelligence — corrections, knowledge, session state, modes, security results — independent of any tool. The Crux MCP Server (43 tools) exposes all capabilities via standard protocol. Any MCP-compatible tool connects with one config line.

## Market

### Target Segments

1. **Solo developers** using multiple AI tools — want knowledge portability
2. **Small teams** building with AI — want safety and consistency
3. **Enterprise developers** — need compliance, audit trails, reproducibility
4. **OpenClaw community** (250K+ users) — need security layer for autonomous agents

### Competitive Position

| Competitor | Weakness Crux Addresses |
|-----------|------------------------|
| Cursor ($2B+ ARR) | Locked ecosystem, no learning |
| Replit ($9B valuation) | Quality crisis, "super buggy" agents |
| Lovable ($100M ARR) | 10% of apps leaked user data |
| Copilot | Autocomplete only, no safety |
| All tools | Vendor lock-in of intelligence |

Crux doesn't compete with any tool — it makes all of them better.

## Business Model

### Revenue Layers

| Layer | Product | Model | Status |
|-------|---------|-------|--------|
| Free | Crux OS | Open source (MIT) | Active |
| SaaS | Crux Vibe | $9-29/month + cloud | Planned |
| Premium | Mac Mini managed | $125-349/month | Planned |

### Unit Economics (Projected)

- Crux Vibe CAC: ~$0 (organic via open source)
- LTV: $108-348/year per subscriber
- Target: 50-100 subscribers from OpenClaw community alone = $6K-35K MRR

## Competitive Moat

1. **Knowledge compounding:** corrections and patterns accumulate over time, can't be cloned
2. **Tool-agnostic lock-in:** switching away means losing accumulated intelligence
3. **Open source foundation:** MIT license builds trust, community contributions compound
4. **Safety infrastructure:** 7-gate pipeline is 3-5 years ahead of competitors
5. **Network effects:** cross-project knowledge benefits all users

## Current State

- 1290+ tests, 100% coverage on core
- 43 MCP tools, 24 specialized modes
- 7-gate safety pipeline operational
- Claude Code and OpenCode fully integrated
- Website built (18 pages), pending deployment
- Build-in-public pipeline functional
- Solo founder (Bryan, Trinsik Labs)
- Pre-revenue, pre-launch

## Milestones

### Q1 2026 (In Progress)

- Deploy runcrux.io
- Show HN launch
- 100+ GitHub stars
- Complete Key migration

### Q2 2026

- 500+ GitHub stars
- 5+ daily active users
- OpenClaw safety skill published
- Background processor operational
- Begin Crux Vibe development

### Q3-Q4 2026

- Crux Vibe beta launch
- Mac Mini premium tier pilot
- First revenue
- Product Hunt launch

## Team

Solo founder: Bryan. Full-stack developer (Python, Elixir/Phoenix/Ash, TypeScript). M1 Max, 64GB RAM. Building in public via @splntrb on X.

## Detailed Strategic Analysis

The full 16.5k-word strategic document lives at `crux-roadmap/crux-suite-argument.md` covering: thesis, architecture deep-dive, product specifications, flywheel mechanics, expansion paths, competitive analysis, and financial projections.
