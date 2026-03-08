# PLAN-329: Freight train auto-disable when plan group fully implemented

**Status:** planned
**Group:** GROUP-OPS
**Domain:** key
**Risk:** 0.20

## Summary

When freight train mode is activated for a plan group (e.g., GROUP-MKT), automatically disable it when all plans in that group reach "implemented" status. Prevents runaway autonomy after completing the intended work.

## Problem

Currently, freight train mode stays active until manually cleared. This creates risk:
1. User grants autonomy for GROUP-MKT plans
2. All GROUP-MKT plans get implemented
3. Freight train mode remains active for unrelated work
4. AI acts autonomously on things user didn't intend to grant blanket approval for

## Solution

### Track Mandate Scope

When freight train mode is activated, record:
- Timestamp of activation
- Scope (plan group, plan IDs, or "blanket")
- Session ID

### Auto-Disable Trigger

After marking a plan as implemented, check:
1. Is freight train mode active?
2. What's the scope of the mandate?
3. If scoped to a group: are all plans in that group now implemented?
4. If yes: clear the mandate and log the auto-disable

### Implementation

Add to the post-implement hook or plan status update trigger:

```python
def check_mandate_completion():
    mandate = get_active_mandate()
    if not mandate:
        return

    if mandate.scope_type == "group":
        group = mandate.scope_value
        remaining = count_plans_in_group(group, status="planned")
        if remaining == 0:
            clear_mandate(mandate.id)
            log(f"MANDATE AUTO-DISABLED: {mandate.scope_value} fully implemented")
```

## Affected Files

- `/home/key/ops/hooks/freight_train_mandate.py` (or equivalent)
- PostgreSQL trigger on entries table (plan status updates)
- Onelist logging for audit trail

## Success Criteria

- [ ] Mandate auto-clears when scoped group is fully implemented
- [ ] Audit log shows auto-disable with reason
- [ ] Blanket mandates are NOT auto-cleared (require explicit clear)
- [ ] Per-plan mandates clear when that specific plan is implemented
