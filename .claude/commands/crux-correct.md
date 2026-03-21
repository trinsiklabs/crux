# /crux-correct — Log a correction for continuous learning

Log a correction when something went wrong — Crux learns from these to avoid repeating mistakes.

## Arguments

$ARGUMENTS = description of what went wrong and what the fix was

## Protocol

Call `log_correction(description=$ARGUMENTS)`.

If $ARGUMENTS is vague, ask the user to clarify:
- What was the error or bad output?
- What was the correct behavior?
- What caused the mistake?

### Examples

```
/crux-correct Used unittest.mock instead of dependency injection — tests were brittle
/crux-correct Generated SQL without parameterized queries — security risk
/crux-correct Assumed Python 3.12 features available but project uses 3.11
```

Corrections feed into Crux's knowledge system and influence future mode prompts.
