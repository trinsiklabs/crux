# crux + openclaw: the autonomous business operations guide

## what this document is

this is a comprehensive, honest guide to using Crux (intelligence framework) + OpenClaw (autonomous agent platform) to build and run a business with minimal human involvement. not "AI does everything" fantasy — but a real architecture where AI handles execution and optimization while humans handle judgment, legal obligations, and strategic direction.

the goal: **human oversight, not human labor.**

you direct. the system executes.

---

## the stack

```
┌─────────────────────────────────────────────────────┐
│                  HUMAN LAYER                         │
│  (direction, judgment, legal signatures, oversight)  │
│  ~30 min/day reviewing dashboards + approvals        │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  CRUX LAYER                          │
│  (.crux/ directory — portable intelligence)          │
│  corrections · patterns · knowledge · safety rules   │
│  compounding context across every session + tool     │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                 OPENCLAW LAYER                        │
│  (autonomous execution engine)                       │
│  cron jobs · self-healing · browser automation        │
│  multi-agent orchestration · 10,000+ skills          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              INFRASTRUCTURE LAYER                     │
│  Vercel/Netlify · Stripe · Resend · PostgreSQL       │
│  GitHub Actions · Gmail · Google Analytics           │
└─────────────────────────────────────────────────────┘
```

**what Crux adds that OpenClaw alone doesn't have:** portable, compounding intelligence. OpenClaw is the execution engine — powerful, autonomous, self-healing. but every session starts from context files. Crux's `.crux/` directory IS those context files, structured for maximum reuse. corrections learned in one session carry forward forever. patterns discovered by one agent are available to every agent. safety rules enforced once are enforced always. without Crux, OpenClaw is a powerful amnesiac. with Crux, it's a team that gets smarter every day.

---

## part 1: building the product

### 1.1 code generation + development

**what's real today:**

OpenClaw agents (powered by Claude, GPT-4o, DeepSeek, etc.) can autonomously:
- scaffold full applications from prompts (Next.js, React Native, Phoenix, Rails, etc.)
- implement features across multiple files with correct imports and types
- write and run test suites
- debug failures by reading error output and fixing code
- commit to git with meaningful messages
- create pull requests with descriptions
- run overnight "night shift" builds — schedule a cron job at midnight, wake up to new features

**OpenClaw skills involved:**
- core code execution (exec tool — full shell access)
- GitHub skill (commits, PRs, issues, actions)
- any language server / linter via shell

**what Crux adds:**
- `.crux/corrections.md` — every "don't do X, do Y instead" persists. the agent stops making the same mistakes.
- `.crux/knowledge/` — domain context (your business logic, your API contracts, your naming conventions) loaded automatically.
- `.crux/sessions/` — what was built, why, and what was deferred. the next session picks up where the last one left off.
- `crux switch` — move between Claude Code, OpenCode, Cursor, Aider mid-project. all context travels.

**realistic capability:** a well-configured Crux + OpenClaw setup can autonomously build and iterate on a web application, run tests, deploy, and pick up deferred work across sessions. this is documented and real — users report waking up to functional apps their agents built overnight.

### 1.2 design

**what's real today:**

- Claude/GPT-4o generate solid Tailwind CSS and component layouts
- OpenClaw's browser automation can screenshot results for visual QA
- v0 (Vercel) generates React UI components from prompts

**what Crux adds:**
- design preferences stored in `.crux/corrections.md`: "use 8px spacing grid," "never use rounded-full on buttons," "dark mode default, zinc-900 background"
- the agent learns your visual language over time instead of guessing fresh each session

**gaps:**
- no Figma integration via OpenClaw (no official skill)
- complex visual design (illustrations, branding, custom graphics) still needs human or specialized tools
- UI polish (micro-interactions, animations, responsive edge cases) requires iteration with human feedback

**realistic capability:** functional, clean UI. not award-winning design. think "solid SaaS dashboard" not "Stripe's marketing site." for most businesses, this is enough.

### 1.3 mobile apps

**what's real today:**

