# Mode Template Guide

## Mode Creation Methodology

Modes are specialized personas that shape how Claude approaches different tasks. When creating modes:

- Use **positive instructions only**: State what to do, not what to avoid
- Create a **simple, task-relevant persona**: Avoid elaborate backstories or role-play elements
- Place **critical rules in prime positions**: First section and last section (recency and primacy effects)
- Target **150-200 words**: Concise enough to fit in context, complete enough to be effective
- Focus on **actionable specifics**: Concrete practices over philosophy

---

# Mode: [name]

[One-line description of what this mode does]

## Core Rules (First Position)
- [Rule 1: Most important constraint or principle]
- [Rule 2]
- [Rule 3]
- [Rule 4]
- [Rule 5]
- [Rule 6]

## Before [Action] / Methodology
- [Preparatory step or question 1]
- [Preparatory step or question 2]
- [Preparatory step or question 3]
- [Preparatory step or question 4]

## Response Format
- [First element of response]
- [Second element]
- [Third element]
- [Fourth element]
- [Fifth element]
- [Sixth element]

## Core Rules (Last Position)
- [Rule A: Reinforce most critical constraint]
- [Rule B]
- [Rule C]
- [Rule D]
- [Rule E]

## Scope
Handles [topic 1], [topic 2], [topic 3], [topic 4], [topic 5], [topic 6].

---

## Structure Explanation

**Core Rules (First Position)** - These come first to anchor Claude's thinking before any other context. Include the 3-5 most important constraints or principles specific to this mode.

**Before [Action] / Methodology** - This section helps Claude think through the problem space before responding. Use questions or preparation steps that ensure good reasoning.

**Response Format** - Specifies the structure Claude should use when responding. This ensures consistency and completeness.

**Core Rules (Last Position)** - These come last for recency effect, reinforcing the most critical rules. Often reframes earlier rules or adds fail-safe constraints.

**Scope** - Defines what this mode handles and what it doesn't (by exclusion).

## Word Count Target

Aim for 150-200 total words in the mode (excluding this template guidance). This fits comfortably in context windows while providing specific enough guidance to be useful.

## Key Principles

1. **Positive framing**: "Do X" not "Don't do Y"
2. **Specificity**: "Use parameterized queries" not "Be secure"
3. **Actionability**: Instruction should guide immediate behavior
4. **Task-focused**: Mode shapes behavior, not personality
5. **Constraint-heavy**: Rules more than stories
