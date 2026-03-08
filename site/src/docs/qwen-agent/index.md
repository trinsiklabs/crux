---
layout: base.njk
title: "Crux + Qwen-Agent"
description: "Crux integration with Qwen-Agent via MCP"
---

# Crux + Qwen-Agent

## Setup

After running `~/.crux/setup.sh`:

1. Configure Qwen-Agent to connect to the Crux MCP server
2. Restart Qwen-Agent to load the connection

## MCP Integration

Qwen-Agent connects to Crux via MCP protocol. All 37 Crux tools are available.

## Supported Features

| Feature | Support |
|---------|---------|
| MCP Tools | Full |
| Knowledge lookup | Yes |
| Session state | Yes |
| Modes | Yes |
| Corrections | Yes |
| Safety pipeline | Yes |

## Configuration

Configure your Qwen-Agent MCP settings to point to:

```
Command: ~/.crux/.venv/bin/python
Args: -m scripts.lib.crux_mcp_server
Env: CRUX_PROJECT=., CRUX_HOME=~, PYTHONPATH=~/.crux
```

## Tool Switching

```bash
# Switch to Qwen-Agent from another tool
crux switch Qwen-Agent

# Switch away from Qwen-Agent
crux switch claude-code
```

## See Also

- [Tool Switching](/switching/) — How switching works
- [MCP Server](/docs/mcp-server/) — All 37 tools
- [Modes](/modes/) — Available modes
