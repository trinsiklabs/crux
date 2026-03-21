# /crux-mode — Switch Crux modes

Switch the active Crux mode. Modes change the system prompt, temperature, and behavior.

## Arguments

$ARGUMENTS = mode name (e.g., "build-py", "review", "debug", "plan", "explain")

If no argument, list all available modes.

## Protocol

If $ARGUMENTS is empty:
- Call `list_modes()` to show all available modes
- Display each mode with a short description

If $ARGUMENTS has a mode name:
- Call `switch_mode($ARGUMENTS)` (or `update_session(active_mode=$ARGUMENTS)`)
- Confirm the switch
- Show what changed (temperature, prompt focus)

## Common modes

| Mode | Purpose |
|------|---------|
| build-py | Python development (default) |
| build-ex | Elixir development |
| review | Code review focus |
| debug | Debugging and troubleshooting |
| plan | Planning and architecture |
| explain | Teaching and explanation |
| strategist | High-level strategy |
