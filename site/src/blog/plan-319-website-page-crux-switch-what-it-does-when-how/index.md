---
layout: post.njk
title: "Website page: crux switch - what it does, when/how to use, tool transitions, what it cannot do, vs crux adopt"
date: 2026-03-08
tags: [ship, plan-319]
summary: "Website page: crux switch - what it does, when/how to use, tool transitions, what it cannot do, vs c"
---

# Website page: crux switch - what it does, when/how to use, tool transitions, what it cannot do, vs crux adopt

Clone a new repo. Open your AI coding tool. It asks you what the project does. You spend the next 20 minutes explaining the architecture, the tech stack, the conventions. Then you do it again in the next tool. This is not what AI assistance was supposed to feel like.

## The problem
AI coding tools are powerful, but they start with zero context about your project. Every new codebase means a cold start: explaining the basics, pointing out important files, describing patterns you follow.

This onboarding tax scales with the number of projects you work on. Consultants, open source contributors, and developers who context-switch frequently pay it constantly. It's friction that should be eliminated.

Some tools try to solve this with automatic indexing, but they miss the nuance. They see the code structure but don't understand the decisions behind it. Why did you choose this pattern? What are the gotchas? That knowledge lives in your head or scattered across docs and conversations.

## Our approach
We built `crux adopt` to automate project onboarding. Point it at a repo and it generates context for all your AI tools in one command.

The key insight was that much of the important context is already in the repo—you just need to extract it. README files, configuration files, directory structure, test patterns, and code comments all contain valuable signal.

We augment this with heuristics learned from analyzing thousands of projects. A Next.js app with Prisma follows different patterns than a FastAPI service with SQLAlchemy. Crux recognizes these patterns and generates appropriate context.

## How it works
Project adoption runs through several analyzers:

**Stack Detection.** We scan for package files (package.json, requirements.txt, Cargo.toml, go.mod) and configuration files (.eslintrc, pyproject.toml, tsconfig.json). Each detected technology adds relevant context about best practices and common patterns.

**Architecture Inference.** Directory structure reveals architecture. A `/src/components` directory suggests React components. `/internal` and `/pkg` suggest Go project layout. We generate a high-level architecture description based on these patterns.

```python
def infer_architecture(repo_path):
    patterns = {
        'src/components': 'React component architecture',
        'internal/': 'Go internal packages (not exported)',
        'lib/': 'Shared library code',
        'tests/': 'Test suite with separate test files',
    }
    return [desc for path, desc in patterns.items() if exists(path)]
```

**Convention Extraction.** Linter configs, formatter configs, and existing CLAUDE.md/.cursorrules files are parsed to extract coding conventions. If you have an ESLint rule requiring single quotes, that becomes part of the generated context.

**Documentation Mining.** README, CONTRIBUTING, and inline documentation are summarized to capture project-specific knowledge that wouldn't be obvious from code alone.

**Multi-Tool Output.** Finally, all this context is formatted for each AI tool you use. CLAUDE.md for Claude Code, .cursorrules for Cursor, and so on.

## What this enables
With `crux adopt`, new projects go from cold start to productive in seconds. Clone a repo, run one command, and your AI tools are ready to help.

This is especially powerful for open source contribution. Fork a repo, adopt it, and your AI already understands the project's conventions and architecture. You can focus on understanding the specific change you want to make.

## Try it
In any project directory:

```bash
crux adopt
```

This scans the project and generates context for all configured AI tools. Preview what would be generated with `--dry-run`.

Documentation: [runcrux.io/docs/adopt](https://runcrux.io/docs/adopt)

---

*Part of the Crux build-in-public journey. Follow along: [@splntrb](https://x.com/splntrb)*
