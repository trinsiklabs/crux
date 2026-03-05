# Command: scripts

List all available scripts with descriptions and risk levels.

## Usage
```
opencode /scripts [filter]
```

## Output Format
Shows:
- Script name
- Risk level (low/medium/high)
- Description
- Last execution date
- Location (active/library/archive)

## Filters
- `active` - Scripts in current session
- `library` - Promoted library scripts
- `archive` - Archived scripts
- `<risk>` - Filter by risk level (low/medium/high)

## Examples
```
opencode /scripts              # List all
opencode /scripts library      # List library scripts
opencode /scripts high         # List high-risk scripts
```
