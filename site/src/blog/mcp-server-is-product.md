---
title: "the MCP server is the product"
date: 2026-03-05T12:00:00
tags: [architecture, mcp, philosophy]
summary: "all logic in one place, every tool connects via standard protocol. adding a new tool = one config line."
---

one of the key architectural decisions: the MCP server IS the product.

not a plugin. not an adapter. not a sync script. one server.

**what lives in the MCP server:**
- knowledge lookup
- session state management
- correction detection
- safety validation
- mode definitions
- digest generation
- project context
- handoff generation

10 tools exposed: `crux_lookup_knowledge`, `crux_get_session_state`, `crux_update_session`, `crux_detect_correction`, `crux_validate_script`, `crux_get_mode_prompt`, `crux_get_digest`, `crux_write_handoff`, `crux_promote_knowledge`, `crux_get_project_context`.

**how tools connect:**

tools with hook support (claude code, opencode):
- paper-thin shims (5-10 lines, zero logic)
- forward events to MCP server for correction detection and safety interception
- the shims don't DO anything — they just relay

tools without hooks (cursor, cline, roo code, aider):
- connect via MCP alone
- get knowledge, session state, modes, safety validation
- ~60% of crux's value available through MCP alone

**adding support for a new AI tool:**
```
# one line in the tool's MCP config
{"mcpServers": {"crux": {"command": "npx", "args": ["-y", "@trinsiklabs/crux-mcp"]}}}
```

not a full adapter. not a sync script. one config line.

this is what makes crux different: you're not competing with any AI tool. you're enhancing all of them. every tool community is your community.

your tools are disposable. your intelligence isn't.
