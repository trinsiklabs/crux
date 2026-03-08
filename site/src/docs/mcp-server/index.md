---
layout: base.njk
title: MCP Server Reference
description: All 37 Crux MCP tools documented
---

# MCP Server Reference

The Crux MCP server exposes 37 tools that any MCP-compatible AI assistant can call.

## Knowledge Tools

| Tool | Description |
|------|-------------|
| `lookup_knowledge` | Search knowledge entries by keyword |
| `promote_knowledge` | Save a learning as a knowledge entry |
| `get_project_context` | Get auto-generated project context |

## Session Tools

| Tool | Description |
|------|-------------|
| `get_session_state` | Get current session (mode, working_on, pending) |
| `update_session` | Update session state |
| `write_handoff` | Write detailed handoff for tool switch |
| `read_handoff` | Read handoff from previous session |
| `restore_context` | Full context restore for new session |

## Mode Tools

| Tool | Description |
|------|-------------|
| `get_mode_prompt` | Get the prompt for a specific mode |
| `list_modes` | List all available modes |

## Safety Tools

| Tool | Description |
|------|-------------|
| `validate_script` | Run script through safety validation |
| `get_pipeline_config` | Get safety pipeline configuration |
| `get_active_gates` | Get active gates for mode/risk level |
| `start_tdd_gate` | Initialize TDD tracking |
| `check_tdd_status` | Check if TDD requirements met |
| `start_security_audit` | Begin security audit |
| `security_audit_summary` | Get security audit results |
| `start_design_validation` | Begin design validation |
| `design_validation_summary` | Get design validation results |
| `check_contrast` | Check color contrast for accessibility |
| `audit_script_8b` | Run script through 8B model audit |
| `audit_script_32b` | Run script through 32B model audit |

## Correction Tools

| Tool | Description |
|------|-------------|
| `log_correction` | Record a correction |
| `log_interaction` | Log a tool interaction |

## Switching Tools

| Tool | Description |
|------|-------------|
| `switch_tool` | Switch to another AI coding tool |

## Processor Tools

| Tool | Description |
|------|-------------|
| `check_processor_thresholds` | Check if background processors should run |
| `run_background_processors` | Run background processors |
| `get_processor_status` | Get processor status |

## Cross-Project Tools

| Tool | Description |
|------|-------------|
| `register_project` | Register project for cross-project features |
| `get_cross_project_digest` | Get digest across all registered projects |
| `get_digest` | Get digest for current project |

## Build-in-Public Tools

| Tool | Description |
|------|-------------|
| `bip_generate` | Check triggers and gather content for BIP draft |
| `bip_approve` | Approve draft and queue to Typefully |
| `bip_status` | Get BIP counters and state |

## Figma Tools

| Tool | Description |
|------|-------------|
| `figma_get_tokens` | Extract design tokens from Figma file |
| `figma_get_components` | Extract components from Figma file |

## Health Tools

| Tool | Description |
|------|-------------|
| `verify_health` | Verify Crux installation health |

## Usage

Any MCP-compatible tool can call these:

```
Tool: lookup_knowledge
Input: { "query": "authentication patterns" }
Output: { "entries": [...], "count": 3 }
```

## Server Configuration

```json
{
  "mcpServers": {
    "crux": {
      "command": "~/.crux/.venv/bin/python",
      "args": ["-m", "scripts.lib.crux_mcp_server"],
      "env": {
        "CRUX_PROJECT": ".",
        "CRUX_HOME": "~",
        "PYTHONPATH": "~/.crux"
      }
    }
  }
}
```
