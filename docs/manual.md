# Crux User Manual

## Introduction

Welcome to Crux—a self-improving AI operating system built for developers who want to work smarter with local AI. Crux wraps your local LLMs (via Ollama) and agentic coding tools (primarily OpenCode CLI) into a unified system that learns from your workflow, adapts to your project needs, and gets safer and more efficient over time.

This manual assumes you've just run the setup script and are ready to dive in. It's structured to let you jump to what you need right now, then return to deeper sections as you grow more comfortable with the system.

---

## Getting Started

### What Just Got Installed

The setup script has given you several key pieces:

1. **Ollama integration** — Your local LLM runtime, ready to serve models without leaving your machine
2. **OpenCode CLI** — The agentic coding engine that handles file modifications, testing, and iteration
3. **The Crux session environment** — A persistent context layer that remembers corrections, preferences, and project knowledge
4. **Safety infrastructure** — Scripts-first architecture that audits all changes before they touch your code
5. **Knowledge base** — A growing repository of project-specific and user-level solutions that improve over time
6. **Daily digest system** — Automated reporting on system health, learning opportunities, and recommendations

None of this requires complicated configuration. You're ready to start now.

### Starting Your First Session

The workflow is simple:

1. Navigate to your project directory.
2. Run `opencode` at the terminal.

This single command launches your Crux session. You'll be dropped into an interactive environment where you can describe what you want to build or fix. Crux will engage with you in natural conversation, propose approaches, write scripts for changes, and guide you through approval and execution.

The first time you run this in a new project, Crux is in learning mode—it's gathering baseline information about your codebase, dependencies, and structure. This takes a few extra seconds but only happens once per project.

### The /init-project Command

When you're starting a truly new project (not adding Crux to an existing one), use the `/init-project` command inside a Crux session. This command scaffolds the project structure Crux needs:

1. Creates a `.crux/` directory where Crux stores session logs, scripts, and project-level knowledge
2. Initializes a `scripts/` library for reusable automation
3. Sets up a `.cruxignore` file (like `.gitignore`) to exclude files from Crux's analysis
4. Creates a `CRUX_CONFIG.md` file where you can document project-specific conventions

After `/init-project` runs, your project is fully Crux-native. All subsequent sessions will be richer because Crux remembers the context from before.

---

## Working with Modes

### What Modes Are and Why They Matter

Modes are Crux's way of specializing. A mode is a distinct operational profile that shapes how Crux thinks, what tools it reaches for, what safety constraints apply, and how aggressively it samples ideas.

Think of modes like switching from "architect" to "debugger" to "documentation writer." Each role has different priorities, different blindspots, and different best practices. Rather than making Crux a generalist that's mediocre at everything, modes let Crux excel at specific tasks.

When you switch to a mode, several things change behind the scenes:

- **Tool access** narrows or expands (debug mode has deeper runtime inspection; infra-architect mode can modify system configs)
- **Sampling parameters** shift (planning modes explore broader solution spaces; execution modes focus narrowly)
- **Safety constraints** adapt (new code scripts get 32B audits; library scripts get lighter-touch reviews)
- **Context priorities** change (in documentation mode, Crux prioritizes user-facing clarity over implementation efficiency)

### How to Switch Modes

Two methods exist, and both are instant:

1. Press **Tab** to cycle through available modes. A menu shows your current mode and the three most recently used modes at the top.
2. Use the command `/mode <name>` (e.g., `/mode debug` or `/mode infra-architect`).

Mode switching is free—it doesn't cost tokens or time. You can switch back and forth as many times per session as you need. Crux preserves context across mode switches, so information you've gathered in one mode is available in another.

### The 15 Modes Reference

**plan** — High-level architecture and design. Use this when you're deciding "what should we build?" before writing any code. Crux explores solution spaces broadly, considers trade-offs, and documents assumptions. Think mode: generates many alternatives; then critique mode: narrows them down.

