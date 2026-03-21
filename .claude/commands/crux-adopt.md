# /crux-adopt — Adopt a project into the Crux ecosystem

Install Crux (intelligence layer) into a project. Sets up modes, MCP tools, session state, and safety gates.

## Arguments

$ARGUMENTS = project directory and optional mode (e.g., "/path/to/project build-py" or just "." for current dir)

## Protocol

### Step 1: Parse arguments

Split $ARGUMENTS into project_dir (first word) and mode (second word, default "build-py").

### Step 2: Run adoption

```python
import os, sys
sys.path.insert(0, "/Users/user/personal/crux")
from scripts.lib.crux_adopt import adopt_project

result = adopt_project(
    project_dir=project_dir,
    home=os.environ["HOME"],
    active_mode=mode,
    active_tool="claude-code",
    working_on="Project adoption",
)
for item in result.items_setup:
    print(f"  ✓ {item}")
```

### Step 3: Verify

```bash
/Users/user/personal/crux/bin/crux status
ls .crux/
cat .claude/mcp.json
```

### Step 4: Report

Tell the user:
- What was set up (.crux/, .claude/mcp.json, settings.local.json)
- Active mode
- Available MCP tools (call `list_modes()` to show modes)
- How to switch modes: call `switch_mode(mode_name)`
- Restart Claude Code to activate MCP tools
