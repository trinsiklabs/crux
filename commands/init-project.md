# Command: init-project

Initialize a new project with Crux structure.

## Usage
```
opencode /init-project <project-name> [--template <type>]
```

## What Gets Created
- `.opencode/` directory structure
- `PROJECT.md` with project metadata
- `.opencode/scripts/local/` for project-specific scripts
- `.opencode/knowledge/` with project-specific knowledge
- `.gitignore` configuration
- Initial git commit

## Templates
- `python` - Python project with venv setup
- `elixir` - Elixir/Phoenix project
- `fullstack` - Python backend + frontend
- `ml` - Machine learning project structure
- `minimal` - Bare-bones structure

## PROJECT.md Contents
- Project name and description
- Technology stack
- Key team members and their roles
- Architecture overview
- Current status and next milestones
- Deployment procedures
- Known technical debt

## Examples
```
opencode /init-project myapp --template python
cd myapp && opencode
```