**debug** — Dig into runtime behavior, failures, and misbehavior. Use when something is broken and you need to understand why. Crux has access to deeper instrumentation, can suggest targeted test cases, and focuses on reproducing issues. High sampling; encourages exploration of edge cases.

**build-py** — Python-focused development. Optimized for writing, testing, and iterating on Python code. Crux understands Python-specific idioms, testing frameworks (pytest, unittest), and common libraries. Scripts audited slightly faster because Python is statically analyzable.

**build-ts** — TypeScript/JavaScript-focused development. Optimized for writing frontend and Node.js code. Crux understands React patterns, async flows, type safety, and common npm packages.

**build-go** — Go development. Optimized for writing concurrent, networked Go code. Crux understands goroutines, interfaces, and the Go standard library deeply.

**build-rust** — Rust development. Optimized for systems programming and memory-safety work. Crux understands ownership, lifetimes, and common crates. High safety constraints because Rust mistakes are often low-level.

**infra-architect** — Infrastructure and deployment. Use when designing or modifying cloud infrastructure, Kubernetes configs, Terraform, Docker setups. Crux can modify system-level configuration with tighter approval gates.

**optimize** — Performance and efficiency work. Use when you're trying to make things faster, smaller, or more resource-efficient. Crux focuses on measurements and benchmarks, proposes targeted changes, and validates improvements.

**security** — Security-focused work. Use when hardening systems, fixing vulnerabilities, or implementing auth/crypto. Crux applies stricter safety gates and prefers well-known patterns over novel solutions.

**docs** — Documentation and knowledge work. Use when writing READMEs, guides, API docs, or training materials. Crux prioritizes clarity for your audience, structures information logically, and suggests examples.

**test** — Testing strategy and test writing. Use when expanding test coverage or designing test architecture. Crux understands coverage gaps and suggests high-ROI test cases.

**refactor** — Code cleanup and simplification. Use when you want to improve structure without changing behavior. Crux focuses on reducing complexity, improving readability, and catching accidental behavior changes.

**review** — Code review and quality gates. Use to review code before merging, analyze pull requests, or spot issues. Crux acts like a thorough code reviewer, looking for logic errors, anti-patterns, and edge cases.

**prototype** — Rapid experimentation and spike work. Use when you're exploring an idea quickly. Crux favors speed and iteration over robustness. Safety constraints loosen slightly because you're in a sandbox.

**research** — Investigation and exploration. Use when learning new libraries, tools, or approaches. Crux gathers information, synthesizes it, and explains trade-offs without immediately pushing for implementation.

### The Think/No-Think Router

Crux has an automatic internal router that decides whether to "think hard" or "move fast" for your current task. You don't configure this—it happens automatically based on your mode and what you're asking.

**Think mode** activates when you're in planning, architecture, or debugging modes, or when you've asked an open-ended question. Crux will take longer but explore more thoroughly, consider edge cases, and generate well-reasoned solutions.

**No-think mode** activates when you're in execution modes (build-py, build-ts, etc.) doing routine work. Crux moves fast, relies on well-established patterns, and prioritizes speed.

You can override this by prefixing commands with `/think` or `/fast`. For example, `/think /mode build-py` will make Crux deliberate carefully even in a fast mode, useful when tackling a tricky problem.

### How Modes Affect Tool Access and Sampling

Each mode has a defined **tool tier** it can reach down to. A developer in `debug` mode might access deep instrumentation and runtime inspection tools. A developer in `docs` mode cannot access those tools because they're not relevant. This isn't a restriction—it's a focus that makes Crux faster and safer by not offering inappropriate tools.

**Sampling** also changes. In planning mode, Crux's temperature is set higher, meaning it will propose more varied solutions. In execution modes, temperature is lower—Crux favors the most likely-to-work approach and avoids wild ideas.

---

## The Scripts-First Architecture

### Why All File Modifications Go Through Scripts

