# CLAUDE.md — Project Context for Crux

## What This Project Is

Crux is a self-improving AI operating system — an open-source framework that wraps any LLM (local or cloud) and any agentic tool (OpenCode, Aider, Claude Code) to maximize effectiveness through specialized modes, continuous learning, and infrastructure-enforced reliability.

It is not tied to any specific model or tool. It is the intelligence layer that makes any LLM setup maximally effective.

## Repository Structure

```
crux/
├── setup.sh                    # Interactive installer (20 steps, symlink-based)
├── bin/crux                    # CLI wrapper (setup, update, doctor, adopt)
├── modes/                      # 24 specialized mode prompts (MD with YAML frontmatter)
├── plugins/                    # 7 OpenCode plugins (JS)
│   ├── session-logger.js       # JSONL logging, crash recovery, checkpoints
│   ├── think-router.js         # /think and /no_think routing per mode
│   ├── correction-detector.js  # Real-time correction capture
│   ├── compaction-hook.js      # Context compaction with state preservation
│   ├── token-budget.js         # Per-mode token tracking and enforcement
│   ├── tool-enforcer.js        # Mode-based tool access control
│   └── crux-bridge.js          # CruxCLI bridge (symlink to cruxcli repo)
├── tools/                      # 9 custom tools (JS with Zod schemas)
│   ├── promote_script.js       # Atomic script promotion (session → lib)
│   ├── list_scripts.js         # Library script discovery with header parsing
│   ├── run_script.js           # Five-gate safety pipeline execution
│   ├── project_context.js      # PROJECT.md reader with section filtering
│   ├── lookup_knowledge.js     # Mode-scoped knowledge retrieval
│   ├── suggest_handoff.js      # Cross-mode handoff with context files
│   ├── manage_models.js        # Model registry CRUD operations
│   ├── marketing_generate.js   # Content pipeline generation
│   └── marketing_update_state.js # Marketing state management
├── commands/                   # 12 custom command definitions (MD)
├── scripts/
│   ├── lib/                    # 38 Python modules (stdlib + mcp)
│   │   ├── crux_mcp_server.py          # 43-tool FastMCP server
│   │   ├── crux_mcp_handlers.py        # Pure handler functions (no MCP deps)
│   │   ├── crux_hooks.py               # Claude Code hook handlers
│   │   ├── crux_hook_runner.py         # Hook execution engine
│   │   ├── crux_session.py             # Session state management
│   │   ├── crux_status.py              # Status reporting
│   │   ├── crux_sync.py                # Tool adapter layer (OpenCode, Claude Code, Cursor, Windsurf)
│   │   ├── crux_switch.py              # Tool switching with config sync
│   │   ├── crux_adopt.py               # Mid-session project onboarding
│   │   ├── crux_init.py                # Project initialization
│   │   ├── crux_paths.py               # Path resolution utilities
│   │   ├── crux_tdd_gate.py            # TDD/BDD enforcement gate
│   │   ├── crux_security.py            # Security primitives
│   │   ├── crux_security_audit.py      # Recursive security audit engine
│   │   ├── crux_design_validation.py   # WCAG, contrast, touch targets
│   │   ├── crux_design_handoff.py      # Design-to-code handoff
│   │   ├── crux_pipeline_config.py     # Gate activation per mode/risk
│   │   ├── crux_ollama.py              # Ollama REST API client (stdlib only)
│   │   ├── crux_llm_audit.py           # LLM-based script auditing (Gates 4-5)
│   │   ├── crux_background_processor.py # Threshold-triggered continuous learning
│   │   ├── crux_cross_project.py       # Cross-project analytics aggregation
│   │   ├── crux_cross_domain.py        # Cross-domain knowledge flows
│   │   ├── crux_figma.py               # Figma API client (design tokens)
│   │   ├── crux_knowledge_categories.py # Structured KB taxonomy
│   │   ├── crux_typefully.py           # Typefully API integration
│   │   ├── crux_bip.py                 # Build-in-public engine
│   │   ├── crux_bip_gather.py          # BIP content gathering
│   │   ├── crux_bip_triggers.py        # BIP trigger detection
│   │   ├── crux_audit_backend.py       # Audit backend services
│   │   ├── extract_corrections.py      # Correction clustering
│   │   ├── generate_digest.py          # Daily analytics digest
│   │   ├── promote_knowledge.py        # Three-tier knowledge promotion
│   │   ├── update_project_context.py   # Project context updates
│   │   ├── model_auto_evaluate.py      # Model quality comparison
│   │   ├── model_registry_update.py    # Ollama model discovery
│   │   ├── preflight_validator.py      # Gate 1: script validation
│   │   ├── audit_modes.py              # Mode prompt quality auditing
│   │   └── __init__.py
│   └── templates/              # Script and transaction templates
├── skills/                     # Skill definitions (SKILL.md per skill)
├── templates/                  # AGENTS.md, PROJECT.md, opencode.json
├── knowledge/                  # Knowledge base template + per-mode dirs
├── docs/                       # Architecture, modes, safety, learning docs
├── tests/                      # 1374+ tests (pytest: 41 files, node:test: 7 files, bats: 8 files)
│                               # 100% coverage enforced on scripts/lib/ via pytest --cov-fail-under=100
├── CONTRIBUTING.md
├── LICENSE                     # MIT
└── README.md
```

