# Crux Architecture
.crux/ is the single source of truth. Two scopes:
- Project: .crux/ (knowledge, corrections, sessions, scripts, context)
- User: ~/.crux/ (cross-project knowledge, modes, analytics, templates)

All path resolution through crux_paths.py. No hardcoded tool paths.
MCP server exposes all logic. Tools connect via MCP protocol.
Tags: architecture, crux, design