When you ask Crux to change code, it doesn't modify files directly. Instead, Crux writes a **script**—a structured, auditable record of the proposed change. You then review and approve that script before it executes.

This architecture exists for good reasons:

- **Auditability** — Every change to your project is logged and traceable
- **Safety** — Multiple layers of AI review catch mistakes before they happen
- **Reversibility** — Scripts are atomic and can be rolled back cleanly
- **Learning** — The system learns from which scripts succeeded, which failed, and why
- **Reusability** — Good scripts get promoted to your library and reused across sessions

### Reading a Script

A script looks like this (simplified):

```
SCRIPT_ID: py-add-tests-2024-03-05-001
RISK_LEVEL: medium
PURPOSE: Add unit tests for user authentication module
MODE: test

TARGET_FILES:
  - auth.py
  - test_auth.py (new file)

BEFORE_STATE:
  # Current state of affected files (captured for rollback)

CHANGES:
  1. Add TestUserAuth class to test_auth.py with fixtures
  2. Update auth.py to expose mock-friendly interfaces
  3. Run pytest to verify tests pass

VALIDATION:
  - All new tests must pass
  - Coverage increases from 45% to 65%
  - No existing tests should break

APPROVAL_STATUS: pending
```

To read a full script, use `/scripts` to list them, then view one with `/scripts view <script_id>`.

### Risk Classification

Scripts are labeled with risk levels. This determines how strictly they're audited:

**Low** — Changes that are clearly safe. Adding a new test. Updating documentation. Adding a config flag. Low-risk scripts go through a single-pass audit by the 8B model, then execute with your approval.

**Medium** — Changes that modify existing behavior but in well-understood ways. Refactoring a function. Adding a feature in an isolated module. Medium-risk scripts get audited by both the 8B model (for syntax/logic) and the 32B model (for deeper reasoning), then execution requires your approval.

**High** — Changes that could break things if they go wrong. Modifying core architecture. Changing database schemas. Altering security logic. High-risk scripts get full human review (you read it), then staged execution (DRY_RUN first, see the impact, then apply if safe).

You can override the risk level if you have good reason. Use `/scripts adjust-risk <script_id> <new_level>` to change it. But be deliberate about lowering risk classifications—they exist to protect you.

### The Safety Pipeline

When you create a script, it flows through this pipeline:

1. **Preflight** — Syntax check, dependency analysis, file existence verification. Catches obvious errors immediately.

2. **8B Audit** — The smaller model reviews the script for logic errors, anti-patterns, and basic safety issues. Fast, good for catching everyday mistakes.

3. **32B Audit** — Only for medium and high-risk scripts. The larger model does deeper reasoning—checks for subtle bugs, race conditions, or unintended consequences.

4. **Approval** — You review the script (Crux highlights the key changes) and approve or reject. This is the human firewall.

5. **DRY_RUN** — Only for high-risk scripts. The script executes in a sandboxed simulation. You see what would happen before it actually happens.

6. **Execute** — The script runs for real. Changes are applied to your actual files.

Each stage can reject the script. If the 8B audit finds issues, the script is returned to you with suggestions. If you reject it, the script is archived and Crux moves forward with a different approach.

### Transaction Scripts for Multi-File Changes

When a single logical change affects multiple files, Crux creates a **transaction script**—a single atomic unit that changes all of them together or none of them.

Example: refactoring a module name across ten files. Rather than creating ten separate scripts and executing them sequentially (risky if the eighth one fails), Crux writes one transaction script that:

1. Renames the module in `__init__.py`
2. Updates all ten import statements
3. Updates tests
4. Runs verification tests
5. Either succeeds entirely or rolls back everything

If any part fails, the whole transaction rolls back. Your codebase never ends up in a partially-broken state.

### Promoting Scripts to Your Library

When you have a script that works well and you know you'll use it again, promote it:

1. Run `/promote <script_id>` while viewing the script.
2. Crux will ask you to name it (e.g., `add-python-tests`, `update-deps`) and optionally add a description.
3. The script is copied to your `.crux/scripts/` library.

