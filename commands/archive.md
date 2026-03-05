# Command: archive

Auto-archive scripts based on age and usage.

## Usage
```
opencode /archive [--check|--execute]
```

## Behavior
- `--check` (default): Show candidates for archival
- `--execute`: Move scripts to archive/YYYY-MM/ directory

## Criteria for Archival
- Not executed in 90 days
- Marked as deprecated
- Superseded by newer version
- 10+ versions accumulated

## Archive Location
`.opencode/scripts/archive/YYYY-MM/script-name.sh`

Archived scripts remain searchable but aren't executed by default.
