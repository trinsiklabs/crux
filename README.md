# Crux

**The self-improving AI operating system.**

Crux is an open-source framework that wraps any LLM and any agentic tool to extract maximum effectiveness through specialized modes, continuous learning, and battle-tested reliability patterns. It works with local models (Ollama, llama.cpp, MLX) and cloud APIs (Anthropic, OpenAI), across agentic tools (OpenCode, Claude Code), and learns from every interaction to get better over time.

It is not another chatbot wrapper. It is an operating system for how you work with AI.

---

## The Problem

AI coding assistants are powerful but unreliable in predictable ways. They forget instructions mid-session. They make the same mistakes across sessions. They hallucinate confident nonsense. They modify files in ways you didn't expect. They can't tell you when they're struggling. And every new session starts from zero — no memory of what worked, what failed, or what you've told them three times already.

The typical response is better prompts. But prompts are the wrong abstraction. A prompt is a suggestion to a probabilistic system. It works most of the time, drifts some of the time, and fails silently. You can't build reliable workflows on suggestions.

Crux replaces suggestions with infrastructure.

## The Approach

Crux is built on a single principle: **everything the AI does must be enforced by code, not by instructions.**

When the AI needs to modify a file, it writes a script. The script goes through a safety pipeline. The script is logged, versioned, and auditable. If the AI keeps doing the same task, the script gets promoted to a reusable tool. If the same tool proves useful across projects, it graduates to the shared ecosystem. Nothing depends on the model remembering to do things correctly — the infrastructure makes it structurally impossible to do them incorrectly.

This principle extends to every layer of the system:

**Modes** are specialized contexts for different types of work — coding, architecture, debugging, security analysis, design, legal analysis, psychological reflection, business strategy, and more. Each mode loads a research-optimized system prompt, restricts tool access to what's appropriate, and configures model parameters (temperature, sampling, thinking depth) for the task at hand. You don't ask the model to "act like a code reviewer." You switch to review mode, and the infrastructure configures everything for code review.

**The tool hierarchy** ensures the AI always uses the most reliable tool available. Custom tools (schema-validated, atomic operations) are preferred over MCP servers (structured external integrations), which are preferred over existing scripts (proven, reusable), which are preferred over new scripts (templated, audited), which are preferred over raw shell commands (last resort, logged). The hierarchy is enforced by plugin hooks — the AI can't skip a tier because the infrastructure checks before every tool invocation.

**The safety pipeline** gates every script through up to seven stages before execution: deterministic pre-flight validation, TDD/BDD enforcement, recursive security audit, adversarial AI audit by a separate model, second-opinion AI audit for high-risk scripts, human approval, and dry-run execution. The number of gates scales with risk — a read-only script passes through one gate in milliseconds; a production deployment script passes through all seven.

**Continuous learning** is the engine that makes everything else improve over time. Every interaction is logged. Corrections are detected automatically and structured into knowledge entries. Tool usage patterns are analyzed to identify promotion candidates. Mode effectiveness is tracked across sessions. The system generates daily digests with concrete, actionable recommendations — which modes need prompt revisions, which bash patterns should become tools, which knowledge gaps are causing repeat corrections.

## Architecture

Crux operates at three scopes, each feeding the next:

### Project Scope (`.crux/`)

Each project gets a `.crux/` directory containing session state, corrections, knowledge entries, analytics, and pipeline configuration. This is the project's learning memory — it persists across sessions and across tool switches.

### User Scope (`~/.crux/`)

User-level configuration shared across all projects: mode definitions, shared knowledge, model registry, and analytics digests. Knowledge entries proven in one project can be promoted here to benefit all projects.

### Tool Adapters

Crux generates tool-specific configuration from `.crux/` data:
- **Claude Code**: `.claude/agents/` with mode-specific frontmatter, `.claude/rules/` from knowledge entries, hooks for interaction logging and correction detection
- **OpenCode**: Symlinks to `~/.config/opencode/` for modes, agents, and knowledge
- **Cursor**: `.cursor/rules/` with plain markdown rules, `.cursor/mcp.json` for MCP registration
- **Windsurf**: `.windsurf/rules/` with plain markdown rules, `.windsurf/mcp.json` for MCP registration
- **MCP Server**: 37-tool FastMCP server accessible from any MCP-compatible client

## The MCP Server

Crux exposes its capabilities via the Model Context Protocol, making them available to any MCP-compatible tool. The server provides 37 tools:

