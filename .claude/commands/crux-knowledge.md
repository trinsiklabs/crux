# /crux-knowledge — Look up or add Crux knowledge

Search and manage Crux knowledge entries — patterns, decisions, and context that persist across sessions.

## Arguments

$ARGUMENTS = search query, or "add <name> <content>" to add new knowledge

## Protocol

### Search (default)

Call `lookup_knowledge(query=$ARGUMENTS)` to search knowledge entries.

Display results with their source (project, user, mode) and content preview.

### Add new knowledge

If $ARGUMENTS starts with "add":
- Parse: `add <name> <content>`
- Call `promote_knowledge(name=<name>, content=<content>, scope="project")`
- Confirm what was saved

### Examples

```
/crux-knowledge auth patterns      → search for auth-related knowledge
/crux-knowledge add api-style "REST with JSON:API envelope, snake_case fields"
/crux-knowledge testing            → search for testing knowledge
```
