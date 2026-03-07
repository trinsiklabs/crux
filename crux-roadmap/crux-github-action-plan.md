# crux as a github action: the complete plan

## the opportunity

GitHub has 150M+ users running 5M+ workflows daily. GitHub Actions is already how developers do CI/CD — linting, testing, security scanning, code review. every team already has a `.github/workflows/` directory.

Crux's safety pipeline, recursive security audit, TDD enforcement, and mode-routed review are exactly what runs in CI. the only question is packaging.

```yaml
# this is the entire adoption friction
- uses: trinsiklabs/crux-review@v1
  with:
    crux-token: ${{ secrets.CRUX_TOKEN }}
```

one line. no new tool to learn. no IDE plugin. no CLI to install. just a YAML file in a repo the developer already owns.

**the competitive landscape:**
- CodeRabbit: 2M+ repos, 13M+ PRs reviewed, $24/seat/month. AI code review but no safety pipeline, no TDD enforcement, no security audit loop.
- GitHub Copilot code review: native but can't block merges, no recursive security auditing, no corrections system.
- SonarCloud: static analysis across 30+ languages, SARIF reporting, but no AI reasoning, no learning.
- Snyk/Semgrep: security-focused but single-pass, no recursive audit, no corrections.

**what none of them have:**
1. recursive security audit that re-audits its own fixes until convergence
2. a corrections system that learns from every repo and gets smarter
3. mode-routed review that applies different expertise to different file types
4. TDD enforcement that verifies tests exist before code ships
5. a public knowledge tier that compounds across every installation

this is Crux's blue ocean in CI/CD.

---

## part 1: the product — what `crux-review` does on every PR

### 1.1 the five review passes

when a PR triggers `crux-review`, it runs five sequential passes on the diff:

```
PR opened/updated
    │
    ▼
┌─────────────────────────────────┐
│  PASS 1: MODE ROUTING           │
│  classify every changed file    │
│  → python? build-py reviewer    │
│  → elixir? build-ex reviewer    │
│  → terraform? infra reviewer    │
│  → UI component? design review  │
│  → test file? test reviewer     │
│  → mixed? multi-mode parallel   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  PASS 2: SECURITY AUDIT LOOP   │
│  recursive, up to 3 iterations  │
│  7 categories per iteration:    │
│  input validation, auth, data   │
│  exposure, crypto, deps, infra, │
│  business logic                 │
│  → converges when 0 crit/high   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  PASS 3: TDD ENFORCEMENT       │
│  does this PR have tests?       │
│  do tests cover new code paths? │
│  coverage delta check           │
│  → fail if below threshold      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  PASS 4: CORRECTIONS CHECK     │
│  does this PR repeat a known    │
│  mistake from this repo?        │
│  → check .crux/corrections.md   │
│  → check public knowledge tier  │
│  → flag known anti-patterns     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  PASS 5: REVIEW SYNTHESIS      │
│  combine all findings           │
│  post inline PR comments        │
│  post summary review            │
│  set check status (pass/fail)   │
│  upload SARIF to Security tab   │
└─────────────────────────────────┘
```

### 1.2 what the PR author sees

**inline comments** on specific lines:

```
🔒 SECURITY [HIGH] — SQL injection via string interpolation
  File: app/models/user.py, line 47
  Category: Input Validation (CWE-89, OWASP A03:2021)

  query = f"SELECT * FROM users WHERE email = '{email}'"

  → Use parameterized queries: cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

  This pattern was caught in 2,847 other repos using Crux. Confidence: 0.99
  Auto-fix available: yes
```

```
🧪 TEST [FAIL] — New function `calculate_tax()` has no test coverage
  File: app/services/billing.py, line 112

  This function handles financial calculations and has 4 code paths.
  TDD policy requires tests before merge.

  → Suggested test file: tests/services/test_billing.py
  → Edge cases to cover: zero amount, negative amount, tax-exempt flag, rounding
```

```
📝 CORRECTION — This repo previously fixed this exact pattern
  File: app/api/routes.py, line 23

  You're using `json.loads(request.body)` without try/except.
  On 2026-02-14, this repo fixed the same pattern in app/api/auth.py.

  → Wrap in try/except JSONDecodeError, return 400 with error message.
```

**summary review comment:**

