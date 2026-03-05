# Session & Tool Switching
SessionState persisted in .crux/sessions/state.json.
switch_tool() syncs configs for target tool and updates active_tool.
Handoff context in .crux/sessions/handoff.md bridges mode/tool switches.
sync_claude_code() generates .claude/agents/ with YAML frontmatter.
sync_opencode() symlinks modes + knowledge to ~/.config/opencode/.
Tags: session, switching, tools