| Tool | Purpose |
|------|---------|
| `restore_context` | Rebuild full session context after restart |
| `get_session_state` / `update_session` | Read and modify session state |
| `lookup_knowledge` | Search knowledge across project and user scopes |
| `get_mode_prompt` / `list_modes` | Access mode definitions |
| `log_interaction` | Log conversation messages for analysis |
| `log_correction` | Record corrections for learning |
| `write_handoff` / `read_handoff` | Cross-mode context transfer |
| `switch_tool_to` | Switch between AI tools with config sync |
| `get_pipeline_config` / `get_active_gates` | Safety pipeline configuration |
| `start_tdd_gate` / `check_tdd_status` | TDD enforcement |
| `start_security_audit` / `security_audit_summary` | Recursive security auditing |
| `start_design_validation` / `design_validation_summary` | Design quality checks |
| `check_contrast` | WCAG contrast ratio validation |
| `validate_script` | Script safety convention checking |
| `promote_knowledge` | Promote knowledge project → user scope |
| `get_project_context` / `get_digest` | Project and analytics access |
| `verify_health` | Full static + liveness health check report |
| `audit_script_8b` / `audit_script_32b` | LLM-based adversarial script auditing (Gates 4-5) |
| `check_processor_thresholds` / `run_background_processors` | Threshold-triggered continuous learning |
| `get_processor_status` | Background processor run history |
| `register_project` / `get_cross_project_digest` | Cross-project analytics aggregation |
| `figma_get_tokens` / `figma_get_components` | Figma design token extraction |
| `bip_generate` / `bip_approve` / `bip_status` | Build-in-public content pipeline |

## What Crux Is Not

**It is not tied to any specific LLM.** Crux works with Qwen, Llama, Claude, GPT, Gemini, or any model that supports tool use. The architecture is model-agnostic.

**It is not tied to any specific agentic tool.** Current adapters support OpenCode, Claude Code, Cursor, and Windsurf, with the MCP server accessible from any MCP-compatible client. Modes, knowledge, scripts, and learning data are tool-independent files on disk.

**It is not just for code.** Twenty-three built-in modes span coding, architecture, debugging, testing, security analysis, design (UI, systems, accessibility, responsive), data analysis, writing, psychological reflection, legal research, business strategy, AI infrastructure, and systems administration.

**It is not a prompt library.** Prompts are one component. The value is in the infrastructure: the safety pipeline, the continuous learning system, the tool hierarchy enforcement, the TDD gate, the recursive security audits, the cross-session knowledge accumulation. These are code, not prompts.

---

## Quick Start

### Prerequisites

- macOS or Linux (Ubuntu 24.04+, Debian, etc.)
- Python 3.10+
- Git

### Claude Code

```bash
git clone https://github.com/trinsiklabs/crux.git ~/.crux
~/.crux/setup.sh        # Select "Claude Code" — installs deps + CLI (~10 seconds)
source ~/.bashrc          # or ~/.zshrc on macOS

cd your-project
crux adopt               # Sets up .crux/, MCP server (37 tools), and hooks
```

Start Claude Code in your project. The Crux MCP tools and hooks (correction detection, interaction logging, session context) are automatically available.

### OpenCode (Local LLMs)

```bash
git clone https://github.com/trinsiklabs/crux.git ~/.crux
~/.crux/setup.sh        # Select "OpenCode" — full setup (Ollama, models, symlinks)
source ~/.zshrc

cd your-project
crux switch opencode     # Or just launch opencode — MCP config is global
```

### Switch Tools Anytime

Already set up? Switch between tools without losing session state:

```bash
crux switch cursor       # Generate .cursor/rules/ + .cursor/mcp.json
crux switch windsurf     # Generate .windsurf/rules/ + .windsurf/mcp.json
crux switch claude-code  # Restore Claude Code hooks + MCP config
```

### Modes

Switch modes via your tool's agent/mode selector:

```
build-py          build-ex          plan              infra-architect
review            debug             explain           analyst
writer            psych             legal             strategist
ai-infra          mac               docker            test
security          marketing         build-in-public   design-ui
design-system     design-review     design-responsive design-accessibility
```

---

## Repository Structure