```
## crux review summary

| category | findings | critical | high | medium | low |
|----------|----------|----------|------|--------|-----|
| security | 3 | 0 | 1 | 2 | 0 |
| tests | 2 | — | 1 fail | 1 warn | — |
| corrections | 1 | — | — | 1 | — |
| code quality | 4 | — | — | 2 | 2 |

**security audit:** converged in 2 iterations (1 high finding, auto-fix suggested)
**test coverage:** 72% → 68% (dropped 4% — new code without tests)
**corrections matched:** 1 known pattern from this repo's history

### action required
- [ ] fix SQL injection in user.py:47 (high severity, auto-fix available)
- [ ] add tests for calculate_tax() (TDD policy violation)

### suggested (non-blocking)
- [ ] add error handling for JSON parsing in routes.py:23
- [ ] consider extracting billing logic to separate module

🔗 [view full security report](link-to-sarif) · 📊 [view coverage report](link-to-coverage)
```

### 1.3 check status behavior

the action sets a GitHub check status that controls merge:

```
PASS (green ✓):
  - zero critical/high security findings
  - test coverage above threshold
  - no TDD violations (or TDD mode = relaxed)

FAIL (red ✗):
  - any critical security finding
  - any high security finding (configurable)
  - test coverage dropped below threshold
  - TDD violation in strict mode

NEUTRAL (yellow ⚠):
  - medium security findings only
  - suggestions but no blocking issues
  - TDD in standard mode with minor gaps
```

repo admins configure merge protection rules in GitHub Settings → branch rules → require `crux-review` to pass.

---

## part 2: configuration

### 2.1 the YAML file

```yaml
# .github/workflows/crux-review.yml
name: Crux Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  security-events: write  # for SARIF upload

jobs:
  crux-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # full history for blame context

      - uses: trinsiklabs/crux-review@v1
        with:
          crux-token: ${{ secrets.CRUX_TOKEN }}
```

that's the minimal config. it works out of the box with smart defaults.

### 2.2 full configuration options

```yaml
      - uses: trinsiklabs/crux-review@v1
        with:
          # authentication
          crux-token: ${{ secrets.CRUX_TOKEN }}

          # review passes (all enabled by default)
          security-audit: true
          security-audit-iterations: 3          # max recursive iterations
          security-severity-threshold: high     # fail on: critical, high, medium, low
          tdd-enforcement: standard             # strict | standard | relaxed | off
          tdd-coverage-threshold: 80            # minimum % coverage
          tdd-coverage-drop-threshold: 5        # max % drop allowed
          corrections-check: true
          code-quality: true

          # mode routing
          mode-routing: auto                    # auto | manual | off
          custom-modes: .crux/modes/            # path to custom mode definitions

          # output
          inline-comments: true
          summary-comment: true
          sarif-upload: true                    # upload to GitHub Security tab
          check-status: true                    # set pass/fail check
          auto-fix-suggestions: true            # include fix code in comments

          # knowledge
          use-public-knowledge: true            # learn from global pattern database
          contribute-to-public: true            # share anonymized patterns back

          # performance
          max-files: 50                         # skip review if PR touches >50 files
          max-diff-lines: 5000                  # skip review if diff >5000 lines
          timeout-minutes: 10                   # max runtime

          # language / framework hints (auto-detected if not specified)
          languages: python,typescript,elixir
          frameworks: phoenix,react,fastapi
```

### 2.3 the `.crux/` directory in CI

the action looks for a `.crux/` directory in the repo root. if it exists, the action uses:

- `.crux/corrections.md` — repo-specific corrections (patterns to flag)
- `.crux/knowledge/` — project-specific knowledge (architecture, conventions)
- `.crux/modes/` — custom mode definitions (if the team has defined any)
- `.crux/safety/` — safety rules (things to always block)

if `.crux/` doesn't exist, the action still works — it uses public knowledge tier patterns and default mode definitions. but repos WITH `.crux/` get dramatically better reviews because the action understands the project's specific patterns.

**this is the adoption flywheel:** install the action → get good reviews → want better reviews → add `.crux/` directory → reviews become project-aware → team can't live without it → they adopt Crux locally too.

---

## part 3: the public knowledge tier — how the action gets smarter

this is the most important architectural decision and the biggest competitive moat.

### 3.1 how it works

