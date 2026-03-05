# Command: promote

Promote a script from active use to the library.

When a script has proven itself reliable and useful across multiple sessions, promote it to make it available system-wide.

## Usage
```
opencode /promote <script-path>
```

## What Happens
1. Validates script follows template requirements
2. Moves script to `.opencode/scripts/library/<category>/`
3. Updates header with promotion timestamp
4. Creates git commit documenting promotion
5. Makes available to other projects via `lookup_knowledge`

## Requirements
- Script must be 30+ days old
- Script must have 5+ successful executions
- Header must follow template format
- No uncommitted changes in git
