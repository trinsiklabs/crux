# Command: log

View and manage session logs.

## Usage
```
opencode /log [options]
```

## Options
- `--today` - Show today's sessions
- `--week` - Show this week's sessions
- `--search <query>` - Search logs for pattern
- `--export <format>` - Export to JSON/CSV
- `--clear-old` - Remove logs older than 90 days

## Format
Logs are stored as JSONL in `.opencode/sessions/`

Each line contains:
- timestamp
- mode
- command
- result (success/failure)
- duration
- context (project, branch, etc.)

## Examples
```
opencode /log --today
opencode /log --search "build-py"
opencode /log --export json
```