## Installation Architecture

Setup.sh **symlinks** repo directories into `~/.config/opencode/` rather than copying files inline. This means:
- `git pull` in the repo immediately updates all modes, plugins, tools, commands, and scripts
- `crux update` = `git pull` + `setup.sh --update` (refreshes symlinks)
- `crux doctor` validates the installation health

Symlinked directories: modes/, plugins/, tools/, commands/, skills/, scripts/lib/, scripts/templates/
User data directories (not symlinked): knowledge/, models/, analytics/, scripts/session/, scripts/archive/

## Architecture Principles

1. **Scripts-first**: All filesystem modifications go through scripts. Never modify files directly. The AI writes scripts, scripts modify files.

2. **Tool hierarchy**: Tier 0 (LSP) → Tier 1 (Custom Tools) → Tier 2 (MCP Servers) → Tier 3 (Library Scripts) → Tier 4 (New Scripts) → Tier 5 (Raw Bash). Always prefer higher tiers. Tier 5 should trend toward zero.

3. **Infrastructure over instructions**: Enforce behavior through code (plugin hooks, tool schemas, pre-flight validators), not through prompt instructions that drift.

4. **Continuous learning**: Corrections are captured automatically, clustered into knowledge entries, promoted across projects, and shared with the ecosystem. The system improves itself.

5. **Three-tier scope**: Project (`.crux/`) → User (`~/.crux/`) → Public (this repo). Artifacts promote upward as they prove value.

6. **Five-gate safety pipeline**: Pre-flight validation → 8B adversarial audit → 32B second-opinion audit → human approval → DRY_RUN. Gates scale with risk level.

7. **MCP server as universal adapter**: The 43-tool FastMCP server (`scripts/lib/crux_mcp_server.py`) exposes all Crux capabilities via the Model Context Protocol, making them available to any MCP-compatible client (Claude Code, Cursor, Windsurf, OpenCode). Handler logic lives in `crux_mcp_handlers.py` (pure functions, no MCP dependency) for testability.

## Development Methodology

This project follows DEVELOPMENT_PATTERNS_CRUXDEV.md (in `/Users/user/personal/cruxdev`) for planning, convergence, and execution. Project-specific patterns, anti-patterns, and stack conventions are captured in **DEVELOPMENT_PATTERNS_CRUX.md** (in this repo). Read both at the start of any development session.

## Test Infrastructure

