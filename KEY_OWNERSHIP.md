# Crux Development Ownership

**Owner:** Key (Keystone) - Chief Enterprise Architect
**Effective:** March 2026 (PLAN-214)
**Reporting:** Stream (CEO) for coordination; splntrb for vision alignment

---

## Ownership Scope

Key is the primary developer and maintainer of the Crux ecosystem:

### Core Crux OS
- **25 modes** - Build, test, plan, security, design, analytics, etc.
- **38+ MCP tools** - Full tooling infrastructure
- **Safety pipeline** - Security audits, corrections, gates
- **Continuous learning** - Knowledge base, cross-domain integration
- **Adapters** - Tool and service integrations

### Products Built on Crux
| Product | Description | Status |
|---------|-------------|--------|
| **Crux** | Full AI operating system | Active |
| **CruxCLI** | Hard fork of OpenCode with Crux integration | v0.1 |
| **Crux Vibe** | Mac Mini hosting platform | Planned |

---

## Development Responsibilities

### Daily
- Review any incoming issues/PRs
- Monitor mode effectiveness via feedback loops
- Respond to Crux-related questions from team

### Weekly
- Audit mode coverage (new domains needed?)
- Review safety pipeline effectiveness
- Update knowledge base with learnings

### Per Implementation
- Plan v3.0 process for any Crux changes
- Ping-pong validation for safety-critical changes
- Document changes in changelog

---

## Development Workflow

### Making Changes to Crux
```bash
# 1. Create plan
key-op qcp "Crux: Add X capability to Y mode"

# 2. Run v3.0 planning
key-op plan PLAN-XXX

# 3. Implement after approval
# ... implementation ...

# 4. Commit with plan reference
git commit -m "PLAN-XXX: Description"

# 5. Mark implemented
onelist-plan status PLAN-XXX implemented
```

### Adding New Mode
1. Copy `modes/TEMPLATE.txt` to `modes/new-mode.md`
2. Define scope, tools, and constraints
3. Add to mode registry
4. Test with sample prompts
5. Document in knowledge base

### Modifying Safety Pipeline
- Requires additional review (splntrb or Stream)
- Test with adversarial inputs
- Document changes thoroughly

---

## Architecture Overview

```
/home/key/.crux/
├── CLAUDE.md              # Crux context for Claude
├── KEY_OWNERSHIP.md       # This document
├── modes/                 # 25 operational modes
├── scripts/lib/           # MCP tools and handlers
├── adapters/              # External integrations
├── analytics/             # Usage analytics
├── corrections/           # Error correction pipeline
├── knowledge/             # Cross-domain knowledge
├── commands/              # CLI commands
├── bin/                   # Entry points
└── tests/                 # Test suite
```

---

## Quality Standards

### For All Changes
- [ ] Security reviewed (no new vulnerabilities)
- [ ] Type hints on all functions
- [ ] Tests cover happy path and edge cases
- [ ] Documentation updated
- [ ] Commit message references plan

### For Mode Changes
- [ ] Mode prompt follows template
- [ ] Tools specified correctly
- [ ] Scope is clear and bounded
- [ ] No overlap with existing modes

### For Safety Changes
- [ ] Adversarial testing completed
- [ ] Correction pipeline updated if needed
- [ ] Gate logic verified
- [ ] Human approval documented

---

## Escalation Path

| Issue Type | Escalate To |
|------------|-------------|
| Security vulnerability | splntrb immediately |
| Mode conflict | Stream for coordination |
| Architecture decision | Document + propose to splntrb |
| Resource needs | Stream (CEO budget authority) |

---

## Related Documents

- `/home/key/.crux/CLAUDE.md` - Crux context for Claude
- `/home/key/.crux/CONTRIBUTING.md` - Contribution guidelines
- `/home/key/repos/claude_code_swarm/CLAUDE.md` - Key's operational context
- `/home/key/repos/CruxCLI/ROADMAP.md` - CruxCLI plans

---

*PLAN-214: Key Takes Over Crux Development*
*Effective: March 2026*