```
┌──────────────────────────────────────────────────────────────┐
│              THE CRUX PUBLIC KNOWLEDGE TIER                    │
│                                                                │
│  every repo that installs crux-review contributes              │
│  anonymized patterns to a shared knowledge base                │
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  repo A  │  │  repo B  │  │  repo C  │  │  repo D  │     │
│  │ python   │  │ elixir   │  │ react    │  │ go       │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │              │              │              │           │
│       └──────────────┼──────────────┼──────────────┘           │
│                      │              │                           │
│                      ▼              ▼                           │
│            ┌─────────────────────────────────┐                 │
│            │     PATTERN AGGREGATION          │                 │
│            │                                  │                 │
│            │  "SQL injection via f-string"    │                 │
│            │   seen in: 12,847 repos          │                 │
│            │   confidence: 0.99               │                 │
│            │   auto-fix success rate: 97%     │                 │
│            │                                  │                 │
│            │  "missing rate limit on /api/"   │                 │
│            │   seen in: 3,291 repos           │                 │
│            │   confidence: 0.94               │                 │
│            │   frameworks: express, fastapi   │                 │
│            │                                  │                 │
│            │  "phoenix channel auth bypass"   │                 │
│            │   seen in: 847 repos             │                 │
│            │   confidence: 0.91               │                 │
│            │   framework-specific: phoenix    │                 │
│            └─────────────────────────────────┘                 │
│                                                                │
│  patterns promoted through confidence tiers:                    │
│  PROPOSED (< 0.7) → ADOPTED (> 0.9, 3+ repos)                 │
│  → CANONICAL (20+ repos, 0 regressions, 1yr stable)            │
│  → LEGACY (replaced, archived)                                  │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 what gets shared (and what doesn't)

**shared (anonymized):**
- vulnerability pattern type (e.g., "SQL injection via string interpolation in Python")
- detection regex / AST pattern
- remediation template
- confidence score
- language / framework tag
- CWE / OWASP classification

**never shared:**
- source code
- file paths
- repo names
- organization names
- business logic
- variable names
- API keys / secrets (obviously)
- anything that could identify the repo or its owners

**the privacy model:** think of it like how antivirus software works. your computer reports "I saw malware signature X" — not "here's my entire hard drive." Crux reports "I saw vulnerability pattern X in Python" — not "here's the code."

### 3.3 why this is a moat

every repo that installs `crux-review` makes the action smarter for every other repo. this is a classic network effect:

- repo 1,000: catches common vulnerabilities (OWASP Top 10)
- repo 10,000: catches framework-specific patterns (Phoenix auth bypass, Django ORM injection)
- repo 100,000: catches project-architecture patterns (microservice auth delegation, event sourcing race conditions)
- repo 1,000,000: catches industry-specific patterns (fintech double-spend, healthcare PHI exposure, e-commerce cart manipulation)

**CodeRabbit has 2M repos but doesn't compound knowledge across them.** each review is independent. Crux's public knowledge tier means repo 2,000,001 gets the benefit of everything learned from the first 2,000,000.

### 3.4 the promotion pipeline

patterns don't go straight into the public tier. they graduate:

```
1. DETECTION
   agent finds pattern in repo A
   → logged as PROPOSED (confidence < 0.7)

2. VALIDATION
   same pattern found in repos B, C, D
   → promoted to ADOPTED (confidence > 0.9, confirmed in 3+ repos)
   → now flagged in reviews with "seen in N repos"

3. CANONICALIZATION
   pattern confirmed in 20+ repos over 1+ year
   zero false positives, zero regressions
   → promoted to CANONICAL
   → included in default review (even repos without .crux/)
   → becomes part of "industry standard" knowledge

4. DEPRECATION
   pattern replaced by better detection
   or language/framework evolves to prevent it
   → moved to LEGACY (archived, not active)
