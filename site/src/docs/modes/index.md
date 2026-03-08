---
layout: base.njk
title: Modes System
description: How Crux modes work and how to create custom modes
---

# Modes System

Modes are specialized prompts that shape AI behavior for different types of work.

## How Modes Work

Each mode is a Markdown file in `~/.crux/modes/` with YAML frontmatter:

```markdown
---
name: security
description: Security-focused code review and hardening
temperature: 0.3
tool_constraints: read-heavy
think_mode: extended
gates: [0, 1, 2, 3, 4, 5]
---

# Security Mode

You are a security-focused code reviewer...
```

## Frontmatter Fields

| Field | Description | Values |
|-------|-------------|--------|
| `name` | Mode identifier | String |
| `description` | One-line description | String |
| `temperature` | LLM temperature | 0.0 - 1.0 |
| `tool_constraints` | Tool usage pattern | `read-heavy`, `write-heavy`, `balanced` |
| `think_mode` | Reasoning depth | `none`, `standard`, `extended` |
| `gates` | Safety gates to activate | Array of gate numbers |

## Using Modes

### Via MCP

```
Tool: get_mode_prompt
Input: { "mode": "security" }
Output: { "prompt": "# Security Mode\n\nYou are..." }
```

### Via CLI

```bash
# List modes
crux modes

# Get mode prompt
crux mode security
```

### In Session

Session state tracks active mode:

```json
{
  "active_mode": "security",
  "active_tool": "claude-code"
}
```

## Built-in Modes (24)

### Development
- `build-py` — Python development
- `build-ex` — Elixir development
- `test` — Test writing and TDD

### Review & Analysis
- `review` — Code review
- `debug` — Debugging
- `explain` — Code explanation
- `analyst` — Data analysis

### Security
- `security` — Security audit and hardening

### Design
- `design-ui` — UI design
- `design-system` — Design systems
- `design-review` — Design review
- `design-responsive` — Responsive design
- `design-accessibility` — Accessibility

### Infrastructure
- `infra-architect` — Infrastructure architecture
- `docker` — Docker and containers
- `ai-infra` — AI infrastructure

### Planning & Strategy
- `plan` — Planning mode
- `strategist` — Strategic thinking

### Communication
- `writer` — Technical writing
- `marketing` — Marketing content
- `build-in-public` — Social content
- `legal` — Legal review

### Specialized
- `mac` — macOS development
- `psych` — Psychology/UX research

## Creating Custom Modes

1. Create a file in `~/.crux/modes/`:

```bash
cat > ~/.crux/modes/my-mode.md << 'EOF'
---
name: my-mode
description: My custom mode
temperature: 0.5
tool_constraints: balanced
think_mode: standard
gates: [0, 1, 2]
---

# My Custom Mode

You are specialized for [my use case]...

## Guidelines

- Specific instruction 1
- Specific instruction 2
EOF
```

2. Use it immediately:

```bash
crux mode my-mode
```

## Mode Switching

Modes can be switched mid-session:

```
Tool: update_session
Input: { "active_mode": "security" }
```

The next prompt will use the new mode's context.

## See Also

- [All modes listed](/modes/) — Browse all 24 modes
- [Architecture](/architecture/) — How modes integrate
- [Safety Pipeline](/safety-pipeline/) — Gate activation by mode