```
crux/
├── setup.sh                    # Interactive installer (symlink-based)
├── bin/crux                    # CLI wrapper (setup, update, doctor, adopt)
├── .crux/                      # Project-level Crux data (sessions, analytics, knowledge)
├── scripts/
│   └── lib/                    # 32 Python modules (stdlib + mcp dependency)
│       ├── crux_mcp_server.py  # 34-tool FastMCP server
│       ├── crux_mcp_handlers.py# Pure handler functions (no MCP deps)
│       ├── crux_hooks.py       # Claude Code hook handlers
│       ├── crux_session.py     # Session state management
│       ├── crux_sync.py        # Tool adapter layer (OpenCode, Claude Code, Cursor, Windsurf)
│       ├── crux_switch.py      # Tool switching with config sync
│       ├── crux_adopt.py       # Mid-session project onboarding
│       ├── crux_tdd_gate.py    # TDD/BDD enforcement gate
│       ├── crux_security_audit.py # Recursive security audit engine
│       ├── crux_design_validation.py # WCAG, contrast, touch targets
│       ├── crux_pipeline_config.py   # Gate activation per mode/risk
│       ├── crux_ollama.py            # Ollama REST API client (stdlib only)
│       ├── crux_llm_audit.py        # LLM-based script auditing (Gates 4-5)
│       ├── crux_background_processor.py # Threshold-triggered continuous learning
│       ├── crux_cross_project.py    # Cross-project analytics aggregation
│       ├── crux_figma.py            # Figma API client (design tokens)
│       ├── crux_cross_domain.py     # Cross-domain knowledge flows
│       ├── crux_design_handoff.py    # Design-to-code handoff
│       ├── crux_knowledge_categories.py # Structured KB taxonomy
│       ├── extract_corrections.py    # Correction clustering
│       ├── generate_digest.py        # Daily analytics digest
│       ├── promote_knowledge.py      # Three-tier knowledge promotion
│       ├── model_auto_evaluate.py    # Model quality comparison
│       ├── model_registry_update.py  # Ollama model discovery
│       ├── preflight_validator.py    # Gate 1: script validation
│       ├── audit_modes.py           # Mode prompt quality auditing
│       └── ...
├── modes/                      # 23 mode definitions (MD with YAML frontmatter)
├── plugins/                    # 6 OpenCode plugins (JS)
│   ├── session-logger.js       # JSONL logging, crash recovery
│   ├── think-router.js         # /think routing per mode
│   ├── correction-detector.js  # Real-time correction capture
│   ├── compaction-hook.js      # Context compaction with logging
│   ├── token-budget.js         # Per-mode token tracking
│   └── tool-enforcer.js        # Mode-based tool access control
├── tools/                      # 9 custom tools (JS)
│   ├── run_script.js           # Safety pipeline execution
│   ├── promote_script.js       # Script promotion (session → lib)
│   ├── list_scripts.js         # Script discovery
│   ├── project_context.js      # PROJECT.md reader
│   ├── lookup_knowledge.js     # Knowledge retrieval
│   ├── suggest_handoff.js      # Cross-mode handoff
│   ├── manage_models.js        # Model registry CRUD
│   ├── marketing_generate.js   # Content pipeline
│   └── marketing_update_state.js
├── commands/                   # Custom command definitions (MD)
├── templates/                  # AGENTS.md, PROJECT.md, opencode.json
├── knowledge/                  # Knowledge base template
├── docs/                       # Architecture, modes, safety, learning docs
├── tests/                      # 1480+ tests (pytest + node:test + bats)
├── CONTRIBUTING.md
├── LICENSE                     # MIT
└── README.md
```

## The 24 Modes

| Category | Mode | Focus |
|----------|------|-------|
| Coding | build-py | Python, security-first |
| Coding | build-ex | Elixir/Phoenix/Ash |
| Coding | test | Test-first development |
| Architecture | plan | Software design |
| Architecture | infra-architect | Deployment, CI/CD |
| Quality | review | Code review |
| Quality | debug | Root cause analysis |
| Quality | security | Adversarial vulnerability analysis |
| Communication | explain | Teaching, mentoring |
| Communication | analyst | Data analysis |
| Communication | writer | Professional writing |
| Communication | marketing | Marketing strategy, positioning |
| Communication | build-in-public | Shipping update content |
| Decision-Making | psych | ACT, attachment theory, shadow work |
| Decision-Making | legal | Legal research, contracts |
| Decision-Making | strategist | First principles, pre-mortems |
| Infrastructure | ai-infra | LLM stack optimization |
| Infrastructure | mac | macOS administration |
| Infrastructure | docker | Containers, Linux |
| Design | design-ui | UI component implementation |
| Design | design-system | Design system creation |
| Design | design-review | Design quality review |
| Design | design-responsive | Responsive layout |
| Design | design-accessibility | WCAG compliance |

## The Tool Hierarchy

| Tier | Type | Reliability |
|------|------|-------------|
| 0 | LSP Servers | Deterministic code intelligence |
| 1 | Custom Tools | Schema-validated, atomic |
| 2 | MCP Servers | Protocol-enforced external access |
| 3 | Library Scripts | Tested, versioned, promoted |
| 4 | New Scripts | Templated, audited before run |
| 5 | Raw Bash | Logged, last resort |

## The Safety Pipeline

| Gate | Stage | Implementation |
|------|-------|----------------|
| 1 | Pre-flight validation | `preflight_validator.py` — structural checks, risk classification |
| 2 | TDD/BDD enforcement | `crux_tdd_gate.py` — red/green phase tracking, coverage |
| 3 | Recursive security audit | `crux_security_audit.py` — 7 categories, convergence detection |
| 4 | 8B adversarial audit | `crux_llm_audit.py` + `run_script.js` — separate model reviews via Ollama |
| 5 | 32B second opinion | `crux_llm_audit.py` + `run_script.js` — high-risk only, larger model review |
| 6 | Human approval | `run_script.js` — required for high-risk scripts |
| 7 | DRY_RUN execution | `run_script.js` — safe preview for medium+ risk |

## Test Suite

1480+ tests across three frameworks:

- **Python (pytest)**: 1070+ tests across 30+ test files covering all Python modules with 100% coverage enforced
- **JavaScript (node:test)**: 199 tests covering plugins and tools
- **Bash (bats)**: 213 tests covering setup, CLI, and repo structure

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The most impactful contributions are battle-tested artifacts from your own Crux usage — knowledge entries, mode refinements, scripts, tools, and MCP servers that have been validated across projects.

## License

[MIT](LICENSE)