```

### 3.5 the competitive intelligence this creates

after 100K+ repos, trinsiklabs has:
- the most comprehensive database of real-world vulnerability patterns, by language and framework
- detection accuracy that improves continuously without manual rule writing
- framework-specific knowledge that competitors would need years to replicate
- a moat that deepens with every installation

this data (aggregated, anonymized) is also the foundation for:
- annual "state of code security" reports (marketing gold)
- framework-specific security guides (community goodwill)
- enterprise sales conversations backed by data

---

## part 4: architecture

### 4.1 the action itself

```
trinsiklabs/crux-review/
├── action.yml                    # GitHub Action metadata
├── Dockerfile                    # container action (for isolation + reproducibility)
├── src/
│   ├── main.ts                   # entry point
│   ├── pr.ts                     # PR diff extraction, file classification
│   ├── router.ts                 # mode routing logic
│   ├── passes/
│   │   ├── security-audit.ts     # recursive security audit (7 categories, up to 3 iterations)
│   │   ├── tdd-enforcement.ts    # test coverage check, TDD policy
│   │   ├── corrections.ts        # repo corrections + public knowledge matching
│   │   └── code-quality.ts       # general code quality review
│   ├── modes/
│   │   ├── build-py.ts           # python-specific review rules
│   │   ├── build-ex.ts           # elixir-specific review rules
│   │   ├── build-ts.ts           # typescript-specific review rules
│   │   ├── infra.ts              # terraform/docker/k8s review rules
│   │   ├── design.ts             # UI component review (accessibility, responsiveness)
│   │   └── test.ts               # test quality review
│   ├── output/
│   │   ├── comments.ts           # format inline PR comments
│   │   ├── summary.ts            # format summary review comment
│   │   ├── sarif.ts              # generate SARIF for Security tab
│   │   └── check.ts              # set check run status
│   ├── knowledge/
│   │   ├── local.ts              # read .crux/ from repo
│   │   ├── public.ts             # query public knowledge API
│   │   └── contribute.ts         # submit anonymized patterns
│   └── llm/
│       ├── client.ts             # LLM API client (Claude, GPT-4o, DeepSeek)
│       └── prompts.ts            # review prompts per mode + pass
├── test/
│   ├── fixtures/                 # sample PRs for testing
│   └── *.test.ts
└── dist/                         # compiled action (committed for distribution)
```

### 4.2 the backend service

the action calls a trinsiklabs-hosted API for:
- LLM inference (the action doesn't call Claude/OpenAI directly — trinsiklabs manages the API keys and rate limits)
- public knowledge tier queries
- pattern contribution
- usage metering (for billing)

```
┌─────────────────────────┐
│  GitHub Action Runner    │
│  (in developer's CI)     │
│                          │
│  reads PR diff           │
│  reads .crux/ if exists  │
│  sends to Crux API       │
└──────────┬───────────────┘
           │ HTTPS (encrypted)
           │ sends: diff + .crux/ context
           │ receives: review comments + findings
           ▼
┌──────────────────────────┐
│  Crux Review API          │
│  (trinsiklabs hosted)     │
│                           │
│  ├── /v1/review           │  ← main review endpoint
│  ├── /v1/knowledge/query  │  ← public knowledge lookup
│  ├── /v1/knowledge/submit │  ← anonymized pattern contribution
│  ├── /v1/sarif            │  ← generate SARIF report
│  └── /v1/usage            │  ← billing/metering
│                           │
│  backed by:               │
│  ├── Claude API           │  ← primary LLM
│  ├── PostgreSQL           │  ← knowledge store
│  ├── vector DB            │  ← semantic pattern matching
│  └── Redis                │  ← rate limiting + caching
└───────────────────────────┘
```

### 4.3 data flow — what leaves the developer's CI

this is the trust question. developers will ask: "what do you see?"

**sent to Crux API:**
- PR diff (the changed lines only, not the full codebase)
- `.crux/corrections.md` content (if it exists)
- `.crux/knowledge/` content (if it exists)
- file paths of changed files (for mode routing)
- language/framework hints (auto-detected or configured)

**NOT sent:**
- full repository source code
- git history
- secrets / environment variables
- other branches
- issues / discussions
- team member information

**data retention:**
- PR diff: deleted after review completes (zero retention)
- anonymized patterns: stored in public knowledge tier (opt-in, configurable)
- usage metrics: stored for billing

**the CodeRabbit benchmark:** CodeRabbit is SOC2 Type II certified with zero data retention post-review. Crux should match this from day one.

### 4.4 handling large PRs

GitHub API limits: 300 files max in a PR diff, 20,000 lines or 1MB raw diff.

**strategy for large PRs:**
1. if PR > `max-files` config (default 50): review only high-risk files (security-sensitive, new files, files with known correction patterns)
2. if diff > `max-diff-lines` config (default 5000): summarize with file-level findings, skip line-level comments
3. if PR > GitHub's 300-file limit: post a warning comment suggesting the PR be split
4. always prioritize: security findings > TDD violations > corrections > code quality

---

## part 5: the free tier — growth engine

### 5.1 pricing model

```
FREE TIER (open source + small teams):
├── unlimited public repos
├── 100 private repo reviews/month
├── security audit (1 iteration, not recursive)
├── TDD enforcement (coverage check only, not strict)
├── corrections from public knowledge tier
├── inline comments + summary
├── SARIF upload to GitHub Security tab
└── "powered by Crux" badge in review comments

PRO ($19/seat/month):
├── unlimited private repo reviews
├── recursive security audit (up to 3 iterations)
├── full TDD enforcement (strict mode available)
├── repo-specific corrections (.crux/corrections.md)
├── custom mode routing
├── auto-fix suggestions with code
├── priority LLM inference (faster reviews)
├── no badge in review comments
└── email support

TEAM ($39/seat/month):
├── everything in Pro
├── team knowledge sharing across repos
├── custom security policies
├── SARIF + custom reporting formats
├── Slack/Discord notifications
├── compliance reports (SOC2, HIPAA, PCI DSS checklists)
├── SSO/SAML integration
├── dedicated support
└── SLA: reviews complete in <5 minutes

ENTERPRISE (custom pricing):
├── everything in Team
├── self-hosted option (no data leaves your network)
├── private knowledge tier (org-only, not shared publicly)
├── custom LLM integration (use your own API keys)
├── audit logs
├── dedicated instance
├── compliance certifications
├── professional services
└── SLA: 99.9% uptime
```

### 5.2 why per-seat, not per-repo or per-review

CodeRabbit charges per-developer ($24/seat). this is the market-established model and developers understand it. per-review pricing creates anxiety ("is this review worth the cost?"). per-repo pricing punishes monorepo teams. per-seat is predictable and aligns with how GitHub itself charges.

**the free tier is critical.** open source projects get unlimited free reviews forever. this is how you:
1. build the public knowledge tier (open source repos contribute the most diverse patterns)
2. get developers hooked on Crux reviews personally, so they push for it at work
3. build brand in the developer community
4. generate case studies and testimonials

### 5.3 the GitHub Marketplace listing

```
trinsiklabs/crux-review

🔒 AI-Powered Security + Quality Review for Every PR

crux-review runs 5 review passes on every pull request:
• recursive security audit (7 categories, up to 3 iterations)
• TDD enforcement (verify tests exist for new code)
• corrections check (catch patterns your repo has fixed before)
• mode-routed review (python, elixir, typescript, infra, design)
• code quality analysis

learns from every repo. gets smarter over time.

[Install Free] [View Plans]

────────────────────────

used by 47,000+ repos · 2.3M+ PRs reviewed
⭐ 4.8/5 (1,247 reviews)

categories: Code Review, Security, Testing, CI/CD
```

---

## part 6: the adoption flywheel

### 6.1 the five stages

```
STAGE 1: INSTALL (zero friction)
  developer finds crux-review on GitHub Marketplace
  adds YAML file to repo (~30 seconds)
  first PR gets reviewed automatically

  ↓

STAGE 2: VALUE (immediate)
  first review catches a real security issue
  developer thinks: "oh, this is actually useful"
  tells teammates

  ↓

STAGE 3: CUSTOMIZE (week 2-4)
  team creates .crux/corrections.md with repo-specific patterns
  reviews become project-aware
  false positives drop
  team starts depending on it

  ↓

STAGE 4: EXPAND (month 2-3)
  team installs on all repos
  upgrades to Pro for recursive security audit + strict TDD
  developers start using Crux locally (the CLI / MCP tools)
  .crux/ directory becomes part of repo standard

  ↓

STAGE 5: ADVOCATE (month 3+)
  developer tweets about it / posts on HN / r/ExperiencedDevs
  writes blog post about how Crux caught a critical vuln
  team lead presents to engineering org
  org upgrades to Team/Enterprise

  → new developers discover crux-review → STAGE 1
```

### 6.2 the local adoption bridge

this is the strategic genius of the GitHub Action: **it's the gateway drug to full Crux adoption.**

```
crux-review (GitHub Action)
  ↓ "I want these corrections to work while I'm coding, not just in CI"

crux CLI + MCP Server (local development)
  ↓ "I want to switch between Claude Code and Cursor without losing context"

crux switch (tool-agnostic portability)
  ↓ "I want my entire team sharing knowledge"

crux team knowledge tier (org-wide intelligence)
  ↓ "I want this running our production infrastructure"

crux + openclaw (autonomous operations)
```

every step is a natural progression. the GitHub Action is the top of the funnel.

---

## part 7: the public knowledge tier as competitive moat

### 7.1 network effects at scale

```
INSTALLATIONS    KNOWLEDGE QUALITY              WHAT UNLOCKS
─────────────    ─────────────────              ────────────
1,000            OWASP Top 10 patterns          basic security review
                 common linting patterns         works for any language
                 standard test patterns

10,000           framework-specific patterns     "phoenix channel auth bypass"
                 library-specific anti-patterns   "react useEffect cleanup"
                 CI/CD misconfigurations          "docker run as root"

100,000          architecture patterns            "microservice auth delegation"
                 industry-specific vulns          "fintech double-spend"
                 supply chain attack patterns     "npm package typosquatting"

1,000,000        emergent vulnerability classes   patterns no human cataloged
                 cross-language pattern transfer   "this Go bug = that Rust bug"
                 predictive security              "this pattern leads to X vuln"

10,000,000       the most comprehensive           no competitor can replicate
                 vulnerability database            without the same install base
                 in existence                      years of compounding
```

### 7.2 data products from the knowledge tier

the aggregated, anonymized data enables:

1. **"state of code security" annual report** — what vulnerabilities are most common, by language, by framework, trending up or down. this is marketing gold and establishes thought leadership.

2. **framework security scores** — "Phoenix has 12% fewer critical vulnerabilities than Rails per 1000 repos." framework communities share this, driving installs.

3. **enterprise security benchmarks** — "your org's vulnerability density is 2.3x the industry average for Python codebases." drives Team/Enterprise upgrades.

4. **open source vulnerability database** — contribute canonical patterns to CVE databases and security research. goodwill + citations + brand.

5. **security training content** — "the 50 most common vulnerabilities in React apps, with real (anonymized) examples." developer education → brand → installs.

---

## part 8: technical implementation roadmap

### phase 1: MVP (weeks 1-6)

**goal:** working GitHub Action that runs security audit + TDD check + posts comments.

```
week 1-2: scaffolding
  - GitHub Action metadata (action.yml)
  - Docker container setup
  - PR diff extraction (GitHub API)
  - file classification (language detection)
  - basic mode routing (python, typescript, elixir, go, rust)

week 3-4: review passes
  - security audit pass (single iteration, 7 categories)
  - TDD enforcement pass (coverage check via existing tools)
  - inline comment formatting
  - summary comment generation
  - check status (pass/fail)

week 5-6: backend
  - Crux Review API (FastAPI or Phoenix — eat your own cooking)
  - Claude API integration (primary LLM)
  - basic rate limiting
  - SARIF generation
  - GitHub Marketplace listing
```

**MVP scope:**
- security audit (1 iteration, not recursive yet)
- TDD enforcement (coverage check only)
- inline comments + summary
- SARIF upload
- works on public repos (free)
- supports: Python, TypeScript, Elixir, Go, Rust

### phase 2: intelligence (weeks 7-12)

**goal:** recursive security audit, corrections system, public knowledge tier.

```
week 7-8: recursive security audit
  - multi-iteration audit loop (find → fix-suggest → re-audit)
  - convergence logic (stop when 0 crit/high or max iterations)
  - finding deduplication across iterations
  - auto-fix code generation

week 9-10: corrections system
  - read .crux/corrections.md from repo
  - match correction patterns against PR diff
  - flag known anti-patterns with repo history context
  - generate corrections from review findings (write back to .crux/)

week 11-12: public knowledge tier v1
  - anonymized pattern extraction
  - PostgreSQL + pgvector for pattern storage
  - pattern promotion pipeline (PROPOSED → ADOPTED)
  - opt-in contribution (configurable per repo)
  - public knowledge query API
```

### phase 3: scale (weeks 13-20)

**goal:** Pro/Team tiers, multi-mode routing, real-time performance.

```
week 13-14: pricing + billing
  - Stripe integration (we know this one)
  - GitHub Marketplace billing (native)
  - usage metering (reviews/month for free tier)
  - seat management (Pro/Team)

week 15-16: advanced mode routing
  - custom mode definitions (.crux/modes/)
  - design review mode (accessibility, responsive)
  - infra review mode (Terraform, Docker, K8s)
  - test quality review mode (not just coverage — test design)

week 17-18: team features
  - team knowledge sharing across org repos
  - custom security policies
  - Slack/Discord notifications
  - compliance report templates (SOC2, HIPAA, PCI DSS)

week 19-20: performance + reliability
  - review completion <3 minutes for average PR
  - caching layer (don't re-analyze unchanged files)
  - parallel pass execution
  - fallback LLM (if Claude is down, use GPT-4o)
  - monitoring + alerting (eat your own cooking: Crux on Crux)
```

### phase 4: enterprise (weeks 21-30)

**goal:** self-hosted option, private knowledge tier, compliance certifications.

```
week 21-24: self-hosted deployment
  - Helm chart for Kubernetes
  - Docker Compose for small teams
  - bring-your-own-LLM (use your API keys)
  - air-gapped mode (no external API calls)

week 25-28: compliance
  - SOC2 Type II audit preparation
  - audit logging
  - data residency options (EU, US, APAC)
  - SSO/SAML integration
  - RBAC for review policies

week 29-30: enterprise features
  - private knowledge tier (org-only patterns)
  - cross-repo analysis ("this vulnerability exists in 7 of your 200 repos")
  - executive dashboard
  - API for custom integrations
  - professional services offering
```

---

## part 9: marketing the action

### 9.1 launch strategy

**the launch post (X/Twitter):**
```
just shipped crux-review — a github action that runs
recursive security audits on every PR.

not "flag and forget" like sonar/snyk.
it finds a vulnerability, suggests a fix, then re-audits
the fix to make sure it didn't introduce new issues.
up to 3 iterations. converges to zero critical findings.

also enforces TDD (your PR needs tests) and catches
patterns your repo has already fixed before.

one line of YAML. free for open source. forever.

uses: trinsiklabs/crux-review@v1
```

**the HN launch:**
```
Show HN: Crux Review – recursive security audit as a GitHub Action

I built a GitHub Action that runs a recursive security
audit loop on every PR. Most tools scan once and dump
findings. Crux audits, suggests fixes, then re-audits
to verify the fixes don't introduce new issues. Up to 3
iterations, converges to zero critical/high findings.

It also enforces TDD (PRs need tests for new code) and
has a corrections system — if your repo has fixed a
pattern before, it'll catch you repeating it.

The interesting part: every repo that installs it
contributes anonymized vulnerability patterns to a
public knowledge base. The action gets smarter with
every installation. Repo 100,000 benefits from
everything learned by the first 99,999.

Free for open source, forever. One line of YAML.

https://github.com/marketplace/trinsiklabs-crux-review
```

### 9.2 growth channels

1. **open source adoption** — free forever for public repos. target popular OSS projects. one high-profile project using crux-review = thousands of developers seeing it in PRs.

2. **"vulnerability of the week"** — weekly post showing a real (anonymized) vulnerability pattern from the public knowledge tier, how Crux catches it, and the fix. educational content that's also marketing.

3. **framework community engagement** — "the 10 most common security issues in Phoenix apps" based on real data from the knowledge tier. post in r/elixir, ElixirForum, etc. repeat for every framework.

4. **GitHub Stars program** — engage GitHub Stars (developer influencers) to try and review crux-review.

5. **conference talks** — "what we learned from reviewing 1 million PRs" — the data from the public knowledge tier is the talk.

6. **the bridge to full Crux** — every crux-review user sees `.crux/` in their repo. they learn what it does. they try the CLI. the funnel works.

---

## part 10: competitive positioning

### 10.1 versus CodeRabbit

| | CodeRabbit | Crux Review |
|---|---|---|
| price | $24/seat | $19/seat (free for OSS) |
| security audit | single pass | recursive (up to 3 iterations) |
| TDD enforcement | no | yes |
| corrections system | no | yes (repo-specific + public) |
| knowledge compounding | no (each review independent) | yes (public knowledge tier) |
| mode routing | no (one-size-fits-all) | yes (python, elixir, infra, design) |
| SARIF upload | yes | yes |
| self-hosted option | no | yes (enterprise) |
| open source | no | core is open source |

**the one-liner:** "CodeRabbit reviews code. Crux reviews code, enforces tests, audits security recursively, and gets smarter from every repo."

### 10.2 versus GitHub Copilot code review

| | Copilot Review | Crux Review |
|---|---|---|
| can block merges | no | yes |
| recursive security audit | no | yes |
| TDD enforcement | no | yes |
| corrections system | cross-agent memory (new, limited) | full corrections file + public tier |
| mode routing | no | yes |
| independent (no vendor lock-in) | GitHub-only | works with any Git host (future) |
| pricing | included in Copilot ($19-39/seat) | $19/seat (free for OSS) |

**the one-liner:** "Copilot suggests. Crux enforces."

### 10.3 versus SonarCloud/Snyk/Semgrep

| | SAST tools | Crux Review |
|---|---|---|
| detection method | static rules + patterns | AI reasoning + rules + patterns |
| recursive auditing | no | yes |
| understands business logic | no | yes (reads .crux/knowledge/) |
| TDD enforcement | no | yes |
| corrections system | no | yes |
| false positive rate | moderate-high | low (AI reasoning reduces FPs) |
| setup complexity | moderate (config per language) | minimal (one YAML line) |

**the one-liner:** "SonarCloud finds patterns. Crux understands code."

---

## part 11: risk analysis

### technical risks

| risk | impact | mitigation |
|---|---|---|
| LLM hallucinations (false positives) | developers lose trust | confidence scoring, threshold filtering, "seen in N repos" validation |
| slow reviews (>5 min) | developers skip/disable | caching, parallel passes, priority queue for Pro |
| LLM API downtime | reviews blocked | fallback LLM chain (Claude → GPT-4o → DeepSeek), graceful degradation |
| large PR handling | OOM or timeout | file limits, diff limits, smart file selection |
| SARIF formatting errors | Security tab broken | extensive test fixtures, GitHub's SARIF validator |

### business risks

| risk | impact | mitigation |
|---|---|---|
| CodeRabbit copies recursive audit | feature parity | public knowledge tier is the moat (they can't replicate the data) |
| GitHub builds this natively | existential | specialize deeper (TDD, corrections, mode routing), multi-git-host support |
| developers don't trust AI review | slow adoption | open-source core, show reasoning in comments, confidence scores |
| public knowledge tier privacy backlash | trust damage | opt-in only, SOC2 certification, open-source the anonymization code |
| free tier costs too much to run | burn rate | rate limit free tier, cache aggressively, use cheaper models for low-risk passes |

### the GitHub risk

GitHub is the platform. they can build this natively. Copilot code review is already moving in this direction, and their "cross-agent memory" system is a knowledge tier of sorts.

**mitigation strategy:**
1. **speed:** ship before Copilot catches up. they're a large org; we're one developer who ships daily.
2. **depth:** Copilot won't do recursive security audits or TDD enforcement — those are opinionated features that conflict with GitHub's "platform for everyone" positioning.
3. **independence:** add GitLab and Bitbucket support. crux-review becomes the cross-platform choice.
4. **the .crux/ directory:** even if GitHub builds a better code review action, the `.crux/` directory is the moat. it's the portable intelligence layer. GitHub's memory system is locked to Copilot. Crux works everywhere.
5. **acquisition target:** if GitHub/Microsoft wants this capability, buying trinsiklabs is faster than building it. a good outcome.

---

## part 12: integration with the broader crux ecosystem

### the full picture

```
┌─────────────────────────────────────────────────────────────┐
│                    CRUX ECOSYSTEM                             │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ crux-review   │  │ crux CLI     │  │ crux MCP     │       │
│  │ GitHub Action │  │ local dev    │  │ server       │       │
│  │              │  │              │  │              │       │
│  │ runs in CI   │  │ runs locally │  │ connects to  │       │
│  │ reviews PRs  │  │ crux switch  │  │ any AI tool  │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │               │
│         └──────────────────┼──────────────────┘               │
│                            │                                  │
│                            ▼                                  │
│                   ┌────────────────┐                          │
│                   │  .crux/        │                          │
│                   │  directory     │                          │
│                   │                │                          │
│                   │  THE shared    │                          │
│                   │  intelligence  │                          │
│                   │  layer         │                          │
│                   └────────┬───────┘                          │
│                            │                                  │
│                            ▼                                  │
│                   ┌────────────────┐                          │
│                   │  public        │                          │
│                   │  knowledge     │                          │
│                   │  tier          │                          │
│                   │                │                          │
│                   │  compounding   │                          │
│                   │  across all    │                          │
│                   │  installations │                          │
│                   └────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

**the .crux/ directory is the connective tissue:**
- crux-review reads `.crux/corrections.md` in CI and writes new corrections when it finds patterns
- crux CLI reads/writes `.crux/` during local development
- crux MCP server exposes `.crux/` to any connected AI tool
- all three contribute to and benefit from the public knowledge tier

**the developer experience:**
1. coding locally with Claude Code + Crux MCP → corrections learned
2. push PR → crux-review runs, uses those corrections + public knowledge
3. crux-review finds new pattern → writes to `.crux/corrections.md`
4. next local session → correction available immediately
5. pattern promoted to public tier → helps every other repo

it's a closed loop. local development and CI reinforce each other. every interaction makes the system smarter.

---

## the bottom line

`crux-review` isn't just a GitHub Action. it's the distribution strategy for the entire Crux ecosystem.

- **zero adoption friction** — one line of YAML
- **immediate value** — first PR review shows real findings
- **natural upgrade path** — action → .crux/ directory → CLI → MCP → full ecosystem
- **network effect moat** — public knowledge tier compounds with every installation
- **revenue engine** — $19-39/seat with enterprise upsell
- **data flywheel** — aggregated patterns become reports, talks, guides, brand

CodeRabbit proved the market (2M+ repos, $24/seat). Crux Review is the version that actually learns.

the tagline: **"the code review that gets smarter from every repo."**
