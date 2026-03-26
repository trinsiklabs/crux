# BUILD_PLAN_010: Multi-Model Routing — Intelligent Model Selection

**Created:** 2026-03-26
**Status:** ALREADY IMPLEMENTED — existing model tier system (crux_model_tiers.py, crux_model_quality.py, crux_audit_backend.py) covers Phases 1-4. MCP tools get_model_for_task, get_mode_model, get_available_tiers, get_model_quality_stats already operational.
**Priority:** SHOULD-CLOSE
**Competitive Gap:** Aider supports multi-model (architect+editor pattern). Crux has model tier infrastructure (PLAN-169/182) but no intelligent routing that selects the best model per task.
**Goal:** Crux recommends and routes to the optimal model for each task based on mode, task type, and quality history. Works across any provider (Ollama, Anthropic, OpenAI, OpenRouter).

**Constraint:** TDD, 100% coverage on new code.
**Constraint:** Build on existing crux_audit_backend.py tier system.
**Rule:** Two consecutive clean audit passes = convergence.

## Why This Matters

Crux already has: model tiers (micro/fast/local/standard/frontier), quality feedback tracking, and per-task model recommendations. What's missing is the routing layer that automatically selects and suggests models based on context — "you're in debug mode, this is a hard problem, use frontier tier" vs "you're writing tests, use fast tier."

## Architecture

```
User request → Crux determines:
  1. Current mode (build-py, debug, security, etc.)
  2. Task complexity (simple edit vs architecture decision)
  3. Quality history (has this model failed this task type before?)
  4. Available models (what's running locally + API keys)

  → Routes to best model
  → Falls back if primary fails
  → Records quality outcome for learning
```

---

## Phase 1: Model Discovery

- [ ] 1.1 Create `scripts/lib/crux_model_router.py`
- [ ] 1.2 `discover_models()` → `list[ModelInfo]` — scan Ollama, check API keys, detect available models
- [ ] 1.3 `ModelInfo` dataclass: id, provider, tier, capabilities (reasoning, tool_call, context_limit)
- [ ] 1.4 Cache discovery results (refresh on request or every N minutes)
- [ ] 1.5 Tests for discovery (Ollama running, not running, API keys present/absent)

## Phase 2: Routing Rules

- [ ] 2.1 `get_recommended_model(mode, task_type, complexity)` → `ModelInfo` — rule-based selection
- [ ] 2.2 Mode → tier mapping: think modes → standard+, no_think modes → fast+
- [ ] 2.3 Task type → tier: code_audit → standard, simple_edit → fast, security_review → frontier
- [ ] 2.4 Quality history override: if model X has <70% success on task Y, escalate tier
- [ ] 2.5 Tests for routing rules across modes and task types

## Phase 3: MCP Tools Enhancement

- [ ] 3.1 Enhance existing `get_model_for_task` to use routing rules
- [ ] 3.2 Enhance existing `get_mode_model` to factor in quality history
- [ ] 3.3 New tool: `suggest_model(prompt_preview)` — analyze prompt and suggest model
- [ ] 3.4 New tool: `model_report()` — show available models, quality stats, routing table
- [ ] 3.5 Tests for enhanced tools

## Phase 4: Quality Feedback Loop

- [ ] 4.1 `record_outcome(model, task_type, success, latency)` — log quality data
- [ ] 4.2 Quality stats per model per task type (success rate, avg latency)
- [ ] 4.3 Auto-escalation: when success rate drops below threshold, recommend higher tier
- [ ] 4.4 Monthly quality report in daily digest
- [ ] 4.5 Tests for feedback and escalation

---

## Convergence Criteria

- Model discovery finds all available models (local + API)
- Routing recommends optimal model per mode + task type
- Quality history influences recommendations
- Works with existing tier system (no breaking changes)
- Two consecutive clean audit passes
