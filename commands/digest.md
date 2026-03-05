# Command: digest

View daily digest of activity and recommendations.

## Usage
```
opencode /digest [--yesterday|--week|--month]
```

## Contents
- Session summary (count, total time, modes used)
- Top scripts executed
- Errors and failures (with solutions)
- Knowledge suggestions (new areas for library)
- Mode suggestions (based on drift data)
- Recommended script promotions

## Output Format
Digestible summary suitable for email or messaging.

## Examples
```
opencode /digest              # Today's digest
opencode /digest --week       # Weekly summary
opencode /digest --yesterday  # Specific day
```
