# /crux-session — Manage Crux session state

View or update the current Crux session (working_on, key decisions, pending items).

## Arguments

$ARGUMENTS = "status" (default), or "update <field> <value>"

## Protocol

### Status (default)

Call `get_session_state()` to show current session:
- Active mode
- What you're working on
- Key decisions made
- Pending items
- Context summary

### Update

Parse $ARGUMENTS for updates:
- `update working_on <description>` → Call `update_session(working_on=<description>)`
- `update pending add <item>` → Call `update_session(pending_add=<item>)`
- `update decision <decision>` → Call `update_session(key_decisions_add=<decision>)`

### Handoff

If $ARGUMENTS is "handoff":
- Call `write_handoff()` to save full session context for the next session
- Confirm what was saved

### Restore

If $ARGUMENTS is "restore":
- Call `restore_context()` to load context from previous session
- Show what was restored
