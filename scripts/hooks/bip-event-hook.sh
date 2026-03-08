#!/usr/bin/env bash
# BIP High-Signal Event Hook
# Part of PLAN-314: Wire Claude Code hooks to fire BIP triggers
#
# Hooks: PostToolUse, Stop
# Detects: test_green, pr_merge, new_mcp_tool, plan_implemented
#
# Usage: Called by Claude Code hooks with context in environment variables

set -euo pipefail

# Find the project's .crux/bip directory
find_bip_dir() {
    local check_path="${PWD}"
    while [[ "$check_path" != "/" && "$check_path" != "$HOME" ]]; do
        if [[ -d "$check_path/.crux/bip" ]]; then
            echo "$check_path/.crux/bip"
            return 0
        fi
        check_path=$(dirname "$check_path")
    done
    return 1
}

BIP_DIR=$(find_bip_dir 2>/dev/null) || exit 0
CRUX_HOME="${HOME}/.crux"
PYTHON="${CRUX_HOME}/.venv/bin/python"

# Get hook context from environment
TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
TOOL_OUTPUT="${CLAUDE_TOOL_OUTPUT:-}"
HOOK_TYPE="${CLAUDE_HOOK_TYPE:-PostToolUse}"

# Event detection functions
detect_test_green() {
    # Check if tool output indicates passing tests
    if [[ "$TOOL_NAME" == "Bash" ]]; then
        if echo "$TOOL_OUTPUT" | grep -qE '(passed|OK|PASSED|✓.*test|tests passed)'; then
            if ! echo "$TOOL_OUTPUT" | grep -qE '(failed|FAILED|ERROR|error)'; then
                echo "test_green"
                return 0
            fi
        fi
    fi
    return 1
}

detect_pr_merge() {
    if [[ "$TOOL_NAME" == "Bash" ]]; then
        if echo "$TOOL_OUTPUT" | grep -qE '(merged.*pull|Pull request.*merged|Merge pull request)'; then
            echo "pr_merge"
            return 0
        fi
    fi
    return 1
}

detect_new_mcp_tool() {
    if [[ "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "Edit" ]]; then
        if echo "$TOOL_OUTPUT" | grep -qE '(mcp.*tool|MCP.*tool|def.*mcp_)'; then
            echo "new_mcp_tool"
            return 0
        fi
    fi
    return 1
}

detect_plan_implemented() {
    if [[ "$TOOL_NAME" == "Bash" ]]; then
        if echo "$TOOL_OUTPUT" | grep -qE "(UPDATE.*status.*implemented|plan.*implemented|PLAN-[0-9]+.*implemented)"; then
            echo "plan_implemented"
            return 0
        fi
    fi
    return 1
}

# Main detection
EVENT=""
EVENT=$(detect_test_green) || \
EVENT=$(detect_pr_merge) || \
EVENT=$(detect_new_mcp_tool) || \
EVENT=$(detect_plan_implemented) || \
true

if [[ -n "$EVENT" ]]; then
    # Fire BIP trigger via Python
    PYTHONPATH="${CRUX_HOME}" "$PYTHON" -c "
from scripts.lib.crux_bip_triggers import evaluate_triggers
from scripts.lib.crux_bip import get_escalation_action, load_config
import json

bip_dir = '$BIP_DIR'
event = '$EVENT'

config = load_config(bip_dir)
result = evaluate_triggers(bip_dir, event=event)
action = get_escalation_action(event, config)

if result.should_trigger:
    output = {
        'event': event,
        'should_trigger': True,
        'reason': result.reason,
        'action': action,
    }
    # Log the trigger
    import os
    log_path = os.path.join(bip_dir, 'events.jsonl')
    with open(log_path, 'a') as f:
        import datetime
        output['timestamp'] = datetime.datetime.now().isoformat()
        f.write(json.dumps(output) + '\n')
    print(json.dumps(output))
" 2>/dev/null || true
fi
