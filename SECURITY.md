# Security Policy

## Reporting Vulnerabilities

Report security issues to: security@trinsiklabs.com

Do NOT open public GitHub issues for security vulnerabilities.

## Security Model

### MCP Server

- Path validation on all file operations (no traversal)
- Environment variable sanitization — `CRUX_HOME`, `CRUX_PROJECT`, `PYTHONPATH` never forwarded to external MCP servers
- API keys stored in gitignored files only (`.crux/bip/typefully.key`, `.crux/marketing/typefully.key`)
- Session state contains no secrets — only metadata (mode, working_on, decisions, files)

### Hook System

- Hooks execute as shell commands configured in `.claude/settings.local.json`
- Hook inputs are length-limited and sanitized
- Correction detection uses regex patterns — no arbitrary code execution
- Conversation logging sanitizes prompts before writing to JSONL

### Safety Pipeline (7 Gates)

1. **Preflight** — Static validation (shebang, risk header, banned patterns, path containment)
2. **TDD** — Test-first enforcement
3. **Security Audit** — Recursive CWE/OWASP pattern scanning (injection, path traversal, hardcoded secrets, SQL injection, insecure HTTP, debug enabled, weak crypto)
4. **8B Adversarial** — Small model reviews code for vulnerabilities
5. **32B Second Opinion** — Large model re-reviews high-risk scripts
6. **Human Approval** — Manual review required
7. **DRY_RUN** — Execute without side effects

### Binary Distribution

- Single Rust binary, no runtime dependencies
- No network access by default — Ollama/Typefully/Figma connections are opt-in
- No telemetry, no analytics collection, no phone-home

## Known Limitations

- Ollama audit backends (Gates 4-5) require a running local LLM — if Ollama is not available, these gates pass by default
- Session recovery parses untrusted `.jsonl` files — malformed entries are skipped but not validated for injection
- The `.crux/` directory is not encrypted — it contains session context that could include code snippets from conversations

## Dependency Audit

| Crate | Purpose | Risk |
|-------|---------|------|
| rmcp | MCP protocol | Low — maintained by MCP org |
| tokio | Async runtime | Low — widely used |
| reqwest | HTTP client | Low — only for opt-in API calls |
| tree-sitter | AST parsing | Low — compiled C grammars |
| serde/serde_json | Serialization | Low — standard |
| regex | Pattern matching | Low — no ReDoS patterns used |
