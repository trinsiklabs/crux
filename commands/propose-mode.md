# Command: propose-mode

Propose new mode based on usage drift.

## Usage
```
opencode /propose-mode
```

## Mechanism
Analyzes recent sessions to identify:
- Commands that don't fit existing modes
- Frequent mode-switching patterns
- Emerging task categories
- Modes that are frequently combined

## Proposal Includes
- Mode name and purpose
- Recommended core rules
- Scope and applicable tasks
- Relationship to existing modes

## Review Process
1. System proposes mode
2. User reviews and provides feedback
3. Draft mode created
4. Used experimentally for 10 sessions
5. Feedback incorporated
6. Promoted to permanent or archived
