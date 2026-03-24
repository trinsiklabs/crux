---
title: Crux MCP API Reference
last_updated: 2026-03-24
source: Generated from scripts/lib/crux_mcp_server.py (43 tools)
migration_date: 2026-03-24
migration_status: normalized
---

# Crux MCP API Reference

The Crux MCP Server exposes 43 tools via the Model Context Protocol (MCP) over stdio transport. Any MCP-compatible tool can connect by adding the server to its MCP config.

## Connection

```json
{
  "mcpServers": {
    "crux": {
      "type": "stdio",
      "command": "<path-to-venv>/python",
      "args": ["-m", "scripts.lib.crux_mcp_server"],
      "env": {
        "CRUX_PROJECT": "<project-dir>",
        "CRUX_HOME": "<home-dir>",
        "PYTHONPATH": "<crux-repo-dir>"
      }
    }
  }
}
```

## Tools by Category

### Knowledge & Learning

| Tool | Description |
|------|-------------|
| `lookup_knowledge` | Search knowledge entries across project and user scopes |
| `promote_knowledge` | Promote a knowledge entry from project scope to user scope |
| `log_correction` | Log a correction for continuous learning |
| `log_interaction` | Log a conversation message for continuous learning analysis |

### Session Management

| Tool | Description |
|------|-------------|
| `get_session_state` | Get the current Crux session state (active mode, tool, working context) |
| `update_session` | Update the current session state |
| `restore_context` | Restore full session context after a restart or tool switch |
| `write_handoff` | Write handoff context for the next mode or tool switch |
| `read_handoff` | Read handoff context left by a previous mode or tool |
| `switch_tool_to` | Switch to a different AI coding tool, syncing all configs |

### Modes

| Tool | Description |
|------|-------------|
| `get_mode_prompt` | Get the full prompt text for a specific mode |
| `list_modes` | List all available Crux modes with descriptions |

### Safety Pipeline

| Tool | Description |
|------|-------------|
| `validate_script` | Validate a script against Crux safety conventions |
| `get_pipeline_config` | Get the current pipeline configuration (gates, TDD level, security settings) |
| `get_active_gates` | Get active safety gates for a mode at a given risk level |
| `start_tdd_gate` | Start the TDD enforcement gate for a feature build |
| `check_tdd_status` | Check the current status of the TDD enforcement gate |
| `start_security_audit` | Start a recursive security audit loop |
| `security_audit_summary` | Get a summary of the security audit |
| `audit_script_8b` | Gate 4: Run an adversarial security audit using a small (8B) model |
| `audit_script_32b` | Gate 5: Run a second-opinion security audit using a large (32B) model |

### Design Validation

| Tool | Description |
|------|-------------|
| `start_design_validation` | Start the design validation gate (WCAG, brand, handoff checks) |
| `design_validation_summary` | Get a summary of design validation results |
| `check_contrast` | Check contrast ratio between two hex colors for WCAG compliance |

### Figma Integration

| Tool | Description |
|------|-------------|
| `figma_get_tokens` | Extract design tokens (colors, typography, spacing) from a Figma file |
| `figma_get_components` | Get the component library from a Figma file |

### Analytics & Diagnostics

| Tool | Description |
|------|-------------|
| `get_digest` | Retrieve a daily digest |
| `get_project_context` | Read the PROJECT.md context file for the current project |
| `verify_health` | Run all health checks (static + liveness) and return a combined report |
| `check_processor_thresholds` | Check which background processing thresholds are exceeded |
| `run_background_processors` | Run all due background processors |
| `get_processor_status` | Get when each background processor last ran |
| `register_project` | Register the current project for cross-project aggregation |
| `get_cross_project_digest` | Generate a digest spanning all registered projects |

### Build-in-Public (BIP)

| Tool | Description |
|------|-------------|
| `bip_generate` | Check triggers and gather content for a build-in-public draft |
| `bip_approve` | Approve a BIP draft — save it and queue to Typefully |
| `bip_status` | Get current build-in-public state — counters, cooldown, recent posts |
| `bip_get_analytics` | Get BIP engagement analytics — Typefully stats, GitHub stars/forks |

### Model Routing

| Tool | Description |
|------|-------------|
| `get_model_for_task` | Get the recommended model for a task type |
| `get_available_tiers` | Show what model is available at each tier |
| `get_mode_model` | Get the recommended model for a Crux mode |
| `get_model_quality_stats` | Get model quality statistics — success rates per task type and tier |

### Impact Analysis

| Tool | Description |
|------|-------------|
| `analyze_impact` | Rank files by relevance to a prompt using git history, keywords, and LSP |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CRUX_PROJECT` | No | Project directory (defaults to cwd) |
| `CRUX_HOME` | No | User home (defaults to `$HOME`) |
| `PYTHONPATH` | Yes | Must include crux repo root |

## Server Info

- **Name:** crux
- **Transport:** stdio
- **Protocol:** MCP 2024-11-05
- **Implementation:** FastMCP (Python)