- **1374+ tests** across pytest (41 files), node:test (7 files), and bats (8 files)
- **100% coverage enforced** on `scripts/lib/` via `pytest --cov=scripts/lib --cov-fail-under=100`
- All PRs must pass: `python3 -m pytest tests/ --tb=short --cov=scripts/lib --cov-fail-under=100`

## Key Design Decisions

- **Positive instruction framing only** in mode prompts. Research shows negative instructions ("don't do X") measurably degrade LLM output compared to positive framing ("do Y instead").
- **Critical rules at beginning and end** of mode prompts (prime positions). The model pays most attention to the start and end of system prompts.
- **Mode prompts target 150-200 words**. Research shows this is the optimal length range.
- **Two Modelfile variants**: `crux-think` (temperature 0.6, top_p 0.95) for reasoning modes, `crux-chat` (temperature 0.7, top_p 0.8) for execution modes. Routed automatically by the think-router plugin.
- **Separate auditor model**: The 8B model audits scripts written by the 32B model. Different model = structural adversarial review, not self-review.
- **Transaction scripts required** for multi-file writes. Hard requirement enforced by pre-flight validator, not a suggestion.
- **Daily digest** (not weekly) because the user works across many active projects and won't return to any single project on a weekly cadence.
- **Continuous background processing** triggered by data thresholds (queue size, interaction count, token usage), not cron jobs or session events.
- **Max narration mode**: The AI must always narrate what it's doing. Never work silently. This is a global rule in the Modelfile system prompt.
- **Symlink-based installation**: setup.sh symlinks repo dirs into ~/.config/opencode/ so `git pull` instantly updates everything. No re-run needed for content changes.

## The 24 Modes

| Mode | Domain | Think/NoThink | Tool Access |
|------|--------|---------------|-------------|
| build-py | Python development | no_think | full |
| build-ex | Elixir/Phoenix/Ash | no_think | full |
| test | Test-first development | no_think | full |
| plan | Software architecture | think | read-only |
| infra-architect | Deployment/CI-CD | think | read-only |
| review | Code review | think | read-only |
| security | Adversarial vulnerability analysis | think | read-only |
| debug | Root cause analysis | think | full |
| explain | Teaching/mentoring | no_think | read-only |
| analyst | Data analysis | no_think | full |
| writer | Professional writing | no_think | read-only |
| marketing | Marketing strategy/copywriting | no_think | read-only |
| build-in-public | Shipping update content | no_think | full |
| psych | ACT/Attachment/Shadow/Somatic | think | read-only |
| legal | Legal research | think | read-only |
| strategist | First principles strategy | think | read-only |
| ai-infra | LLM infrastructure | no_think | full |
| mac | macOS systems | no_think | read-only |
| docker | Containers/Linux | no_think | full |
| design-ui | UI component implementation | no_think | full |
| design-system | Design system creation | no_think | full |
| design-review | Design quality review | think | read-only |
| design-responsive | Responsive layout | no_think | full |
| design-accessibility | WCAG compliance | think | read-only |

## Contribution Workflow

This repo is owned by `trinsiklabs`. All edits come as PRs from the `tecto` fork.

```bash
git checkout -b feature/whatever
# make changes
git push -u origin feature/whatever
gh pr create --repo trinsiklabs/crux --title "Title" --body "Description"
```

## What Still Needs Building

### OpenCode Integration Verification
- Verify plugin hook format matches OpenCode's actual plugin system
- Verify tool export format matches OpenCode's custom tool loading
- Verify command/mode file format matches OpenCode's expectations
- Test end-to-end with a real OpenCode session

## User Preferences

- Always use numbered lists for questions, never bullets
- When discussing things "one at a time," present each item individually and wait for confirmation
- Always narrate what you're doing — never work silently
- Daily cadence for digests and notifications, not weekly
- The user works primarily in Python locally and Elixir/Phoenix/Ash/PostgreSQL for web apps
- The user's Mac is an M1 Max with 64GB RAM