- React Native + Expo is the standard for AI-generated mobile apps (used by Replit, Bolt.new, Natively)
- OpenClaw can scaffold and build Expo projects
- Expo EAS handles cloud builds and app store submission from the command line:
  - `eas build --platform all` — builds iOS + Android without Xcode/Android Studio
  - `eas submit --platform all` — submits to both stores
  - `eas update` — OTA updates that bypass app review

**what Crux adds:**
- mobile-specific corrections and patterns persist: "use SafeAreaView on iOS," "handle Android back button," "test on both platforms before submitting"
- API contract knowledge shared between web and mobile agents

**gaps requiring human:**
- Apple Developer account ($99/year) — requires human identity, KYC
- Google Play Console ($25 one-time) — requires human identity
- first app store submission — requires human review of metadata, screenshots, privacy policy
- app store rejections — appeals require human judgment about policy interpretation
- ~20% of Google Play submissions hit false rejections from automated review, requiring human appeals

**realistic capability:** autonomous build + deploy cycle. human handles account setup, first submission, and rejection appeals. subsequent updates can be fully autonomous via `eas update` for JS changes.

### 1.4 chrome extensions

**what's real today:**

- OpenClaw can generate manifest.json, popup HTML, background scripts, content scripts
- browser automation (chrome-relay + headless Playwright) can test extensions
- Chrome Web Store submission is API-accessible

**gaps:**
- Chrome Web Store developer account requires human registration ($5 one-time)
- review process for new extensions is manual on Google's end (1-3 days)

**realistic capability:** fully autonomous build and packaging. human handles store account and initial review. updates can be autonomous.

---

## part 2: monetization

### 2.1 payment processing (Stripe)

**what's real today:**

OpenClaw's Stripe skill handles the full payment lifecycle:
- **PaymentIntents** — create, confirm, capture one-time payments
- **Subscriptions** — create plans, manage trials, handle upgrades/downgrades, metered billing
- **Invoicing** — generate, finalize, send invoices
- **Refunds** — full and partial, with reason tracking
- **Webhooks** — real-time event handling for payment failures, subscription changes, trial endings
- **Customer management** — create customers, store tokenized payment methods
- **Test/live mode** — develop against test mode, switch to live with one config change
- **Idempotent requests** — safe retries, no double-charges

additionally:
- **CreditClaw Wallet skill** — agent-controlled spending with per-transaction limits and category blocks
- **Webhook Generator skill** — auto-generates webhook handlers with signature verification and retry-safe patterns
- **Payment skill** — multi-gateway support (Stripe, PayPal, Square, crypto)

**what Crux adds:**
- pricing strategy stored in `.crux/knowledge/`: "free tier = 100 API calls, pro = $29/month, enterprise = custom"
- refund policy rules in `.crux/corrections.md`: "auto-refund if within 7 days and <$50, escalate otherwise"
- payment error patterns: "when Stripe returns card_declined, show X message, don't retry"

**gaps requiring human:**
- Stripe account creation — requires human KYC (government ID, bank account, tax info)
- PCI DSS compliance attestation — human must sign SAQ (Self-Assessment Questionnaire)
- high-risk transaction review — OFAC/AML regulations require human compliance officer sign-off
- pricing decisions — AI can suggest based on data, human decides

**realistic capability:** once Stripe account exists and is verified, the entire payment lifecycle runs autonomously. AI creates checkout flows, handles webhooks, processes refunds within policy, sends receipts, manages subscriptions. human reviews monthly revenue reports and handles pricing changes.

### 2.2 accounting + bookkeeping

**what's real today:**

- **QuickBooks skill** — OAuth-connected, handles invoicing, collections, recurring billing, payment reconciliation, company-level reporting
- **Xero skill** — invoice CRUD, contact management, bank transaction retrieval, P&L reporting, reconciliation
- **OpenClaw Accounting Firm Suite** — 10 AI skills built for CPAs/bookkeepers, integrates with both QuickBooks and Xero

**what Crux adds:**
- categorization rules in `.crux/knowledge/`: "AWS charges = COGS, Stripe fees = payment processing, domain registrations = marketing"
- reconciliation patterns learned over time

