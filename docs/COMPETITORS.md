# Crux — Competitive Analysis

The AI coding tools market exceeds $35B with 150M+ developers on GitHub. Every tool traps intelligence in vendor-specific directories. Crux is the only tool-agnostic intelligence layer — .crux/ stores corrections, knowledge, session state, and modes that travel with you across any AI coding tool. We don't compete with these tools; we make all of them better.

## Official Competitors

### Cursor
**URL:** https://cursor.com
**Category:** official
**Pricing:** $20/month Pro, $40/month Business

AI-first code editor built on VS Code with integrated AI coding assistance

**Strengths:**
- Polished IDE experience
- $2B+ ARR
- Large user base
- Fast iteration
- Good UX

**Weaknesses:**
- Vendor lock-in (.cursor/ directory)
- No cross-tool portability
- No learning from corrections
- No safety pipeline
- Intelligence trapped in their ecosystem
**Revenue Model:** subscription

### Claude Code
**URL:** https://claude.ai/code
**Category:** official
**Pricing:** API usage-based ($3-15/MTok)

Anthropic's CLI agent for coding — hooks system, MCP support, agentic workflows

**Strengths:**
- Best instruction-following model
- Hook system enables deep integration
- MCP ecosystem
- Anthropic backing
- Opus/Sonnet model quality

**Weaknesses:**
- Intelligence locked in .claude/
- No cross-tool portability
- No learning from corrections across sessions
- No safety pipeline beyond model guardrails
- Expensive API costs
**Revenue Model:** usage

### Windsurf
**URL:** https://windsurf.com
**Category:** official
**Pricing:** Free tier, $15/month Pro

AI-powered IDE (formerly Codeium) with Cascade agent and flows

**Strengths:**
- Good free tier
- Cascade agent is capable
- Growing fast

**Weaknesses:**
- Global-only MCP config
- No project-level isolation
- Intelligence locked in platform
- No cross-tool portability
**Revenue Model:** freemium

### Aider
**URL:** https://aider.chat
**Category:** official
**Pricing:** Free (open source), API costs for models

Open-source AI pair programming in the terminal — repo map, git integration

**Strengths:**
- Open source
- Excellent repo map
- Git integration
- Multi-model
- Terminal-native

**Weaknesses:**
- No MCP support
- No cross-tool portability
- No learning from corrections
- No safety pipeline
- No session state persistence
**Revenue Model:** open_source

## Watch Competitors

### Copilot
**URL:** https://github.com/features/copilot
**Category:** watch
**Pricing:** $10/month Individual, $19/month Business

GitHub's AI coding assistant — inline completions, chat, workspace agent

**Strengths:**
- Massive distribution (GitHub)
- Enterprise adoption
- Multi-IDE

**Weaknesses:**
- Autocomplete-focused
- No agentic workflows
- No learning
- No safety pipeline
- Locked to GitHub ecosystem
**Revenue Model:** subscription

### Replit
**URL:** https://replit.com
**Category:** watch
**Pricing:** $25/month Hacker, custom Enterprise

Cloud IDE and deployment platform with AI agent

**Strengths:**
- $9B valuation
- Full platform (IDE + deploy)
- Mass market reach

**Weaknesses:**
- Code quality crisis (2.74x more vulnerabilities)
- Agent reliability issues
- Locked to platform
- No local development
- No portability
**Revenue Model:** subscription

### Lovable
**URL:** https://lovable.dev
**Category:** watch
**Pricing:** $20/month Starter, $50/month Launch

AI-powered full-stack app builder — prompt to deployed app

**Strengths:**
- $100M ARR in 8 months
- Fast time-to-app
- Non-developer friendly

**Weaknesses:**
- 10% of apps leaked user data
- No code quality controls
- No learning
- Platform lock-in
- Not for professional developers
**Revenue Model:** subscription

### Roo Code
**URL:** https://roocode.com
**Category:** watch
**Pricing:** Free (open source)

AI coding assistant with MCP support — VS Code extension

**Strengths:**
- MCP support
- Customizable
- Growing community

**Weaknesses:**
- Smaller ecosystem
- No cross-tool portability
- No learning system
- VS Code only
**Revenue Model:** open_source

## Gap Analysis

