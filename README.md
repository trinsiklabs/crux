# Crux

**The self-improving AI operating system.**

Crux is an open-source framework that wraps any LLM and any agentic tool to extract maximum effectiveness through specialized modes, continuous learning, and battle-tested reliability patterns. It works with local models (Ollama, llama.cpp, MLX) and cloud APIs (Anthropic, OpenAI), across agentic tools (OpenCode, Aider, Claude Code), and learns from every interaction to get better over time.

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

**Modes** are specialized contexts for different types of work — coding, architecture, debugging, legal analysis, psychological reflection, business strategy, and more. Each mode loads a research-optimized system prompt, restricts tool access to what's appropriate, and configures model parameters (temperature, sampling, thinking depth) for the task at hand. You don't ask the model to "act like a code reviewer." You switch to review mode, and the infrastructure configures everything for code review.

**The tool hierarchy** ensures the AI always uses the most reliable tool available. Custom tools (schema-validated, atomic operations) are preferred over MCP servers (structured external integrations), which are preferred over existing scripts (proven, reusable), which are preferred over new scripts (templated, audited), which are preferred over raw shell commands (last resort, logged). The hierarchy is enforced by plugin hooks — the AI can't skip a tier because the infrastructure checks before every tool invocation.

**The safety pipeline** gates every script through up to five stages before execution: deterministic pre-flight validation (structural checks, risk classification, path containment), adversarial AI audit by a separate model (semantic risk analysis), second-opinion AI audit for high-risk scripts (different model, different persona), human approval, and dry-run execution. The number of gates scales with risk — a read-only script passes through one gate in milliseconds; a production deployment script passes through all five.

**Continuous learning** is the engine that makes everything else improve over time. Every interaction is logged. Corrections are detected automatically and structured into knowledge entries. Tool usage patterns are analyzed to identify promotion candidates. Mode effectiveness is tracked across sessions and projects. The system surfaces daily digests with concrete, actionable recommendations — which modes need prompt revisions, which bash patterns should become tools, which knowledge gaps are causing repeat corrections. None of this requires you to do anything except approve the improvements the system proposes.

## Architecture

Crux operates at five levels, each feeding the next:

### Level 1: Interaction

Real-time detection of corrections and mistakes during active work. When you correct the AI, a plugin hook captures the pattern (what went wrong, what the fix was) and writes a structured reflection to the session log. This reflection stays in active context for the rest of the session, providing immediate in-session learning.

### Level 2: Continuous Processing

A background processor runs alongside your work, triggered by data thresholds (accumulated corrections, interaction count, token usage) rather than timers or session boundaries. It clusters corrections into knowledge entries, analyzes tool usage patterns for promotion candidates, scores mode effectiveness, and updates project context. Learning happens continuously and invisibly.

### Level 3: Cross-Session

Pattern detection across multiple sessions within a project. Identifies recurring correction topics (systemic gaps, not one-off mistakes), workflow fingerprints (repeated multi-step sequences that should become transaction scripts), and mode drift (using a mode for work outside its intended scope). Proposes new modes when drift patterns reveal unserved needs.

### Level 4: Cross-Project

Aggregation across all your projects. Detects when the same correction appears in multiple repos (indicating a mode-level weakness, not a project-level gap). Compares mode effectiveness across projects to identify knowledge base gaps. Triggers mode prompt optimization when accumulated evidence warrants it. Promotes proven scripts, tools, and knowledge entries from project-level to your personal library.

### Level 5: Ecosystem

Bidirectional learning between your system and the community. Battle-tested artifacts (scripts, tools, knowledge entries, MCP servers, mode refinements) that you promote to the public repo carry provenance metadata — what correction pattern birthed them, how many projects validated them, what measurable improvement they produced. Community contributions enter through a staging layer and must prove their value in your projects before integrating into your workflow.

## What Crux Is Not

**It is not tied to any specific LLM.** Crux works with Qwen, Llama, Claude, GPT, Gemini, or any model that supports tool use. The architecture is model-agnostic. When a better model comes out, Crux adapts — the modes, tools, knowledge base, and safety pipeline transfer unchanged.

**It is not tied to any specific agentic tool.** The initial implementation targets OpenCode CLI, with planned support for Aider, Claude Code, and Continue.dev. The modes, knowledge base, scripts library, and learning pipeline are tool-independent — they're files on disk with standard formats (Markdown, JSON, JSONL, JavaScript) that any tool can consume.

**It is not just for code.** Fifteen built-in modes span coding, architecture, debugging, data analysis, writing, psychological reflection, legal research, business strategy, AI infrastructure, and systems administration. Any knowledge domain that benefits from specialized context, tool restrictions, and accumulated learning can become a Crux mode.

**It is not a prompt library.** Prompts are one component. The value is in the infrastructure: the script execution pipeline, the continuous learning system, the tool hierarchy enforcement, the adversarial safety audits, the cross-project knowledge accumulation. These are code, not prompts.

## Addressing Skepticism

