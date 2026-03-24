---
title: Crux Executive Summary
last_updated: 2026-03-24
migration_date: 2026-03-24
migration_status: normalized
---

# Crux — Executive Summary

## What It Is

Crux is an open-source AI operating system that makes any AI coding tool smarter. It wraps LLMs and agentic tools (Claude Code, OpenCode, Cursor, Aider, Roo Code) with specialized modes, continuous learning, and infrastructure-enforced safety — without locking developers into any single tool.

## The Problem

Every AI coding tool traps your intelligence in its own directory. Teach Cursor your codebase patterns, switch to Claude Code — start over. Corrections, context, and learned knowledge are locked in vendor-specific storage that doesn't transfer.

AI-generated code also has a quality crisis: 2.74x more security vulnerabilities, 75% more misconfigurations than hand-written code. No tool has infrastructure-level safety enforcement.

## The Solution

The `.crux/` directory stores all AI development intelligence — corrections, knowledge, session state, mode definitions, security results — independent of any tool. The Crux MCP Server exposes 43 tools via standard protocol. Any MCP-compatible tool connects with one config line.

`crux switch opencode` after working in Claude Code: session state, knowledge, corrections, and context come with you. Zero re-teaching.

## Current State

- **1290+ tests**, 100% coverage on core modules
- **43 MCP tools** operational via FastMCP server
- **24 specialized modes** (coding, architecture, design, security, marketing)
- **7-gate safety pipeline** (preflight → TDD → security audit → adversarial audit → human approval → dry run → design validation)
- **Website:** 18 pages built at runcrux.io (pending deployment)
- **Build-in-public pipeline:** Typefully integration, trigger-based drafts
- **Cross-platform:** macOS + Linux (Ubuntu 24.04)

## Who It's For

Solo developers and small teams using multiple AI coding tools who want their AI to get smarter over time without vendor lock-in.

## Business Model

- **Crux OS:** Free, MIT licensed (this product)
- **Crux Vibe (planned):** Commercial vibe coding platform — $9-29/month
- **Mac Mini premium tier (planned):** Managed local LLM setup — $125-349/month

## Next Milestones

1. Deploy runcrux.io
2. Show HN launch
3. 100+ GitHub stars
4. Background processor for continuous learning
5. OpenClaw safety skill integration
6. Begin Crux Vibe development