Next time you're working on a similar task, Crux will recognize the pattern and suggest using the library script. You can also manually invoke library scripts with `/scripts run <name>`.

Library scripts are project-specific. They live in your `.crux/` directory and are version-controlled with your project. After three projects use a library script successfully, consider contributing it to the public Crux repository (`/review-community`).

### Finding Existing Scripts

Use `/scripts` to:

- **List all** — Shows all scripts from this session and previous sessions
- **View** — `/scripts view <id>` to read a full script
- **Search** — `/scripts search <keyword>` to find scripts by purpose
- **Run** — `/scripts run <library_name>` to execute a library script

Scripts are kept for 30 days by default, then archived. You can keep important ones forever with `/scripts keep <id>`.

---

## The Tool Hierarchy

### Six Tiers Explained

Crux accesses tools in a strict hierarchy. The system prefers high-tier tools (most reliable, most auditable) and only reaches for lower tiers when necessary. This hierarchy is:

1. **LSP** (Language Server Protocol) — IDE-like static analysis, symbol navigation, refactoring suggestions. Highly reliable because it's built into your IDE/editor stack. Crux reaches for this first for any code understanding task.

2. **Custom Tools** — Project-specific tools you've built and registered with Crux. These are hyper-reliable because they're created specifically for your codebase. Example: a custom script that validates your API contract, or a tool that runs your project's custom test suite.

3. **MCP** (Model Context Protocol) — Standardized integrations with external services and tools. These are well-tested, maintained by the community. Examples: GitHub CLI integration, database query tools, API clients.

4. **Library Scripts** — The scripts you've promoted and reused. Highly auditable because they've succeeded before in your project.

5. **New Scripts** — Scripts Crux generates on the fly for one-off changes. These go through the full safety pipeline (audits, approval, dry-run).

6. **Raw Bash** — Direct shell commands. Crux avoids this by default because it's the least auditable. Only used when no higher tier is available and you explicitly approve it.

Why this hierarchy? Reliability and auditability. Each step down the hierarchy is less checkable and more risky. By preferring high tiers, Crux maximizes the chance of success and minimizes surprises.

### Why the Hierarchy Matters

Consider a simple task: "run all tests." Crux's approach:

1. **Try LSP first** — Is there a test runner symbol in the codebase? Can it be invoked directly?
2. **Try custom tools** — Do you have a project-specific test command registered?
3. **Try MCP** — Is there a standard test runner integration available?
4. **Generate a new script** — If none of the above work, write a script that discovers and runs tests.

You don't have to think about this. It happens automatically. The benefit is that Crux solves your problem using the most reliable available method.

### How the System Enforces Tier Preference

When you ask Crux to do something, it internally debates which tool tier to use. This is logged and visible in `/stats` (daily analytics). If Crux is consistently reaching for tier 6 (raw bash) when tier 2 (custom tools) would work, that's a sign you should register a custom tool or promote a library script.

The system will even suggest this in your daily digest: "You've created five similar scripts in the last week. Consider promoting one to your library."

---

## The Knowledge Base

### How Knowledge Entries Are Created

You don't manually write knowledge entries. They emerge organically from your workflow.

Here's how: When you correct Crux (you point out a mistake, you clarify an assumption, you explain why your approach is better), Crux captures that correction as a potential **knowledge entry**. These corrections are like lessons learned. Over time, they build up.

Example: You're working in debug mode. Crux suggests using `print()` for debugging. You say, "Actually, in this codebase we use the logging module with DEBUG level—it integrates with our observability system." Crux learns from this and stores it as knowledge: "In this project, use logging.DEBUG over print()."

### Three Levels of Knowledge

**Project-level** — Specific to this project. Lives in `.crux/knowledge/`. Examples: "We use logging, not print"; "All database queries must use the ORM, never raw SQL"; "Test files always go in `/tests/` alongside source."

