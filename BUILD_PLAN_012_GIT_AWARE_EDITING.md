# BUILD_PLAN_012: Git-Aware Editing — Context from Version History

**Created:** 2026-03-26
**Status:** NOT STARTED
**Priority:** SHOULD-CLOSE
**Competitive Gap:** Aider's git integration understands diffs, auto-commits with meaningful messages, and uses git context for better edits. Crux captures git commits as decisions but doesn't use git context to improve editing.
**Goal:** Crux provides git-aware context to any connected tool — current diff, recent changes to a file, blame info, branch context — so the AI makes better edits informed by version history.

**Constraint:** TDD, 100% coverage on new code.
**Constraint:** stdlib + subprocess (git CLI) only.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

When an AI edits a file, knowing "this function was refactored 3 times this week" or "this line was last changed to fix a security bug" changes how it approaches the edit. Git history is rich context that no tool currently feeds to the AI systematically.

## Architecture

```
MCP tools for git context:
  git_context(filepath)     → recent changes, blame, branch
  git_diff()                → current uncommitted changes
  git_file_history(path, n) → last N commits touching this file
  git_suggest_commit()      → generate commit message from staged changes
  git_risk_assessment()     → which files are risky to edit (high churn + many authors)
```

---

## Phase 1: Git Context Provider

- [ ] 1.1 Create `scripts/lib/crux_git_context.py`
- [ ] 1.2 `get_current_diff(root)` → `str` — `git diff` output (staged + unstaged)
- [ ] 1.3 `get_file_history(root, filepath, n=10)` → `list[CommitInfo]` — last N commits with message, author, date, diff stats
- [ ] 1.4 `get_blame_summary(root, filepath)` → `dict[line_range, author+date]` — who changed what recently
- [ ] 1.5 `get_branch_context(root)` → `dict` — current branch, ahead/behind, recent branches
- [ ] 1.6 Tests with fixture git repos

## Phase 2: Risk Assessment

- [ ] 2.1 `assess_file_risk(root, filepath)` → `RiskScore` — churn rate + author count + recent bugs
- [ ] 2.2 `get_risky_files(root, top_n=10)` → files most likely to cause problems if edited
- [ ] 2.3 Integrate with analyze_impact: risky files get flagged in results
- [ ] 2.4 Tests for risk scoring

## Phase 3: Commit Intelligence

- [ ] 3.1 `suggest_commit_message(root)` → `str` — generate message from staged changes using diff analysis
- [ ] 3.2 Conventional commit format detection: if repo uses conventional commits, match the style
- [ ] 3.3 `get_commit_patterns(root)` → `dict` — detected patterns (prefixes, max length, co-author)
- [ ] 3.4 Tests for message generation

## Phase 4: MCP Tools

- [ ] 4.1 `git_context(filepath)` — full context for a file (history + blame + risk)
- [ ] 4.2 `git_diff()` — current uncommitted changes
- [ ] 4.3 `git_file_history(filepath, n)` — commit history
- [ ] 4.4 `git_suggest_commit()` — generate commit message
- [ ] 4.5 `git_risky_files()` — files to be careful editing
- [ ] 4.6 Integrate into restore_context: include current diff summary + branch context
- [ ] 4.7 Tests for all MCP tools

---

## Convergence Criteria

- Git context available for any file via MCP
- Risk assessment identifies high-churn / multi-author files
- Commit message suggestions match repo style
- Current diff and branch context in restore_context
- Works on any git repo (not Crux-specific)
- Two consecutive clean audit passes
