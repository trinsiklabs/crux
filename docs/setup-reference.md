# Crux Setup Script

Complete interactive installer for Crux — a self-improving AI operating system for macOS (Apple Silicon).

## Overview

This is a 3,065-line comprehensive setup script that transforms a Mac into a fully-configured Crux system with:

- Local LLM infrastructure (Ollama + optimized models)
- 15 specialized AI modes for different tasks
- 11 custom commands for workflow optimization
- 7 custom tools for system integration
- 5 plugins for automatic enhancements
- 2 skills for session logging and script building
- Complete knowledge base infrastructure
- Analytics and session tracking
- Optional IDE integrations

## Features

### Hardware-Aware Installation
- Detects total and available RAM
- Identifies Apple Silicon chip (M1/M2/M3/M4)
- Recommends optimal model quantization based on hardware
- Warns if memory insufficient, suggests closing apps

### Intelligent Model Management
- Automatic quantization selection (Q8_0, Q6_K, Q4_K_M, Q4_K_S)
- Pulls primary model + compaction model + optional visual model
- Creates two Modelfile variants: crux-think (reasoning) and crux-chat (execution)
- Model registry with capability tracking

### 15 Specialized Modes
1. **build-py** - Python development (security-first)
2. **build-ex** - Elixir/Phoenix development
3. **plan** - Software architecture
4. **infra-architect** - Infrastructure & deployment
5. **review** - Code review (security priority)
6. **debug** - Root cause analysis
7. **explain** - Teaching & mentoring
8. **analyst** - Data analysis
9. **writer** - Professional writing
10. **psych** - Psychological reflection
11. **legal** - Legal research
12. **strategist** - First principles thinking
13. **ai-infra** - LLM infrastructure
14. **mac** - macOS systems
15. **docker** - Containers & infrastructure

Each mode includes complete prompts with core rules, methodologies, safety guidelines, and response formats.

### Framework Components

**AGENTS.md** - Framework documentation covering:
- Scripts-first design principle
- Tool resolution hierarchy (Tier 0-5)
- Script template with risk classification
- TDD requirements per risk level
- Transaction scripts for multi-file writes
- Auto-archive heuristics
- Git integration rules
- Session logging & resume mechanisms

**11 Custom Commands** - /promote, /scripts, /archive, /log, /init-project, /stats, /digest, /propose-mode, /review-knowledge, /review-community, /configure-api

**7 Custom Tools** - JavaScript implementations for script promotion, listing, execution, context retrieval, knowledge lookup, handoff suggestion, and model management

**5 Plugins** - Session logging, think-router, correction detection, session compaction, token budget enforcement

**2 Skills** - Session logging capability and script building workflow

## Installation

```bash
chmod +x setup.sh
./setup.sh
```

The script is fully interactive with numbered menus and state tracking for safe re-runs.

## System Requirements

- macOS 12+ (Apple Silicon: M1/M2/M3/M4)
- 16GB+ RAM minimum (32GB+ recommended)
- Homebrew installed
- ~30GB free disk space
- Internet connection

## Key Features

### Hardware Detection
Automatically detects RAM, chip type, and recommends optimal configuration.

### Intelligent Quantization
- 64GB+ → Q8_0 (best quality)
- 32-64GB → Q6_K
- 16-32GB → Q4_K_M
- <16GB → Q4_K_S (with warning)

### Tool Resolution Hierarchy
Tier 0 (LSP) → Tier 1 (Custom Tools) → Tier 2 (MCP) → Tier 3 (Library Scripts) → Tier 4 (New Scripts) → Tier 5 (Bash)

### Automatic Enhancements
- Session logging with crash recovery
- Mode-aware thinking routing
- Token budget enforcement
- Correction pattern detection
- Knowledge promotion pipeline

## Configuration Locations

```
~/.config/opencode/
├── opencode.json          # Main configuration
├── AGENTS.md             # Framework documentation
├── modes/                # 15 mode definitions
├── commands/             # 11 custom commands
├── tools/                # 7 JavaScript tools
├── plugins/              # 5 plugins with full implementations
├── skills/               # 2 skill definitions
├── knowledge/            # Per-mode knowledge base
├── models/               # Model registry
└── analytics/            # Usage tracking
```

## After Installation

```bash
source ~/.zshrc              # Reload shell
ollama list                  # Verify models
opencode /init-project myapp # Initialize project
opencode --mode build-py     # Start using
```

## Script Structure (3,065 lines)

- Helper functions with colored output
- State tracking for idempotency
- 18 sequential setup steps
- Hardware detection with memory math
- Ollama installation and verification
- Intelligent model selection
- Modelfile creation with system prompts
- Environment configuration
- All 15 modes with complete prompts
- AGENTS.md framework documentation
- 11 custom commands with descriptions
- 7 custom tools with Zod schemas
- 5 plugins (3 full implementations, 2 stubs)
- 2 skills with capability descriptions
- Knowledge base structure
- Model registry setup
- Analytics infrastructure
- Optional IDE integrations
- Final verification checklist

## Highlights

- Pure bash with no external dependencies
- Fully idempotent (safe to re-run)
- Interactive numbered menus only
- Comprehensive error handling
- State tracking prevents duplicate work
- Hardware-aware optimization
- Production-ready plugin implementations
- Complete system prompt with critical rules
- Risk-based execution framework
- Knowledge promotion pipeline
- Session logging and recovery

## License

Part of the Crux self-improving AI operating system project.

Version 1.0 | Created 2026-03-05 | Production Ready
