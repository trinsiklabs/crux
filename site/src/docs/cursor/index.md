---
layout: base.njk
title: "Crux + Cursor"
description: "Crux integration with Cursor via MCP"
---

# Crux + Cursor

## Setup

After running `~/.crux/setup.sh`:

1. Configure Cursor to connect to the Crux MCP server
2. Restart Cursor to load the connection

## MCP Integration

Cursor connects to Crux via MCP protocol. All 37 Crux tools are available.

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

Configure your Cursor MCP settings to point to:

```
Command: ~/.crux/.venv/bin/python
Args: -m scripts.lib.crux_mcp_server
Env: CRUX_PROJECT=., CRUX_HOME=~, PYTHONPATH=~/.crux
```

## Tool Switching

```bash
# Switch to Cursor from another tool
crux switch Cursor

# Switch away from Cursor
crux switch claude-code
```

## See Also

- [Tool Switching](/switching/) — How switching works
- [MCP Server](/docs/mcp-server/) — All 37 tools
- [Modes](/modes/) — Available modes
