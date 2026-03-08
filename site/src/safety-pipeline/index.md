---
layout: base.njk
title: Safety Pipeline
description: The 7-gate safety pipeline that makes AI-generated code trustworthy
---

# Safety Pipeline

## The Problem

AI-generated code is fast but risky. It can introduce security vulnerabilities, break existing tests, violate design patterns, or simply be wrong. Most tools ship first and fix later.

## The Crux Approach

Crux implements a 7-gate safety pipeline. Code passes through progressively more rigorous checks based on risk level. Low-risk changes skip expensive gates. High-risk changes get full review.

## The 7 Gates

```
Code Change
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 0: Static Validation                   │
│ Syntax check, linting, formatting           │
│ Cost: Free │ Speed: Instant                 │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 1: TDD Compliance                      │
│ Tests exist? Tests pass? Coverage check     │
│ Cost: Free │ Speed: Seconds                 │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 2: Security Audit                      │
│ OWASP checks, credential detection, deps    │
│ Cost: Free │ Speed: Seconds                 │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 3: Design Validation                   │
│ UI patterns, accessibility, responsiveness  │
│ Cost: Free │ Speed: Seconds                 │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 4: Deep Audit (8B Model)               │
│ Local LLM reviews code for issues           │
│ Cost: Compute │ Speed: ~10s                 │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 5: Expert Audit (32B Model)            │
│ Larger model for subtle issues              │
│ Cost: More compute │ Speed: ~30s            │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Gate 6: Human Review                        │
│ Final approval for critical changes         │
│ Cost: Human time │ Speed: Variable          │
└─────────────────────────────────────────────┘
    │
    ▼
  Ship It
```

## Gate Activation

Not every change needs every gate. The pipeline activates gates based on:

**Mode** — Different modes have different risk profiles:
- `build-py` (standard dev) → Gates 0-2
- `security` (security work) → Gates 0-5
- `debug` (debugging) → Gates 0-1
- `infra-architect` (infrastructure) → Gates 0-6

**Risk Level** — Assessed per-change:
- Config change → Low risk → Gates 0-1
- New feature → Medium risk → Gates 0-3
- Security fix → High risk → Gates 0-5
- Auth/payment code → Critical → Gates 0-6

**File Type** — Some files warrant extra scrutiny:
- `.env`, credentials → Always Gate 2
- `*.sql`, migrations → Always Gate 2+
- Public API → Always Gate 3+

## Local LLM Integration

Gates 4 and 5 use local LLMs via Ollama:

- **Gate 4**: 8B parameter model (e.g., Llama 3.1 8B)
- **Gate 5**: 32B parameter model (e.g., Qwen 2.5 32B)

If Ollama isn't available, these gates can fall back to cloud APIs (Anthropic) for critical paths.

## Configuration

```json
{
  "safety": {
    "default_gates": [0, 1, 2],
    "high_risk_gates": [0, 1, 2, 3, 4, 5],
    "critical_gates": [0, 1, 2, 3, 4, 5, 6],
    "ollama_model_8b": "llama3.1:8b",
    "ollama_model_32b": "qwen2.5:32b"
  }
}
```

## Why This Works

**Fail fast.** Cheap gates run first. Expensive gates only run if cheap gates pass.

**Risk-proportional.** Low-risk code ships fast. High-risk code gets scrutiny.

**Local-first.** No cloud dependency for most checks. Your code stays on your machine.

**Corrections compound.** Gate failures become corrections that improve future code.
