# Contributing to Crux

Crux gets better when people share what they've learned. The most valuable contributions aren't theoretical — they're artifacts that have been battle-tested in real projects and proven their value through Crux's own measurement systems.

## What We Accept

### Knowledge Entries

Domain-specific reference material that helps modes perform better. Examples: framework conventions (Ash resource patterns, Django REST best practices), common error resolutions (solutions to bugs you've solved that the model keeps getting wrong), security checklists, API patterns.

**Requirements:**

- Must be scoped to a specific mode (placed in `knowledge/<mode-name>/`)
- Must include a provenance header: what problem it addresses, how it was validated, how many projects it's been tested in
- Must be concise (under 500 words — knowledge entries that are too long burn context without proportional benefit)
- Must use positive framing (what to do, not what to avoid)

### Mode Refinements

Improvements to existing mode prompts, backed by data. Don't submit "I think this wording is better." Submit "this revision reduced correction rate from 0.25 to 0.12 across 3 projects over 2 weeks."

**Requirements:**

- Must include before/after prompt text
- Must include correction rate data or other measurable evidence
- Must follow mode template rules: positive instructions, simple task-relevant persona, critical rules at beginning and end, 150-200 word length
- Must pass the automated mode audit (run `scripts/lib/audit-mode.sh <mode-file>`)

### New Mode Proposals

Entirely new modes for domains not currently covered.

**Requirements:**

- Must include evidence of need: what work pattern triggered this? What existing mode was being used incorrectly?
- Must follow the mode template
- Must include at least 3 example interactions showing the mode performing well
- Must include a seeded knowledge directory with at least 2 baseline knowledge entries

### Scripts

Reusable scripts for common workflows.

**Requirements:**

- Must follow the Crux script template (header with name, risk classification, description; `set -euo pipefail`; DRY_RUN support for medium+ risk)
- Must not contain hardcoded paths, project-specific references, or credentials
- Must include a brief description of what problem the script solves and in what context it was originally created
- Must pass `bash -n` syntax check and shellcheck

### Custom Tools

JavaScript/TypeScript tools for the tool hierarchy.

**Requirements:**

- Must use Zod schemas for parameter validation
- Must include a clear description (the model reads this to decide when to use the tool)
- Must handle errors gracefully (tools should never crash the session)
- Must be idempotent where possible
- Must include at least one example invocation

### MCP Servers

Protocol-compliant servers for external system integration.

**Requirements:**

- Must implement the MCP protocol correctly
- Must include setup instructions (dependencies, configuration)
- Must include security documentation (what access is required, what data flows where)
- Must handle authentication gracefully

### Documentation

Guides, tutorials, examples, and improvements to existing docs.

**Requirements:**

- Must be accurate (test all code examples before submitting)
- Must follow existing documentation style
- Must not duplicate content that already exists elsewhere in the docs

## How to Submit

1. Fork the repository
2. Create a feature branch (`git checkout -b contribute/knowledge-ash-migrations`)
3. Add your contribution following the requirements above
4. Run the validation script: `./scripts/lib/validate-contribution.sh`
5. Commit with a descriptive message explaining what you're contributing and why
6. Open a pull request using the appropriate template

## Quality Standards

Every contribution is checked against these automated standards before human review:

- **No hardcoded paths** — contributions must work in any project directory
- **No credentials or secrets** — even example ones can leak into real usage
- **Template compliance** — scripts have headers, modes follow the template, knowledge entries have provenance
- **Positive framing** — mode prompts and knowledge entries use "do X" not "don't do Y"
- **Size constraints** — mode prompts: 150-200 words; knowledge entries: under 500 words; scripts: under 200 lines (split larger scripts into transaction scripts)
- **Shellcheck clean** — all bash scripts pass shellcheck with no warnings

## Review Process

1. **Automated checks** run on PR submission (template compliance, shellcheck, size constraints, path scanning)
2. **Maintainer review** within 7 days — focused on relevance, quality, and whether the contribution fills a real gap
3. **Community feedback period** — 3 days minimum for non-trivial contributions
4. **Merge** — contributions that pass automated checks and maintainer review are merged and included in the next release

## What Makes a Great Contribution

The best contributions share these qualities:

- **Born from real usage** — they were created by Crux's own continuous learning pipeline and promoted through the three-tier scope system (project → user → public)
- **Backed by data** — they include provenance showing what problem they solved and how they performed
- **Self-contained** — they work independently without requiring other uncommitted changes
- **Well-scoped** — they do one thing well rather than trying to cover an entire domain

## Code of Conduct

Be constructive. Review others' contributions the way you'd want yours reviewed — with specificity, kindness, and a focus on making the work better rather than proving it wrong. The adversarial auditing is for scripts, not for people.

## Questions?

Open a discussion on the GitHub Discussions tab. For bugs, use the issue templates.