**gaps requiring human:**
- tax filings — legally require human signature (federal, state, local)
- audit preparation — CPA must personally attest
- financial strategy — AI provides data, human makes decisions

**realistic capability:** day-to-day bookkeeping runs autonomously. transactions categorized, invoices sent, payments reconciled, reports generated. human reviews monthly and handles tax filings (or delegates to CPA).

---

## part 3: marketing + growth

### 3.1 email marketing

**what's real today:**

OpenClaw email skills cover the full lifecycle:
- **Gmail integration** — read, compose, reply, label, search via IMAP/SMTP + Pub/Sub for real-time monitoring
- **Resend integration** — transactional email from your own domain (free tier: 3,000 emails/month)
- **SMTP-Send skill** — works with any SMTP provider (Gmail, Outlook, Yahoo, Resend, custom)
- **Email Marketing skill** — campaign management, drip sequences (welcome, nurture, sales), list segmentation, deliverability optimization, engagement tracking
- **IMAP/SMTP skill** — full inbox management, search, attachments, read/unread status

**autonomous email sequences possible:**
1. new user signs up → welcome email (immediate)
2. day 3 → feature highlight email
3. day 7 → case study / social proof
4. day 14 → upgrade prompt with discount
5. day 30 → re-engagement if inactive

all of this runs via OpenClaw cron jobs. no human involvement after initial setup.

**what Crux adds:**
- voice/tone rules in `.crux/corrections.md`: "always lowercase, never use exclamation marks, keep subject lines under 40 chars"
- deliverability knowledge: "warm up new domains at 50 emails/day for first week, increase 2x weekly"
- engagement patterns: "Tuesday 10am sends get highest open rates for our audience"

