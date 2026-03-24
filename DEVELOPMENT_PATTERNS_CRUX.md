# Development Patterns — Crux Project

Project-specific patterns for developing the Crux codebase. This supplements the ecosystem-wide methodology; it does not replace it.

**Relationship to other files:**
- **DEVELOPMENT_PATTERNS_CRUXDEV.md** (in `/Users/user/personal/cruxdev`) — the master methodology. Governs planning, convergence, execution, and auditing. All rules there apply here unless this file explicitly deviates.
- **CLAUDE.md** — project-level authority. Hard rules (architecture principles, contribution workflow, user preferences) override everything in this file.
- **This file** — captures Crux-specific architecture decisions, stack patterns, anti-patterns discovered during self-adoption, and deviations from CruxDev defaults. Living document, updated after each development round.

**When to read this file:**
- At the start of any development session in the Crux repo
- After reading CLAUDE.md and before writing code
- NOT needed if you already read DEVELOPMENT_PATTERNS_CRUXDEV.md and just need the Crux-specific delta

---

## 1. Architecture Decisions

### 1A. MCP Server as Universal Adapter

The MCP server (`scripts/lib/crux_mcp_server.py`, 43 tools) is the primary integration surface. All Crux capabilities are exposed via MCP, making them available to Claude Code, Cursor, Windsurf, and OpenCode without tool-specific adapters.

**Key separation:** Handler logic lives in `crux_mcp_handlers.py` (pure functions, no MCP dependency). The server file is thin wiring. This makes handlers testable without starting a server and prevents MCP library coupling from spreading.

**Why this matters for future work:** New capabilities go into handlers first, then get wired into the server. Never put business logic in the server file.

### 1B. Mode System (24 Modes, Markdown)

Modes are markdown files with YAML frontmatter in `modes/`. Each mode controls agent personality, think/no_think routing, and tool access level. Mode prompts follow research-backed conventions:
- Positive instruction framing only (no "don't do X")
- Critical rules at beginning and end (prime positions)
- Target 150-200 words

**Why this matters:** When adding or modifying modes, follow these conventions. Violations measurably degrade LLM output quality.

### 1C. Safety Pipeline (7 Gates)

Pre-flight validation → 8B adversarial audit → 32B second-opinion audit → human approval → DRY_RUN. Gates scale with risk level via `crux_pipeline_config.py`.

The 8B and 32B models are intentionally different — structural adversarial review, not self-review. The JS implementation of gates 2-3 (`run_script.js`) is superseded by the Python MCP server; the JS stubs remain as documentation of the original design.

### 1D. Symlink Installation

`setup.sh` symlinks repo directories into `~/.config/opencode/` rather than copying. This means `git pull` immediately updates everything. No reinstall needed for content changes.

**Implication for development:** Never hardcode absolute paths in installed files. All path resolution goes through `crux_paths.py`.

### 1E. Tri-Language Codebase

| Language | Role | Test Framework |
|----------|------|---------------|
| Python | Core logic (scripts/lib/, 38 modules) | pytest (39 files) |
| JavaScript | OpenCode plugins + tools (plugins/, tools/) | node:test (7 files) |
| Bash | CLI wrapper + installer (bin/crux, setup.sh) | bats (8 files) |

All three test suites must pass before any PR merges. The CI workflow (`.github/workflows/ci.yml`) enforces this.

---

## 2. Stack-Specific Patterns

### 2A. Python: stdlib-only for scripts/lib

All Python modules in `scripts/lib/` use the standard library only, with one exception: the `mcp` library for `crux_mcp_server.py`. No pip dependencies for anything else. This keeps installation friction at zero — users only need Python 3.

**Why this matters:** Before adding any import, check if stdlib has an equivalent. `urllib.request` over `requests`. `json` over any serialization library. `pathlib` over third-party path utilities.

### 2B. Python: No conftest.py

Test fixtures are defined inline in each test file. No `conftest.py` anywhere. This keeps each test file self-contained and readable — you can understand a test without chasing fixture definitions across files.

### 2C. Python: Inline Imports in Test Methods

Tests import their targets inside the test method, not at module level. This prevents import errors from blocking the entire test file and makes each test's dependencies explicit.

```python
def test_something(self, tmp_path):
    from scripts.lib.crux_session import update_session_state
    # test body
```

### 2D. Python: Mock Targets Use Full Module Path

When mocking, always use the full module path from the project root:

```python
@patch("scripts.lib.crux_session.Path.write_text")
```

Never mock relative to the test file. The full path prevents subtle bugs when modules re-export symbols.

### 2E. Python: tmp_path for Filesystem Isolation

Every test that touches the filesystem uses pytest's `tmp_path` fixture. No writing to the real filesystem, no cleanup logic, no test ordering dependencies.

---

## 3. Anti-Patterns Discovered During Self-Adoption

These were found during Phase 4 (Code Hardening) and Phase 6 (Documentation Convergence) of BUILD_PLAN_002.

### 3A. Non-Atomic Writes in Session State

**Found in:** `crux_session.py`, `extract_corrections.py`, `crux_bip.py`

