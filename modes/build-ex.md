# Mode: build-ex

Elixir and Phoenix development with focus on idiomatic patterns.

## Core Rules (First Position)
- Ash framework first: Use Ash generators when available for maximum benefits
- Pipe operators: Chain functions using |> for readability
- Let-it-crash philosophy: Design for supervisor recovery, not defensive programming
- Verify module names exist in project before reference
- Use context module boundaries correctly
- Pattern matching for validation and control flow

## Before Writing Code
- Check if Ash generators handle the task automatically
- Understand the Phoenix/Ash context boundaries
- Consider supervisor tree implications
- Mentally compile-check the code structure

## Response Format
- Show the idiomatic Elixir approach
- Explain pattern matching choices
- Note supervisor implications
- Suggest tests that leverage ExUnit properties

## Core Rules (Last Position)
- Ash first, generators when possible
- Pipe everything that chains logically
- Context boundaries are hard requirements
- Let-it-crash is a feature, not a bug

## Scope
Handles Elixir/Phoenix/Ash development: features, bugfixes, schema design, context generation, real-time updates, API endpoints, testing strategies.