**User-level** — Specific to you across all projects. Lives in `~/.crux/knowledge/`. Examples: "I prefer async/await over callbacks"; "Always add type hints to Python"; "I want all scripts to run in dry-run mode by default."

**Public** — Contributed to the Crux ecosystem and available to all users. Examples: "Common gotchas when using React hooks"; "Terraform best practices for AWS"; "How to debug CircleCI builds."

### Reviewing Knowledge Promotion Candidates

Every day, Crux identifies which corrections could become permanent, reusable knowledge. Use `/review-knowledge` to see candidates:

```
CANDIDATES FOR PROMOTION:

1. "Use logging.DEBUG over print()" (project-level)
   - Suggested 3 times in last 7 days
   - Applied in 4 different sessions
   - Confidence: high
   → Promote to project knowledge? (Y/n)

2. "Add type hints to all functions" (user-level)
   - Suggested 8 times across 2 projects in last month
   - Consistency: 95%
   → Promote to user knowledge? (Y/n)
```

Promoting is instant. Once promoted, that knowledge is folded into Crux's decision-making and suggestions for the future.

### How the Daily Digest Surfaces Gaps

Your daily digest (see below) includes a "Knowledge Gaps" section. These are patterns Crux detected where it seemed to be missing information. Examples:

- "You corrected me 3 times about authentication patterns this week. Is there project-specific auth knowledge I should learn?"
- "I see you consistently prefer approach X over approach Y for this type of problem. Should I make that a preference?"

These aren't errors—they're Crux asking "should I learn this?" You can dismiss them or accept them and fold them into knowledge.

---

## Session Logging and Recovery

### What Gets Logged

Every session is logged in JSONL format (one JSON record per line) in `.crux/logs/`. Each record captures:

- Timestamp
- Mode
- Your input
- Crux's response
- Scripts created
- Knowledge corrections applied
- Tools used
- Execution results

This log is how Crux remembers conversations across sessions and how it understands your patterns over time.

Logs are retained for 90 days by default. Archive older logs with `/log archive`.

### Crash Recovery

If your session crashes (network failure, power loss, terminal closes), don't worry. When you run `opencode` again, Crux automatically:

1. Detects there's an incomplete session
2. Reads the last log entry
3. Reconstructs the context up to the crash point
4. Shows you what was happening and asks: "Continue from where we left off, or start fresh?"

If you choose to continue, Crux is right back where you were. Any pending scripts aren't lost—they're still there in your scripts list.

### The Resume Mechanism

When you resume a session, Crux loads:

- The full conversation history from the previous session
- All pending scripts and their approval status
- The current mode
- The current project context

This means you can stop working on something, close your terminal, come back tomorrow, and pick up exactly where you left off. No context loss.

### The Continuous Background Processor

Crux runs a lightweight background process (if you opt into it during setup) that:

- Watches your codebase for changes
- Updates Crux's understanding of your project automatically
- Generates the daily digest while you sleep
- Surfaces urgent issues (test failures, warnings) in your next session

This is optional. If you disable it, digests are generated on-demand when you ask.

---

## The Daily Digest

### What It Contains

Every day (or on-demand with `/digest`), Crux generates a summary:

**Correction Rate** — How many times you corrected Crux this week, grouped by type. Example: "3 corrections about testing patterns, 2 about code style, 1 about architecture." Trending up? You're teaching Crux. Trending down? Either Crux is learning or you're in a comfortable domain.

**Promotion Candidates** — Knowledge entries ready to graduate, scripts ready to be promoted to your library, modes that might help you.

**Mode Drift** — If you've been in the same mode for hours doing diverse work, Crux will suggest: "You've been in build-py for 4 hours working on testing, DevOps, and docs. Consider switching modes to specialize?"

**Tool Usage** — Which tool tiers you're using. Spending a lot of time in tier 6 (raw bash)? Crux suggests registering a custom tool.