| Feature | Crux | Aider | Claude Code | Copilot | Cursor | Lovable | Replit | Roo Code | Windsurf |
|---|---|---|---|---|---|---|---|---|---|
| .claude/ directory | N | N | Y | N | N | N | N | N | N |
| .cursor/rules/ for context | N | N | N | N | Y | N | N | N | N |
| .windsurf/rules/ | N | N | N | N | N | N | N | N | Y |
| 24 specialized modes | Y | N | N | N | N | N | N | N | N |
| 43 MCP tools | Y | N | N | N | N | N | N | N | N |
| 7-gate safety pipeline | Y | N | N | N | N | N | N | N | N |
| AI agent | N | N | N | N | N | N | Y | N | N |
| AI code completion | N | N | N | N | Y | N | N | N | N |
| Agentic coding | N | N | Y | N | N | N | N | N | N |
| Cascade agent | N | N | N | N | N | N | N | N | Y |
| Cloud IDE | N | N | N | N | N | N | Y | N | N |
| GitHub integration | N | N | N | Y | N | N | N | N | N |
| Inline completions | N | N | N | Y | N | N | N | N | N |
| MCP server support | N | N | Y | N | N | N | N | N | N |
| MCP support | N | N | N | N | Y | N | N | Y | Y |
| Prompt-to-app | N | N | N | N | N | Y | N | N | N |
| Repo map (AST-based file ranking) | N | Y | N | N | N | N | N | N | N |
| Supabase integration | N | N | N | N | N | Y | N | N | N |
| TDD enforcement gate | Y | N | N | N | N | N | N | N | N |
| VS Code extension | N | N | N | N | N | N | N | Y | N |
| VS Code/JetBrains integration | N | N | N | Y | N | N | N | N | N |
| architect mode | N | Y | N | N | N | N | N | N | N |
| auto-handoff on exit | Y | N | N | N | N | N | N | N | N |
| background agents | N | N | Y | N | N | N | N | N | N |
| build-in-public pipeline (Typefully integration) | Y | N | N | N | N | N | N | N | N |
| chat | N | N | N | Y | N | N | N | N | N |
| chat with codebase | N | N | N | N | Y | N | N | N | N |
| codebase awareness | N | N | N | N | N | N | N | N | Y |
| codebase indexing | N | N | N | N | Y | N | N | N | N |
| composer mode | N | N | N | N | Y | N | N | N | N |
| continuous learning from corrections | Y | N | N | N | N | N | N | N | N |
| correction detection (10 regex patterns) | Y | N | N | N | N | N | N | N | N |
| cross-project analytics | Y | N | N | N | N | N | N | N | N |
| custom modes | N | N | N | N | N | N | N | Y | N |
| daily digest generation | Y | N | N | N | N | N | N | N | N |
| database | N | N | N | N | N | N | Y | N | N |
| deployment | N | N | N | N | N | Y | N | N | N |
| design system | N | N | N | N | N | Y | N | N | N |
| design validation (WCAG) | Y | N | N | N | N | N | N | N | N |
| file context management | N | N | N | N | N | N | N | Y | N |
| flows (multi-step) | N | N | N | N | N | N | N | N | Y |
| full-stack generation | N | N | N | N | N | Y | N | N | N |
| git-aware editing | N | Y | N | N | N | N | N | N | N |
| hooks system (SessionStart, PostToolUse, etc.) | N | N | Y | N | N | N | N | N | N |
| hosting | N | N | N | N | N | N | Y | N | N |
| impact analysis (analyze_impact) | Y | N | N | N | N | N | N | N | N |
| knowledge promotion (project→user→public) | Y | N | N | N | N | N | N | N | N |
| linting integration | N | Y | N | N | N | N | N | N | N |
| memory system | N | N | Y | N | N | N | N | N | N |
| multi-file editing | N | N | N | N | Y | N | N | N | N |
| multi-model | N | N | N | N | N | N | N | Y | N |
| multi-model support | N | Y | N | N | N | N | N | N | N |
| multiplayer editing | N | N | N | N | N | N | Y | N | N |
| one-click deploy | N | N | N | N | N | N | Y | N | N |
| per-project MCP isolation | Y | N | N | N | N | N | N | N | N |
| plan mode | N | N | Y | N | N | N | N | N | N |
| recursive security audit | Y | N | N | N | N | N | N | N | N |
| seamless tool switching (crux switch) | Y | N | N | N | N | N | N | N | N |
| session state portability | Y | N | N | N | N | N | N | N | N |
| terminal integration | N | N | N | N | Y | N | N | N | Y |
| tool recipe engine (6 tools) | Y | N | N | N | N | N | N | N | N |
| tool-agnostic intelligence (.crux/ directory) | Y | N | N | N | N | N | N | N | N |
| voice coding | N | Y | N | N | N | N | N | N | N |
| workspace agent | N | N | N | Y | N | N | N | N | N |
| worktrees | N | N | Y | N | N | N | N | N | N |

### Must-Close
- **MCP support** — has: Cursor, Windsurf, Roo Code
- **terminal integration** — has: Cursor, Windsurf

### Should-Close
- **.claude/ directory** — has: Claude Code
- **.cursor/rules/ for context** — has: Cursor
- **.windsurf/rules/** — has: Windsurf
- **AI code completion** — has: Cursor
- **Agentic coding** — has: Claude Code
- **Cascade agent** — has: Windsurf
- **MCP server support** — has: Claude Code
- **Repo map (AST-based file ranking)** — has: Aider
- **architect mode** — has: Aider
- **background agents** — has: Claude Code
- **chat with codebase** — has: Cursor
- **codebase awareness** — has: Windsurf
- **codebase indexing** — has: Cursor
- **composer mode** — has: Cursor
- **flows (multi-step)** — has: Windsurf
- **git-aware editing** — has: Aider
- **hooks system (SessionStart, PostToolUse, etc.)** — has: Claude Code
- **linting integration** — has: Aider
- **memory system** — has: Claude Code
- **multi-file editing** — has: Cursor
- **multi-model support** — has: Aider
- **plan mode** — has: Claude Code
- **voice coding** — has: Aider
- **worktrees** — has: Claude Code

### Nice-To-Have
- **AI agent** — has: Replit
- **Cloud IDE** — has: Replit
- **GitHub integration** — has: Copilot
- **Inline completions** — has: Copilot
- **Prompt-to-app** — has: Lovable
- **Supabase integration** — has: Lovable
- **VS Code extension** — has: Roo Code
- **VS Code/JetBrains integration** — has: Copilot
- **chat** — has: Copilot
- **custom modes** — has: Roo Code
- **database** — has: Replit
- **deployment** — has: Lovable
- **design system** — has: Lovable
- **file context management** — has: Roo Code
- **full-stack generation** — has: Lovable
- **hosting** — has: Replit
- **multi-model** — has: Roo Code
- **multiplayer editing** — has: Replit
- **one-click deploy** — has: Replit
- **workspace agent** — has: Copilot
