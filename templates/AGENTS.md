# Crux Agent Framework

## Core Principles

### Scripts-First Design
All filesystem modifications must be executed through scripts in `.opencode/scripts/` following the project script template. Never modify files directly. This ensures:
- Auditability: Every change is tracked and reversible
- Consistency: Standard structure for all modifications
- Safety: Scripts are the only way to modify state

### Tool Resolution Hierarchy
When deciding how to accomplish a task, use this priority order:

1. **Tier 0: LSP Servers** - Language-specific intelligence (pyright, elixir-ls)
2. **Tier 1: Custom Tools** - Built for Crux workflows (promote_script.js, run_script.js)
3. **Tier 2: MCP Servers** - Third-party integrations and capabilities
4. **Tier 3: Library Scripts** - Vetted, re-usable scripts in `.opencode/scripts/library/`
5. **Tier 4: New Scripts** - Custom scripts for one-off tasks following template
6. **Tier 5: Raw Bash** - Direct command execution (last resort only)

## Script Template

Every script must follow this structure:

```bash
#!/bin/bash
set -euo pipefail

###############################################################################
# Script Header
# Name: descriptive-name
# Risk: low|medium|high
# Created: YYYY-MM-DD
# Status: active|deprecated|archived
# Description: What this script does
###############################################################################

DRY_RUN="${DRY_RUN:-0}"

main() {
    # Implementation here
}

main "$@"
```

### Header Requirements
- **Name**: Kebab-case identifier
- **Risk**: Impact level (low: read-only, medium: modification, high: destructive)
- **Created**: ISO date of creation
- **Status**: active, deprecated, or archived
- **Description**: One-line explanation of purpose

### Implementation Requirements
- `set -euo pipefail` at top for error safety
- DRY_RUN support for testing without side effects
- Clear error messages
- Logging of significant operations
- Idempotent behavior (safe to re-run)

## Risk Classification

Risk levels guide execution caution and testing requirements:

### Low Risk Scripts
- Read-only operations
- Information retrieval
- Non-destructive configuration
- Requirements: No special approval, can run in dry-run mode

### Medium Risk Scripts
- Filesystem modifications (non-destructive)
- Configuration changes
- Service restarts
- Requirements: User confirmation recommended, dry-run strongly suggested

### High Risk Scripts
- Permanent deletions
- System integrity changes
- Permissions modifications
- Requirements: Explicit user approval mandatory, dry-run mandatory, rollback plan required

## Test-Driven Development by Risk

### Low Risk
- Manual testing of success case
- Document side effects

### Medium Risk
- Test success and error cases
- Verify idempotency (run twice, same result)
- Document rollback procedure
- Test in isolated environment

### High Risk
- Comprehensive test suite required
- Staging environment testing mandatory
- Rollback procedure tested and documented
- Approval from project maintainers
- Version controlled with clear commit message

## Transaction Scripts

**Hard Requirement**: Multi-file writes must use a transaction script pattern.

When a task involves coordinated changes to multiple files:
1. Create a transaction script that updates all files
2. Use atomic operations where possible (mv, git add/commit)
3. Include rollback logic if partial failure occurs
4. Document the transaction boundaries clearly

This ensures consistency: Either all changes succeed or none do.

## Auto-Archive Heuristics

Scripts become candidates for archival when:
- Not executed in 90 days
- Superseded by newer version
- Marked as deprecated
- Accumulated 10+ archived versions

Archive script location: `.opencode/scripts/archive/YYYY-MM/`

## Git Integration Rules

Every script modification should be git-tracked:
- Create feature branch for new scripts: `git checkout -b scripts/new-feature`
- Commit with clear message: `git commit -m "Add script: description"`
- Sign commits if configured: Uses existing git config
- Push to origin: `git push origin scripts/new-feature`
- Never force-push to main

## Session Logging

Every session is automatically logged in `.opencode/sessions/` with:
- Start timestamp
- Mode used (if specific)
- Commands executed
- Results and outputs
- End timestamp

Logs are JSONL format for easy parsing and analysis.

## Resume Mechanism

If a session is interrupted:
1. Previous context is available in session log
2. Re-run command to resume from last completed step
3. Scripts marked with transaction boundaries can resume atomically
4. Session-logger plugin handles recovery context

## Max Narration Rule

**Always narrate what you're doing and why.**

Every major operation should include:
- Brief statement of plan before starting
- Status updates during multi-step work
- Explanation of decisions as they're made
- Result summary on completion

Never work silently. The user should always understand what's happening.

## Mode-Specific Behaviors

Modes adjust their approach based on tool resolution hierarchy and risk management:

- **build-py/build-ex**: Tier 0 (LSP) for syntax, Tier 3/4 for testing
- **debug**: Tier 2 (MCP) for external services, Tier 3 for diagnostic tools
- **plan/strategist**: Tier 0-1 only (no direct modifications)
- **review**: Tier 0 for analysis, no modifications
- **infra-architect/docker**: Tier 3/4 scripts preferred, Tier 5 for diagnostics