**"Self-improving AI sounds like marketing language."**

Nothing in Crux involves the AI modifying its own weights or doing anything magical. "Self-improving" means: corrections are captured as structured data, patterns are detected by scripted analytics, and improvements are proposed for human approval. The AI reads better knowledge entries and follows better-tuned mode prompts over time because the infrastructure puts better information in front of it. The human approves every structural change. The scripts do the maintenance. The AI just benefits from a progressively better-informed environment.

**"Local models aren't good enough for serious work."**

A 32B model at Q8 quantization, running on Apple Silicon with properly tuned sampling parameters, thinking mode for complex tasks, and a curated knowledge base providing domain context, is a remarkably capable system. Crux's architecture specifically addresses the gap between local and frontier models: the safety pipeline catches more mistakes, the knowledge base reduces the need for the model to reason from scratch, and the graceful degradation system tells you exactly when a task exceeds local model capability so you can make an informed decision about when cloud API calls are worth the cost.

**"This is over-engineered for a coding assistant."**

If all you need is autocomplete and occasional chat, Crux is not for you. Crux is for people who use AI as a primary working tool across multiple domains and multiple projects, who have experienced the frustration of AI assistants that forget everything between sessions, who have been burned by AI confidently making the wrong change to a production file, and who want their investment in correcting and teaching an AI system to compound over time rather than evaporate at session close.

**"I don't want to learn a whole new system."**

The quick start below takes five minutes. After that, you work normally — write code, ask questions, review PRs. Crux operates in the background. The daily digest tells you what improved and what needs attention. The modes are there when you want them. The safety pipeline runs automatically. The learning happens without you thinking about it.

---

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4) or Linux with NVIDIA GPU
- 32GB+ RAM (64GB recommended for Q8 quantization)
- Git and Homebrew installed

### Install

```bash
git clone https://github.com/yourusername/crux.git
cd crux
chmod +x setup.sh
./setup.sh
```

The setup script is interactive. It detects your hardware, recommends optimal model configuration, installs everything, and verifies the installation. Takes 5-15 minutes depending on model download speed.

### First Session

```bash
cd your-project
opencode
```

Switch modes with Tab or `/mode <name>`. Available modes:

```
build-py    build-ex    plan          infra-architect
review      debug       explain       analyst
writer      psych       legal         strategist
ai-infra    mac         docker
```

Everything else happens automatically. Write code, get corrections captured, watch your system get smarter.

See the [User Manual](docs/manual.md) for comprehensive usage documentation.

---

## Repository Structure

```
crux/
├── setup.sh                    # Interactive setup script (3,065 lines)
├── docs/
│   ├── manual.md               # User guide and tutorial
│   └── setup-reference.md      # Setup script documentation
├── modes/                      # 15 mode definitions + template
├── plugins/                    # 5 plugins (session logger, think router, etc.)
├── tools/                      # 7 custom tools (script management, knowledge, etc.)
├── commands/                   # 11 custom commands
├── scripts/templates/          # Script and transaction templates
├── templates/                  # AGENTS.md, PROJECT.md, opencode.json
├── knowledge/                  # Knowledge base template
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT
└── README.md
```

## The 15 Modes

| Category | Mode | Focus |
|----------|------|-------|
| Coding | build-py | Python, security-first |
| Coding | build-ex | Elixir/Phoenix/Ash |
| Architecture | plan | Software design |
| Architecture | infra-architect | Deployment, CI/CD |
| Quality | review | Code review, security priority |
| Quality | debug | Root cause analysis |
| Communication | explain | Teaching, mentoring |
| Communication | analyst | Data analysis |
| Communication | writer | Professional writing |
| Decision-Making | psych | ACT, attachment theory, shadow work |
| Decision-Making | legal | Legal research, contracts |
| Decision-Making | strategist | First principles, pre-mortems |
| Infrastructure | ai-infra | LLM stack optimization |
| Infrastructure | mac | macOS administration |
| Infrastructure | docker | Containers, Linux |

## The Tool Hierarchy

| Tier | Type | Reliability |
|------|------|-------------|
| 0 | LSP Servers | Deterministic code intelligence |
| 1 | Custom Tools | Schema-validated, atomic |
| 2 | MCP Servers | Protocol-enforced external access |
| 3 | Library Scripts | Tested, versioned, promoted |
| 4 | New Scripts | Templated, audited before run |
| 5 | Raw Bash | Logged, read-only only, last resort |

## The Safety Pipeline

| Risk Level | Gates | Applies To |
|------------|-------|-----------|
| Low | Pre-flight validation | Read-only operations |
| Medium | Pre-flight + 8B adversarial audit + DRY_RUN | File modifications, configs |
| High | Pre-flight + 8B audit + 32B audit + human approval + DRY_RUN | Deployment, database, deletes |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The most impactful contributions are battle-tested artifacts from your own Crux usage — knowledge entries, mode refinements, scripts, tools, and MCP servers that have been validated across projects.

## License

[MIT](LICENSE)
