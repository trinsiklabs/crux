---
title: Website Configuration — runcrux.io
last_updated: 2026-03-27
---

# Website Configuration

## Stack

- **Generator:** Eleventy (11ty) 2.x
- **Templates:** Nunjucks (.njk)
- **CSS:** Hand-written, dark/light mode, monospace headings, system font body
- **Hosting:** runcrux.io via rsync to vh1.trinsik.io
- **Domain:** runcrux.io

## Directory Structure

```
site/
├── .eleventy.js          # 11ty configuration
├── package.json          # Dependencies (11ty only)
├── src/
│   ├── _data/site.json   # Site metadata
│   ├── _includes/
│   │   ├── base.njk      # Base HTML layout (nav, header, footer)
│   │   └── post.njk      # Blog post layout (tweet cross-reference)
│   ├── css/style.css     # All styles (334 lines)
│   ├── feed.njk          # Atom RSS feed
│   ├── index.njk         # Landing page
│   ├── 404.md            # Custom 404
│   ├── about/            # Founder story
│   ├── adopt/            # crux adopt guide
│   ├── architecture/     # Architecture diagram
│   ├── blog/             # Build-in-public blog (19 posts)
│   ├── changelog/        # Release history
│   ├── docs/             # Tool-specific docs (7 tools + MCP + modes)
│   ├── modes/            # 24 modes showcase
│   ├── safety-pipeline/  # 7-gate pipeline explained
│   └── switching/        # Tool switching guide
└── _site/                # Build output (gitignored)
```

## Build & Deploy

```bash
# Build
cd site && npm install && npm run build

# Deploy
./deploy-runcrux.io.sh --build --force

# Deploy with dry-run
./deploy-runcrux.io.sh --build --dry-run
```

## Deploy Script

`deploy-runcrux.io.sh` — rsync-based deployment:
- `--build` — run `npm install && npm run build` first
- `--dry-run` — show what would transfer without doing it
- `--force` — skip confirmation prompt
- `--verbose` — show transfer progress

Target: `runcrux.io@runcrux.io:/home/runcrux.io/public_html/`

## Design Principles

Per marketing plan:
- All lowercase copy (matching voice), proper nouns capitalized
- Monospace headings, system font body
- Dark mode default, light mode via prefers-color-scheme
- No tracking, no cookies, no JavaScript
- Target < 50ms TTFB, < 100KB page weight
- No Tailwind, no framework — hand-written CSS

## Pages (41 total)

- Landing page
- About (founder story)
- Architecture
- Safety Pipeline
- Tool Switching
- crux adopt
- Modes showcase (24 modes)
- Changelog
- 404
- Blog index + 19 posts
- Docs: Getting Started, Claude Code, OpenCode, Cursor, Windsurf, Aider, Roo Code, Qwen-Agent, MCP Server, Modes System
- RSS feed
