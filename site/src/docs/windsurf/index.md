---
layout: base.njk
title: "Crux + Windsurf"
description: "Crux integration with Windsurf via MCP"
---

# Crux + Windsurf

## Setup

After running `~/.crux/setup.sh`:

1. Configure Windsurf to connect to the Crux MCP server
2. Restart Windsurf to load the connection

## MCP Integration

Windsurf connects to Crux via MCP protocol. All 37 Crux tools are available.

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

Configure your Windsurf MCP settings to point to:

```
Command: ~/.crux/.venv/bin/python
Args: -m scripts.lib.crux_mcp_server
Env: CRUX_PROJECT=., CRUX_HOME=~, PYTHONPATH=~/.crux
```

## Tool Switching

```bash
# Switch to Windsurf from another tool
crux switch Windsurf

# Switch away from Windsurf
crux switch claude-code
```

## See Also

- [Tool Switching](/switching/) — How switching works
- [MCP Server](/docs/mcp-server/) — All 37 tools
- [Modes](/modes/) — Available modes