**Learning Opportunities** — Patterns Crux noticed where you solved something in a non-obvious way. Example: "I saw you use a generator expression instead of a list comprehension here for memory efficiency. That's clever—should I learn that as a preference?"

**Community Contributions** — If you've enabled it, Crux flags scripts or knowledge entries that could benefit other users and might be worth contributing.

### How to Read and Act On Recommendations

The digest is **not a todo list**. It's a report. Skim it. Most items are informational. Act on the ones that resonate:

- "Knowledge ready to promote?" — Promote the ones that feel right.
- "Mode drift detected?" — If you feel the suggestion is valid, switch modes. If you're happy where you are, ignore it.
- "Promotion candidates?" — Promote scripts that worked well. Leave the rest alone.

### Escalation — What Happens When You Ignore Recommendations

Nothing happens automatically. Recommendations are suggestions, not mandates. However, if you consistently ignore similar recommendations (e.g., you ignore "promote this script" five times in a row, and similar scripts pile up), the digest will escalate: "Multiple promotion candidates have accumulated. Your library might benefit from organization."

At that point, Crux is just being helpful: "Hey, I've noticed a pattern. Would now be a good time to review your library?"

---

## Model Management

### Available vs Assigned Models

During setup, Crux detected which models you have available locally via Ollama. You have one **assigned model**—the model Crux uses by default. You can also have fallback models.

View your setup with `/models`:

```
ASSIGNED: mistral-7b (fast, good at coding)
FALLBACK: neural-chat-7b (better at reasoning)
AVAILABLE: mistral-7b, neural-chat-7b, llama2-13b, mistral-8x7b

Current session: mistral-7b
```

### How to Switch Models Mid-Session

Use `/models switch <model_name>` to swap models instantly. Your context carries over. This is useful when:

- The current model is struggling with a problem (switch to a stronger model temporarily)
- You want to compare approaches (run the same prompt in two models)
- You're in a fast mode but need to think hard (switch to a more capable model)

Switching costs nothing except the time to load the new model into memory.

### How the System Auto-Evaluates New Models

If you install a new model in Ollama (e.g., `ollama pull mixtral`), Crux detects it and automatically evaluates it:

1. Runs it on your recent prompts and compares outputs
2. Benchmarks speed, quality, and token usage
3. Reports results in your next digest: "New model 'mixtral' is available. It's 30% faster than your current model on coding tasks, but 20% less accurate on reasoning. Try it with `/models switch mixtral`?"

### Cloud API Fallback