**gaps:**
- email reputation recovery from major incidents — requires human decision-making and potentially ISP relationship management
- no dedicated HubSpot/Mailchimp/ConvertKit integration (Resend + SMTP covers the sending, but you don't get their analytics UIs)

**realistic capability:** fully autonomous email marketing. setup the sequences, configure the triggers, let it run. AI manages deliverability (SPF/DKIM/DMARC, warmup, bounce handling). human reviews engagement metrics weekly.

### 3.2 social media + content

**what's real today:**

- **Social Content skill** — create and schedule across LinkedIn, Twitter/X, Instagram, TikTok, Facebook
- **Twitter/X skill** — read tweets/threads, browse profiles, search, post, engage
- **Tweet-Writer skill** — specialized tweet generation
- **Marketing Growth skill** — cross-post to Medium, Dev.to, LinkedIn, Twitter, Reddit (non-promotional)
- **Post Bridge** — AI social media manager integration
- **Social-Gen skill** — platform-optimized post generation

combined with Crux's marketing pipeline (from the marketing plan):
- event-driven triggers fire when commits/interactions hit thresholds
- drafts generated in your voice
- one-keystroke approval → tweet + blog post + deploy

**what Crux adds:**
- your voice style (all lowercase, specific phrasing patterns) enforced consistently
- content calendar awareness: "posted about MCP architecture yesterday, don't repeat"
- engagement patterns: "threads with code snippets get 3x engagement"
- community knowledge: "r/ExperiencedDevs hates self-promotion, lead with the problem"

**gaps:**
- Instagram/TikTok require visual content creation (AI image/video generation is separate)
- community engagement (responding to replies, DMs) needs human judgment for non-routine interactions
- influencer relationships — human-only

**realistic capability:** autonomous content generation, scheduling, and cross-posting. human approves drafts (one keystroke) and handles community engagement that requires judgment.

### 3.3 SEO

**what's real today:**

- **SEO Optimizer skill** — title tags, meta descriptions, heading hierarchy, image alt text, Open Graph, Twitter Cards, schema.org markup, canonical URLs, mobile/technical SEO
- **SEO Audit skill** — full technical analysis
- **Sitemap generation** — automated XML sitemap creation
- **GA4 Analytics skill** — Google Analytics + Search Console + Indexing API combined
- **Content Creator skill** — SEO-optimized content generation

**what Crux adds:**
- keyword strategy in `.crux/knowledge/`: target keywords, competitor analysis, content gaps
- SEO patterns: "every blog post needs schema.org/Article markup," "internal link to /docs/ from every technical post"
- performance baselines: "organic traffic was 450/week last month, flag if drops below 350"

**realistic capability:** fully autonomous technical SEO. content SEO (keyword research, content planning) benefits from human strategic input but execution is autonomous.

---

## part 4: operations

### 4.1 deployment + infrastructure

**what's real today:**

- **Web-Hosting Meta-Skill** orchestrates the full deploy pipeline:
  - GitHub repo integration
  - Vercel deployment (framework auto-detection, tarball packaging, preview URLs, production deploy)
  - Netlify deployment (site creation, CI/CD setup, production deploy)
  - domain + DNS operations
  - SSL certificate setup
  - API gateway integration

- **self-healing architecture (4-tier):**
  - Tier 1 — KeepAlive (0-30s): auto-restart on crash, state preservation
  - Tier 2 — Watchdog v4.1 (3-5min): HTTP + PID + memory monitoring every 3 min, exponential backoff
  - Tier 3 — AI Emergency (5-30min): Claude Code reads logs, diagnoses, writes fix, tests, deploys
  - Tier 4 — Human Alert: Discord/Telegram notification when autonomous recovery fails
  - documented success rate: 9 of 14 incidents resolved fully autonomously, 5 correctly escalated

- **cron-based maintenance:**
  - scheduled health checks (endpoint verification, database ping, SSL expiry check)
  - log rotation
  - dependency updates (with test suite verification before merge)
  - database optimization (VACUUM, index rebuild)
  - backup verification

**what Crux adds:**
- infrastructure patterns: "this app needs 512MB minimum, crashes below that," "Vercel cold starts cause timeouts on the /api/heavy endpoint, use edge functions"
- incident history: every failure and its resolution stored, making future diagnosis faster
- deployment rules: "always deploy to staging first," "never deploy on Friday after 3pm"

**realistic capability:** fully autonomous deployment and self-healing. human gets notified only when Tier 4 escalation triggers (which is <36% of incidents based on documented testing). this is one of the strongest autonomy areas.

### 4.2 customer support

**what's real today:**

- OpenClaw agents can triage incoming tickets by urgency
- auto-route to appropriate response templates or escalation
- auto-respond to common issues (password resets, billing questions, feature requests)
- process refunds within policy (integrated with Stripe skill)
- documented: 60-70% first-contact resolution for e-commerce teams
- sentiment analysis for escalation (frustrated customer → human)

- multi-channel support via OpenClaw's 50+ channel integrations:
  - email (Gmail/IMAP)
  - Slack
  - Discord
  - Telegram
  - WhatsApp
  - and 45+ more

**what Crux adds:**
- support knowledge base in `.crux/knowledge/`: common issues, known bugs, workarounds
- response patterns: "when user reports X error, it's usually Y. check Z first."
- escalation rules: "any mention of 'legal' or 'lawyer' → immediate human escalation"
- customer context: "enterprise customers get priority, free tier users get templated responses"

**gaps:**
- novel situations (unusual bugs, edge cases) need human
- emotional situations (angry enterprise customer threatening to cancel) need human empathy
- financial disputes involving judgment (was this charge legitimate?) need human
- Gartner projects AI resolves 80% of standard queries by 2029, humans remain essential for 20%

**realistic capability:** 70-80% of support tickets handled autonomously. human reviews escalations daily (~30 min). this ratio improves over time as Crux accumulates more knowledge.

### 4.3 monitoring + analytics

**what's real today:**

- **GA4 skill** — traffic, conversions, top pages, user demographics, real-time visitors
- **Search Console integration** — search queries, indexing status, SEO performance
- **Task Monitor skill** — agent cost tracking (daily, all-time, projected), active session monitoring
- **ClawMetry / ClawWatcher** — real-time token usage and cost dashboards
- **custom dashboards** — Dashboard skill creates real-time, mobile-responsive monitoring pages

**what Crux adds:**
- metric baselines and anomaly thresholds: "normal daily traffic is 400-600, alert if <300 or >2000"
- cost tracking patterns: "Claude API spend should be <$50/day, flag spikes"
- business KPIs: "MRR, churn rate, LTV, CAC — track weekly, alert on negative trends"

**realistic capability:** fully autonomous monitoring. dashboards update in real-time. anomalies trigger alerts. human reviews weekly business metrics dashboard.

---

## part 5: what legally requires a human

this is the non-negotiable list. no amount of AI capability changes these requirements in 2026:

### must have human identity/signature

| requirement | why | frequency |
|---|---|---|
| business entity formation | legal registration requires human identity | once |
| bank account opening | KYC requires government ID, facial verification | once |
| Stripe account creation | KYC + tax info + bank account linkage | once |
| Apple Developer account | requires human identity + $99/year | once/year |
| Google Play Console | requires human identity + $25 | once |
| tax filings (federal/state) | human signature legally required | quarterly/annually |
| contract signing | only humans can bind organizations legally | as needed |
| PCI DSS self-assessment | human must sign compliance questionnaire | annually |
| GDPR Data Protection Impact Assessment | requires human judgment about risk | as needed |
| insurance policies | require human policyholder | annually |
| trademark/IP filings | require human applicant | as needed |

### must have human judgment (but AI assists)

| area | AI does | human does |
|---|---|---|
| pricing strategy | analyzes competitors, models scenarios | makes the decision |
| hiring/contractors | screens, schedules, provides analysis | makes hiring decisions |
| legal compliance | flags potential issues, drafts documents | reviews and signs |
| financial strategy | generates reports, models forecasts | allocates capital |
| partnership decisions | researches potential partners | negotiates and commits |
| crisis response | detects issues, drafts responses | approves public statements |
| product strategy | analyzes usage data, competitive landscape | decides what to build |

---

## part 6: the daily operating rhythm

here's what the human's day actually looks like when Crux + OpenClaw is running the business:

### morning review (~15 min)

```
8:00 AM — check overnight dashboard

  overnight build:
  ✓ 3 features implemented (PRs ready for review)
  ✓ 12 support tickets resolved (3 escalated)
  ✓ email sequence sent to 847 subscribers (42% open rate)
  ✓ 2 blog posts drafted from last night's commits
  ✗ 1 deployment failed — self-healed at Tier 3 (log attached)

  revenue:
  $2,847 MRR (+$129 from yesterday)
  4 new subscribers, 1 churn
  2 refund requests (both auto-processed within policy)

  alerts:
  ⚠ 3 support tickets need human judgment
  ⚠ 1 app store review response needed
  ⚠ Stripe flagged 1 transaction for manual review
```

### approval sprint (~10 min)

- review 3 escalated support tickets → respond or delegate
- review overnight PRs → merge or request changes
- approve 2 draft blog posts / tweets → one keystroke each
- review flagged Stripe transaction → approve or block

### strategic direction (~5 min, not daily)

- adjust pricing? tell the agent. it updates Stripe, the website, email templates, and docs.
- new feature idea? describe it. agent creates a GitHub issue, plans the architecture, starts building.
- enter a new market? describe the strategy. agent researches competitors, adjusts SEO, drafts content.

**total human time: ~30 minutes/day for a running business.**

everything else — code, deploy, email, support, monitoring, marketing, SEO, billing, bookkeeping — runs autonomously.

---

## part 7: the multi-agent architecture

for a real business, you don't run one OpenClaw agent. you run a crew:

```
┌────────────────────────────────────────────────────────────┐
│                    MISSION CONTROL                          │
│  (orchestration layer — routes tasks, manages state)        │
│  tools: Mission Control, CrewClaw, or custom orchestrator   │
└────────┬───────┬───────┬───────┬───────┬───────┬──────────┘
         │       │       │       │       │       │
    ┌────▼──┐ ┌──▼───┐ ┌▼────┐ ┌▼────┐ ┌▼────┐ ┌▼─────┐
    │ BUILD │ │DEPLOY│ │SALES│ │SUPP │ │MKTG │ │BOOKS │
    │ AGENT │ │AGENT │ │AGENT│ │AGENT│ │AGENT│ │AGENT │
    └───────┘ └──────┘ └─────┘ └─────┘ └─────┘ └──────┘

    BUILD:  writes code, runs tests, creates PRs
    DEPLOY: handles Vercel/Netlify, DNS, SSL, monitoring
    SALES:  manages Stripe, pricing pages, checkout flows
    SUPPORT: triages tickets, auto-responds, escalates
    MARKETING: content generation, email sequences, SEO, social
    BOOKKEEPING: QuickBooks/Xero sync, categorization, reports
```

each agent has:
- its own OpenClaw workspace and session isolation
- access to shared `.crux/` directory (Crux's intelligence layer)
- its own cron schedules
- inter-agent messaging for coordination

**what Crux enables here that OpenClaw alone doesn't:** all six agents share the same `.crux/knowledge/`, `.crux/corrections.md`, and `.crux/sessions/`. when the Build Agent learns "our API rate limits at 1000 req/min," the Support Agent knows it too. when the Marketing Agent discovers "threads with code snippets get 3x engagement," that pattern is available to every agent. the intelligence is collective and compounding.

---

## part 8: security + risk model

### the real risks

OpenClaw has documented security concerns that must be addressed:

1. **ClawHub malicious skills** — a security audit found 341 malicious skills out of 2,857 audited (~12%). the "ClawHavoc" campaign embedded infostealers (Atomic Stealer) in popular skills. **mitigation:** only install skills from verified publishers, audit skill code before installation, use OpenClaw's allowlist security mode.

2. **unrestricted file system access** — by default, OpenClaw can read SSH keys, .env files, browser cookies, any file your user has access to. **mitigation:** run agents in isolated containers/VMs, use allowlist mode for shell commands, never store production secrets on the same machine as OpenClaw agents.

3. **shell command execution** — default mode has no restrictions on what commands agents can run. **mitigation:** enable `security=allowlist` mode, which rejects command chaining/redirections unless explicitly safe-listed.

4. **LLM data exposure** — when using cloud LLM providers (Anthropic, OpenAI), all prompts (including your business data) go to those providers. **mitigation:** use on-premise/self-hosted models for sensitive operations, or accept the cloud LLM provider's data handling terms.

### what Crux adds to security

- `.crux/safety/` — rules that persist across every session:
  - "never commit .env files"
  - "never expose API keys in logs"
  - "never deploy to production without running tests"
  - "never process refunds over $500 without human approval"
  - "never send emails to more than 1000 recipients without human approval"
- safety rules compound — every incident teaches the system a new rule
- rules are portable — switch tools, safety travels with you

### the risk-stratified autonomy model

```
LOW RISK — fully autonomous (no human needed)
├── deploy to staging
├── run tests
├── process refund <$50
├── respond to FAQ support ticket
├── publish blog post (pre-approved template)
├── send transactional email (receipt, password reset)
└── rotate logs, run backups

MEDIUM RISK — AI proposes, human approves
├── deploy to production
├── process refund $50-$500
├── send marketing email to >100 recipients
├── merge PR that changes database schema
├── respond to support ticket mentioning "cancel" or "legal"
├── change pricing
└── publish social media post (non-templated)

HIGH RISK — human decides, AI assists
├── process refund >$500
├── sign contracts
├── file taxes
├── handle data breach response
├── respond to regulatory inquiry
├── make hiring/firing decisions
└── change business strategy
```

---

## part 9: cost model

### monthly operating costs (real business)

| item | cost | notes |
|---|---|---|
| Claude Code Pro (or API) | $100-200/month | primary LLM for all agents |
| OpenClaw | $0 | MIT-licensed open source |
| Crux | $0 | open source |
| VPS for agents | $20-50/month | DigitalOcean/Hetzner for running OpenClaw Gateway |
| Vercel Pro | $20/month | hosting + edge functions |
| Stripe fees | 2.9% + $0.30/txn | payment processing |
| Resend | $0-20/month | email (free tier = 3,000/month) |
| Apple Developer | $8.25/month | ($99/year) for iOS app |
| Google Play | $2.08/month | ($25 one-time, amortized) |
| domain (runcrux.io) | $2.50/month | (~$30/year) |
| **total fixed costs** | **~$175-300/month** | before Stripe transaction fees |

### comparison to Shipper 2.0

| | Shipper | Crux + OpenClaw |
|---|---|---|
| base cost | $100/month (Pro) | ~$175-300/month (all-in infrastructure) |
| per-app cost | $25/100 credits | $0 (unlimited) |
| real cost for serious use | $200-500+/month | ~$175-300/month (flat) |
| intelligence compounds | no (resets each session) | yes (Crux persists everything) |
| tool lock-in | yes (their chat UI only) | no (any AI tool) |
| self-healing | marketing claim | 4-tier documented system |
| email marketing | unsubstantiated | real Gmail + Resend + drip sequences |
| payment processing | unsubstantiated | real Stripe full lifecycle |
| open source | no | yes (audit every line) |

---

## part 10: what's missing + roadmap

### gaps that need custom Crux skills/modes

| gap | current workaround | what to build |
|---|---|---|
| native CRM | Notion/Trello integration | Crux CRM mode — customer lifecycle in `.crux/knowledge/customers/` |
| legal document generation | manual / generic LLM output | Crux legal templates — ToS, privacy policy, GDPR notices with auto-update on product changes |
| visual design iteration | screenshot + manual feedback | Crux design review mode — automated screenshot comparison against design spec |
| competitive monitoring | manual web searches | Crux competitive intel — scheduled scraping of competitor pricing, features, social |
| financial forecasting | spreadsheet modeling | Crux finance mode — automatic MRR/churn/LTV modeling from Stripe + QuickBooks data |
| multi-language support | manual translation | Crux i18n mode — auto-detect content changes, regenerate translations |

### gaps that need ecosystem maturation

| gap | timeline | dependency |
|---|---|---|
| LiveView Native replacing React Native | 12-18 months | Android client stability + AI training data |
| first-class CRM skill | 3-6 months | community demand is high, likely coming |
| HubSpot/Mailchimp integration | 3-6 months | MCP servers in development |
| autonomous app store submission | 6-12 months | Apple/Google API improvements needed |
| on-premise LLM for sensitive ops | available now | Llama 3, DeepSeek — but quality gap vs Claude |

---

## part 11: the honest bottom line

### what "build and run a business" actually means in 2026

**fully autonomous (no human needed after setup):**
- code generation + testing + deployment
- self-healing infrastructure
- email marketing sequences
- payment processing (within policy)
- SEO optimization
- content generation + scheduling
- bookkeeping + transaction categorization
- routine customer support (70-80%)
- monitoring + alerting

**human oversight (review + approve, ~30 min/day):**
- production deployments
- marketing content approval
- support escalations
- revenue/metrics review
- non-routine refunds

**human required (can't delegate to AI):**
- legal entity formation
- bank/payment account setup (KYC)
- tax filings
- contract signing
- strategic decisions
- crisis response
- app store account creation
- regulatory compliance attestation

### the marketing angle

Shipper says: "the first AI that can truly build and run a business for you."

the honest version: **no AI runs a business for you.** a human must exist for legal, financial, and strategic reasons. what AI can do is reduce the human's role from **full-time operator** to **part-time overseer.**

Crux + OpenClaw does this better than anything else because:
1. the intelligence compounds (Crux) instead of resetting
2. the execution is autonomous and self-healing (OpenClaw)
3. the stack is open source and auditable
4. there's no vendor lock-in, no per-app pricing, no middleman markup
5. you can switch AI tools without losing anything

**the real tagline: "your AI team gets smarter every day. Shipper's starts from scratch every session."**

---

## appendix: the Felix case study

the most documented example of an OpenClaw agent running a business:

- **Felix** — given $1,000 seed money
- within 3 weeks: earned $14,718
- architecture: OpenClaw + Telegram (project management) + layered memory + cron jobs + Stripe + crypto wallet
- actions taken autonomously: launched website, created info product, built X (Twitter) account, processed payments
- human role: initial setup, periodic oversight, strategic direction

this isn't hypothetical. it happened. with Crux's intelligence layer on top, Felix's patterns would compound instead of being locked in one agent's memory files.
