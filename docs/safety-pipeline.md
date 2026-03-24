---
title: Crux Safety Pipeline
last_updated: 2026-03-24
source: Updated from 5-gate to 7-gate architecture
migration_date: 2026-03-24
migration_status: normalized
---

# Seven-Gate Safety Pipeline

## Overview

All script execution flows through the safety pipeline which implements seven sequential gates. Gates scale with risk level — low-risk scripts go through fewer gates, high-risk scripts go through all seven. The model cannot bypass or reason about the validation logic.

## Gate 1: Pre-Flight Validation

Deterministic checks (always runs, implemented in `preflight_validator.py`):

1. Shebang present (`#!/bin/bash` or similar)
2. Risk header declared (low/medium/high)
3. `set -euo pipefail` safety clause present
4. `main()` function pattern used
5. Risk level matches operations (low-risk scripts cannot contain destructive ops)
6. DRY_RUN support for medium+ risk
7. Path containment (no writes to root filesystem)
8. Transaction pattern for multi-file modifications

**On failure**: Script never executes. Error returned to model for correction.

## Gate 2: TDD Enforcement

Test-first development gate (build modes, implemented in `crux_tdd_gate.py`):

Enforces four-phase workflow: plan → red (write failing tests) → green (make tests pass) → complete. Tracks coverage targets and prevents skipping the test-writing phase.

**On failure**: Build blocked until tests are written first.

## Gate 3: Security Audit

Recursive security audit loop (medium+ risk, implemented in `crux_security_audit.py`):

Scans for vulnerabilities across 7 categories with CWE/OWASP classification. Runs audit → fix → re-audit until convergence (zero new findings) or max iterations reached.

**On failure**: Findings reported with severity, CWE/OWASP classification, and suggested fixes.

## Gate 4: 8B Adversarial Audit

A different model (8B) reviews the script as a security auditor, looking for data loss, corruption, unintended side effects, and scope creep. Using a different model prevents self-enhancement bias.

**On failure**: Concerns returned to the main model for review and resolution.

## Gate 5: 32B Second-Opinion

High-risk scripts only. A larger model performs a second review of both the script and the 8B audit findings. Structural adversarial review, not self-review.

**On failure**: Script returned for revision with combined audit feedback.

## Gate 6: Human Approval

All scripts require explicit user approval. The tool returns a request for approval with full audit results. Human reviews the script and approves or rejects.

**On failure**: Script archived. Model generates alternative approach.

## Gate 7: DRY_RUN

Configurable. Medium+ risk scripts can execute with `DRY_RUN=1` environment variable first. The script must handle this variable and simulate operations without side effects.

**On failure**: Dry run results shown to user before real execution.

## Risk Levels and Gate Activation

| Level | Examples | Gates Activated |
|-------|----------|----------------|
| Low | Read configs, format code, add tests | 1, 6 |
| Medium | Modify configs, update deps, refactor | 1, 2, 3, 4, 6, 7 |
| High | Delete data, deploy, modify system, security changes | 1, 2, 3, 4, 5, 6, 7 |

Gate activation is configurable per mode and risk level via `crux_pipeline_config.py`.

## Design Validation (Bonus Gate)

For design modes (design-ui, design-system, design-responsive, design-accessibility), an additional design validation gate runs:

- WCAG compliance checks
- Color contrast verification
- Touch target size validation
- Brand consistency checks
- Design-to-code handoff verification

Implemented in `crux_design_validation.py`.