If a local model struggles or crashes, Crux can fall back to a cloud API (e.g., OpenAI's API). This requires you to set it up:

1. Run `/configure-api openai <your-api-key>` (your key is stored securely)
2. Crux now has a safety net. If local models fail, it can reach for cloud models.

This only happens if you explicitly enable it and local models are unavailable. It's not default behavior.

### The Model Registry

All your models and their performance characteristics are tracked in `.crux/models/registry.json`. This is how Crux learns which model is best for which type of task over time.

---

## Mode Handoffs

### When and Why to Hand Off Between Modes

Sometimes you start in one mode but realize mid-task that a different mode is better. Handoffs exist for this.

Example: You're in `build-py` writing tests. Midway through, you realize the test strategy is flawed and you need to step back and plan. Use `/handoff plan` to switch modes with full context preservation.

Handoffs are free and instant. They're just mode switches with explicit context carry-over.

### How the Handoff Preserves Context

When you handoff, Crux:

1. Captures the current conversation and scripts
2. Summarizes key decisions and context
3. Switches to the new mode
4. Injects the summary so the new mode understands what happened

Example: You're in `build-py` and handoff to `debug`. Crux will tell the debug mode: "You were writing tests for the auth module. A test is failing because of unexpected behavior in the login function. Here's what we know so far..." and provides the relevant code snippets.

### Common Handoff Patterns

**build-py ↔ debug** — You're writing code, something breaks, you need to debug. Handoff to debug. Once fixed, handoff back to build-py.

**plan ↔ infra-architect** — You're planning features and realize it affects infrastructure. Handoff to infra-architect to design that layer, then back to plan.

**build-ts ↔ optimize** — You've built a feature, it's slow. Handoff to optimize to profile and improve. The optimize mode has different tools for performance work.

**any mode ↔ review** — At any point, handoff to review mode for a code review. It will review everything you've done so far and flag issues.

---

## Custom Commands Reference

**/promote**

Promote the current script to your library. Crux asks for a name and optional description. The script is copied to `.crux/scripts/` and becomes available for reuse.

```
/promote
→ Name this script: add-python-fixtures
→ Description (optional): Adds pytest fixtures for common test patterns
→ Promoted! Use `/scripts run add-python-fixtures` to run it again.
```

**/scripts**

Manage your script library and history.

```
/scripts                    # List all scripts
/scripts view <id>          # View full script
/scripts search <keyword>   # Search by purpose
/scripts run <name>         # Run a library script
/scripts keep <id>          # Mark script to keep forever (don't auto-archive)
/scripts adjust-risk <id> <level>  # Change risk classification
```

**/archive**

Auto-archive old scripts. By default, scripts older than 30 days are archived. You can adjust this:

```
/archive                    # Archive scripts older than 30 days
/archive 7                  # Archive scripts older than 7 days
/archive list               # List archived scripts
```

**/log**

Manage session logs.

```
/log                        # Show current session log stats
/log view <date>            # View logs from a specific date
/log archive                # Archive old logs (older than 90 days)
/log export <format>        # Export logs (json, csv)
```

**/init-project**

Initialize a new project with Crux structure. Run this once when starting a new project:

```
/init-project
→ Project initialized. Created .crux/, scripts/, and .cruxignore.
→ Edit CRUX_CONFIG.md to document project conventions.
```

**/stats**

View on-demand analytics about your session and usage patterns.

```
/stats                      # Summary for this session
/stats all                   # Summary across all sessions
/stats tool-usage           # Breakdown of tool tier usage
/stats mode-time            # How much time in each mode
```

**/digest**

View the daily digest on-demand.

```
/digest                     # Generate and display digest for today
/digest yesterday            # Digest from yesterday
```

**/propose-mode**

Propose a new custom mode based on your usage patterns. If Crux detects you consistently doing work that doesn't fit the 15 standard modes, it suggests creating a custom one.

```
/propose-mode
→ I've noticed you spend 30% of your time on infrastructure work that's not pure DevOps.
   Suggest creating a "platform-eng" mode? (Y/n)
```

**/review-knowledge**

Review and promote knowledge entries.

```
/review-knowledge           # Show candidates for promotion
/review-knowledge promote <id>  # Manually promote one
```

**/review-community**

If you've enabled community contributions, review scripts and knowledge that could be shared.

```
/review-community           # Show contribution candidates
/review-community submit <id>   # Submit to community repo
```

**/configure-api**

Add or update API keys for cloud services (cloud LLM fallback, external integrations).

```
/configure-api openai <key>      # Add OpenAI API key
/configure-api list              # List configured APIs
```

**/mode**

Switch modes explicitly.

```
/mode plan                   # Switch to plan mode
/mode debug                  # Switch to debug mode
/mode build-py              # Switch to Python build mode
```

---

## Continuous Improvement

### The Five Levels of Learning

Crux improves through five cascading levels:

**Level 1: Interaction** — Within a single session, Crux learns from your corrections. You correct a suggestion, Crux immediately adjusts its next suggestions in that session.

**Level 2: Session** — Crux logs your entire session and builds internal knowledge about your preferences. Next time you start a session, it remembers your patterns from before.

**Level 3: Cross-session** — Knowledge gets promoted from corrections into permanent project-level knowledge. Future sessions use this knowledge immediately.

**Level 4: Cross-project** — User-level knowledge (your preferences) transfer across projects. The same knowledge applies to every project you work on.

**Level 5: Ecosystem** — When you contribute scripts or knowledge to the public Crux repository, other users benefit. And improvements from other users' contributions flow back to you.

Most of this happens automatically. You just work naturally, correct Crux when needed, and promote what works.

### How Corrections Become Knowledge

1. You correct Crux: "Actually, we use X instead of Y here."
2. Crux logs the correction and stores it as a candidate entry.
3. The correction is applied to the current session immediately (Level 1).
4. Over the next week, if the same correction applies multiple times, it becomes a promotion candidate (Level 2-3).
5. You review it in `/review-knowledge` and promote it (Level 3).
6. Now it's permanent project knowledge.

### How Knowledge Becomes Shared

Once you've built strong project knowledge, you can share it:

1. Use `/review-community` to see what knowledge might help others.
2. Submit candidates with `/review-community submit <id>`.
3. The contribution goes to the public Crux repository.
4. Other users can discover and adopt it.
5. Contributions are attributed to you and your project.

### How Modes Evolve Over Time

The 15 standard modes are good baselines. But over time, Crux might detect that you work differently. Example: You consistently mix infrastructure work with security concerns. Crux suggests a custom mode called "secure-infra."

You can create custom modes with `/propose-mode`, and they become available immediately. Custom modes have the same flexibility as standard modes—Crux will tailor tool access, sampling, and safety constraints to your specialized mode.

### Contributing Back to the Public Repo

If you create a particularly useful script, knowledge entry, or custom mode that you think benefits others, contribute it:

1. Use `/review-community` to prepare your contribution.
2. Submit with `/review-community submit <id>`.
3. Your contribution is reviewed by the community and added to the public repo if accepted.
4. You get attribution, and other users benefit.

---

## Tips for Maximum Effectiveness

**Let the system learn.** Don't try to pre-emptively teach Crux everything. Just correct it naturally when it's wrong, and the infrastructure captures those corrections. Natural corrections are richer than manual documentation because they include context.

**Use modes intentionally.** Switching modes is free. Don't work in `plan` mode when you should be in `build-py`. Wrong-mode work wastes tokens because Crux has to work against its specialization. Switch often—it's a feature, not a bug.

**Check the daily digest.** Takes 30 seconds. It tells you where the system is improving, what knowledge is ready to promote, and where you might be missing tools or modes. Use it as a guide, not a checklist.

**Trust the safety pipeline.** The more you use the scripts-first architecture and let Crux write and audit changes, the safer your workflow becomes. Direct you raw bash commands are riskier. Use scripts.

**Promote what works.** When you write a script that solves a problem well, promote it to your library. When you learn something about your project that should stick around, promote it to knowledge. These aren't optional—they're how the system multiplies your effectiveness across sessions.

**Mode handoffs are free.** Realize midway you're in the wrong mode? Handoff instantly. No penalty, no context loss. Keep mode specialization tight.

**Read your scripts before approving.** The safety pipeline catches most issues, but review scripts still matters. Scan them. If something looks odd, reject it and ask Crux to try again.

**Experiment in prototype mode.** When exploring new ideas, switch to `prototype` mode. Constraints loosen, Crux moves faster, and you're not worried about breaking things. Once the spike works, move to production modes.

---

## Closing

Crux is built around a simple philosophy: **AI works best when it specializes, learns from feedback, and operates in ways that are safe and auditable.**

You just installed it. Start a session, describe what you want to build, and let the system guide you. Correct it when needed. Switch modes when appropriate. Promote what works. Check the digest occasionally.

Within a few days, you'll notice the system working better—making fewer mistakes, understanding your codebase more deeply, and operating faster. Within a week, you'll have built up project knowledge and library scripts that accelerate your work dramatically.

That's Crux. Welcome aboard.

---

**For support, file issues at:** [Crux Repository]

**For community scripts and knowledge:** Run `/review-community` to explore public contributions.

**For performance questions:** Run `/stats` to understand your own usage patterns and where the system is spending tokens.