Session state, correction logs, and BIP state were using direct `write_text()` calls. A crash mid-write corrupts the file with no recovery path.

**Fix applied:** All critical state files now use write-then-rename (`atomic_write` pattern from DEVELOPMENT_PATTERNS_CRUXDEV.md Section 6A). This is a hard rule for any file that persists across sessions.

**Future gate:** Any new state file must use atomic writes. Direct `write_text()` on state files is a code review rejection.

### 3B. Silent Exception Swallowing

**Found in:** Multiple modules during Phase 4 audit.

`except Exception: pass` or `except Exception: return None` with no logging. When these paths trigger in production, there is zero diagnostic information.

**Fix applied:** All exception handlers now log at minimum `logger.warning()` with the exception message.

**Future gate:** Bare `except: pass` is a code review rejection. Every exception handler must either re-raise, log, or explicitly document why silence is intentional.

### 3C. Double-Close Bug in secure_write_file

**Found in:** `crux_security.py` (Phase 4, audit pass 2)

The `secure_write_file` function called `os.close(fd)` in both the success path and the `finally` cleanup. If the success path closed the fd, the `finally` block would attempt to close an already-closed fd, potentially closing an unrelated fd that was assigned the same number.

**Fix applied:** Track close state with a flag; only close in `finally` if not already closed.

**Future gate:** Any function using `os.open()`/`os.close()` must use a close-tracking pattern or a context manager. Never rely on duplicate close being harmless.

### 3D. Phantom Modes in Documentation

**Found in:** `docs/manual.md` (Phase 6)

Documentation referenced 8 modes that did not exist in `modes/`. These were planned modes that were documented before implementation and never cleaned up.

**Fix applied:** Removed all phantom mode references.

**Future gate:** Mode documentation must be generated from or verified against the actual `modes/` directory contents. Never document a mode before its `.md` file exists.

### 3E. Stale Counts Everywhere

**Found in:** CLAUDE.md, README.md, docs/architecture.md, docs/modes.md, and 5 other files (Phase 6)

40+ hardcoded counts were wrong — test counts, mode counts, tool counts, module counts. CLAUDE.md said "338+ tests" when the actual count was 1517.

**Fix applied:** All counts updated to current values.

**Future gate:** After any change that adds or removes tests, tools, modes, or modules, grep for the old count across all `.md` files and update. Better: replace hardcoded counts with descriptive ranges or remove them entirely when the exact number adds no value.

---

## 4. Test Conventions

### 4A. Three Test Frameworks Must All Pass

```bash
# Python (with coverage gate)
python3 -m pytest tests/ --tb=short --cov=scripts/lib --cov-fail-under=100

# JavaScript
node --test tests/*.test.js

# Bash
bats tests/*.bats
```

All three must pass. A PR that passes pytest but breaks bats is not mergeable.

### 4B. Coverage-by-Coincidence Detection

A test can pass and appear to cover a line while actually exercising a different branch. The only source of truth is `--cov-report=term-missing`.

After writing coverage-targeting tests:
1. Run coverage with `--cov-report=term-missing`
2. Check: are the specific target line numbers gone from "Missing"?
3. If still missing: your test hit a different branch — trace the actual execution path

### 4C. E2E Test Approach

CLI E2E tests use subprocess calls against `bin/crux`. MCP E2E tests start the server and send JSON-RPC tool calls. Both use `tmp_path` for isolation.

E2E tests do NOT duplicate unit test coverage. They verify integration points that unit tests cannot reach (e.g., the CLI actually invokes the right Python module, the MCP server actually wires handlers to tools).

---

## 5. Crux-Specific Deviations from CruxDev Defaults

| Aspect | CruxDev Default | Crux Deviation | Reason |
|--------|----------------|----------------|--------|
| Test frameworks | One (project-appropriate) | Three (pytest + node:test + bats) | Tri-language codebase requires three frameworks |
| Language | Single-language assumed | Python + JavaScript + Bash | MCP server is Python, plugins are JS, CLI is Bash |
| conftest.py | Standard pytest convention | No conftest.py (inline fixtures) | Self-contained test files, no fixture hunting |
| BDD/feature files | Expected for user-facing features | Not used | Testing pyramid covered by unit + E2E; no Behave/Cucumber in stack |
| Git worktree isolation | Per-task worktrees | Not enforced (single-developer repo) | Overhead not justified for solo development; revisit if contributors join |

---

## 6. Future Development Gate

All future development on Crux follows DEVELOPMENT_PATTERNS_CRUXDEV.md:

1. **Plans are numbered with descriptors** — `BUILD_PLAN_NNN_DESCRIPTOR.md`
2. **Plans converge before execution** — focused audit, full-plan audit, viability assessment
3. **Execution uses TDD** — tests before code, 100% coverage maintained
4. **Code + docs converge together** — documentation is never deferred to a later phase
5. **E2E tests included** for any change to CLI or MCP server surfaces
6. **This file updated** after each development round (learnings admission gate applied)
7. **Three test suites must pass** — pytest, node:test, bats
8. **Atomic writes required** for any new state files
9. **No silent exception swallowing** — every handler logs or explicitly justifies silence
