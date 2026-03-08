"""Threshold-triggered background processor for continuous learning.

Checks data thresholds and runs processors (correction extraction,
digest generation, mode auditing) only when thresholds are exceeded.

Security improvements (PLAN-166):
- Atomic state file writes to prevent race conditions
- Rate limiting and cooldown for processors
- Timestamp validation within reasonable range
- Sanitized error messages in status
- Configurable timeout for processor execution
- Structured audit logging
- Validated import sources (allowlist)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from scripts.lib.crux_paths import get_project_paths

# Configure structured logging
_logger = logging.getLogger("crux.background_processor")

# Maximum timestamp drift allowed (in days)
_MAX_TIMESTAMP_DRIFT_DAYS = 30

# Minimum cooldown between processor runs (in seconds)
_DEFAULT_COOLDOWN_SECONDS = 60

# Default timeout for processor execution (in seconds)
_DEFAULT_TIMEOUT_SECONDS = 30

# Allowlist of valid processor modules (prevents arbitrary code execution)
_ALLOWED_PROCESSOR_MODULES = frozenset([
    "scripts.lib.extract_corrections",
    "scripts.lib.generate_digest",
    "scripts.lib.audit_modes",
    "scripts.lib.crux_paths",
    "scripts.lib.crux_bip",
    "scripts.lib.crux_bip_triggers",
    "scripts.lib.crux_bip_gather",
    "scripts.lib.crux_bip_publish",
])


class ProcessorTimeoutError(Exception):
    """Raised when a processor exceeds its timeout."""
    pass


def _timeout_handler(signum: int, frame: Any) -> None:
    raise ProcessorTimeoutError("Processor execution timed out")


@dataclass
class ProcessorConfig:
    correction_queue_size: int = 10
    interaction_count: int = 50
    digest_age_hours: int = 24
    cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    rate_limit_per_hour: int = 10  # Max processor runs per hour


@dataclass
class RateLimitState:
    """Track rate limiting for processor runs."""
    runs_this_hour: int = 0
    hour_start: str = ""


def _load_processor_state(project_dir: str) -> dict:
    """Load processor state with validation."""
    state_path = os.path.join(project_dir, ".crux", "analytics", "processor_state.json")
    try:
        with open(state_path) as f:
            state = json.load(f)
        # Validate structure
        if not isinstance(state, dict):
            _logger.warning("Invalid processor state format, resetting")
            return {}
        return state
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        _logger.warning("Corrupt processor state file: %s", _sanitize_error(str(e)))
        return {}


def _save_processor_state(project_dir: str, state: dict) -> None:
    """Save processor state atomically to prevent race conditions.

    Writes to a temp file first, then atomically renames to prevent
    partial writes from corrupting the state file.
    """
    state_dir = os.path.join(project_dir, ".crux", "analytics")
    os.makedirs(state_dir, exist_ok=True)

    final_path = os.path.join(state_dir, "processor_state.json")

    # Write to temp file first, then atomic rename
    fd, temp_path = tempfile.mkstemp(dir=state_dir, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        # Atomic rename (on POSIX systems)
        os.replace(temp_path, final_path)
        _logger.debug("Saved processor state atomically")
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_error(error_msg: str) -> str:
    """Sanitize error messages to prevent sensitive data leakage.

    Removes file paths, stack traces, and other potentially sensitive info.
    """
    # Remove file paths
    sanitized = error_msg
    # Remove anything that looks like a path
    import re
    sanitized = re.sub(r'/[^\s:]+', '[PATH]', sanitized)
    # Remove potential credentials/keys
    sanitized = re.sub(r'(key|password|secret|token|api)[=:]\S+', r'\1=[REDACTED]', sanitized, flags=re.IGNORECASE)
    # Truncate to reasonable length
    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."
    return sanitized


def _validate_timestamp(iso_timestamp: str) -> bool:
    """Validate that a timestamp is within reasonable range.

    Rejects timestamps that are too far in the past or future.
    """
    try:
        ts = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        drift = abs((now - ts).days)
        return drift <= _MAX_TIMESTAMP_DRIFT_DAYS
    except (ValueError, TypeError):
        return False


def _count_corrections(project_dir: str) -> int:
    corr_file = os.path.join(project_dir, ".crux", "corrections", "corrections.jsonl")
    if not os.path.exists(corr_file):
        return 0
    count = 0
    with open(corr_file) as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _count_todays_interactions(project_dir: str) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    int_file = os.path.join(project_dir, ".crux", "analytics", "interactions", f"{today}.jsonl")
    if not os.path.exists(int_file):
        return 0
    count = 0
    with open(int_file) as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _hours_since(iso_timestamp: str) -> float:
    """Calculate hours since a timestamp, with validation."""
    if not _validate_timestamp(iso_timestamp):
        _logger.warning("Invalid or out-of-range timestamp: %s", iso_timestamp[:30] if iso_timestamp else "empty")
        return float("inf")

    try:
        ts = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    except (ValueError, TypeError):
        return float("inf")


def _check_cooldown(state: dict, processor_name: str, cooldown_seconds: int) -> bool:
    """Check if enough time has passed since the last run of a processor.

    Returns True if cooldown has passed (OK to run), False otherwise.
    """
    last_key = f"last_{processor_name}"
    last_run = state.get(last_key, "")

    if not last_run:
        return True

    if not _validate_timestamp(last_run):
        return True  # Invalid timestamp, allow run

    try:
        ts = datetime.strptime(last_run, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - ts).total_seconds()
        return elapsed >= cooldown_seconds
    except (ValueError, TypeError):
        return True


def _check_rate_limit(state: dict, config: ProcessorConfig) -> bool:
    """Check if we're within rate limits.

    Returns True if OK to proceed, False if rate limited.
    """
    now = datetime.now(timezone.utc)
    current_hour = now.strftime("%Y-%m-%dT%H")

    rate_state = state.get("rate_limit", {})
    stored_hour = rate_state.get("hour", "")

    if stored_hour != current_hour:
        # New hour, reset counter
        state["rate_limit"] = {"hour": current_hour, "count": 0}
        return True

    count = rate_state.get("count", 0)
    return count < config.rate_limit_per_hour


def _increment_rate_limit(state: dict) -> None:
    """Increment the rate limit counter."""
    now = datetime.now(timezone.utc)
    current_hour = now.strftime("%Y-%m-%dT%H")

    if "rate_limit" not in state:
        state["rate_limit"] = {"hour": current_hour, "count": 0}

    if state["rate_limit"].get("hour") != current_hour:
        state["rate_limit"] = {"hour": current_hour, "count": 0}

    state["rate_limit"]["count"] = state["rate_limit"].get("count", 0) + 1


def _safe_import(module_name: str) -> Any:
    """Safely import a module from the allowlist.

    Only imports from the predefined allowlist of trusted modules.
    Raises ImportError if module is not in allowlist.
    """
    if module_name not in _ALLOWED_PROCESSOR_MODULES:
        raise ImportError(f"Module '{module_name}' is not in the allowed processor modules list")

    import importlib
    return importlib.import_module(module_name)


def _run_with_timeout(func: Callable, timeout_seconds: int, *args, **kwargs) -> Any:
    """Run a function with a timeout.

    Uses SIGALRM on Unix systems. Falls back to no timeout on Windows.
    """
    # Check if SIGALRM is available (Unix only)
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout_seconds)
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel alarm
            return result
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # No timeout support on this platform
        return func(*args, **kwargs)


def _log_processor_run(processor_name: str, status: str, details: dict) -> None:
    """Log processor execution for audit trail."""
    _logger.info(
        "Processor run: name=%s status=%s details=%s",
        processor_name,
        status,
        json.dumps(details)
    )


def check_thresholds(
    project_dir: str,
    home: str,
    config: ProcessorConfig | None = None,
) -> dict:
    """Check which processing thresholds are exceeded."""
    cfg = config or ProcessorConfig()
    state = _load_processor_state(project_dir)

    correction_count = _count_corrections(project_dir)
    interaction_count = _count_todays_interactions(project_dir)

    last_digest = state.get("last_digest", "")

    # Validate timestamp before using it
    if last_digest and not _validate_timestamp(last_digest):
        _logger.warning("Invalid last_digest timestamp, treating as never run")
        last_digest = ""

    digest_age = _hours_since(last_digest) if last_digest else float("inf")
    # Only flag stale if there's actually data to process
    has_data = interaction_count > 0 or correction_count > 0
    digest_stale = digest_age > cfg.digest_age_hours and has_data

    return {
        "corrections_exceeded": correction_count >= cfg.correction_queue_size,
        "correction_count": correction_count,
        "interactions_exceeded": interaction_count >= cfg.interaction_count,
        "interaction_count": interaction_count,
        "digest_stale": digest_stale,
        "digest_age_hours": round(digest_age, 1) if digest_age != float("inf") else None,
    }


def should_process(project_dir: str, home: str, config: ProcessorConfig | None = None) -> bool:
    """Quick check if any processing is due."""
    t = check_thresholds(project_dir, home, config)
    return t["corrections_exceeded"] or t["interactions_exceeded"] or t["digest_stale"]


def run_processors(project_dir: str, home: str, config: ProcessorConfig | None = None) -> dict:
    """Run all due processors and update state.

    Security features:
    - Rate limiting to prevent runaway execution
    - Cooldown period between processor runs
    - Timeout for each processor
    - Sanitized error messages
    - Audit logging for all operations
    """
    cfg = config or ProcessorConfig()
    t = check_thresholds(project_dir, home, cfg)
    state = _load_processor_state(project_dir)
    processors_run: list[dict] = []
    now = _now_iso()

    # Check rate limit
    if not _check_rate_limit(state, cfg):
        _logger.warning("Rate limit exceeded, skipping processor run")
        _save_processor_state(project_dir, state)
        return {
            "success": False,
            "reason": "rate_limited",
            "processors_run": [],
            "thresholds": t,
        }

    # Processor 1: Correction extraction
    if t["corrections_exceeded"] and _check_cooldown(state, "corrections", cfg.cooldown_seconds):
        try:
            _log_processor_run("corrections", "starting", {"count": t["correction_count"]})

            module = _safe_import("scripts.lib.extract_corrections")
            extract_corrections = module.extract_corrections

            corr_dir = os.path.join(project_dir, ".crux", "corrections")

            results = _run_with_timeout(
                extract_corrections,
                cfg.timeout_seconds,
                reflections_dir=corr_dir
            )

            processors_run.append({
                "name": "corrections",
                "status": "completed",
                "entries": len(results) if isinstance(results, (list, dict)) else 0,
            })
            _log_processor_run("corrections", "completed", {"entries": len(results) if isinstance(results, (list, dict)) else 0})

        except ProcessorTimeoutError:
            processors_run.append({
                "name": "corrections",
                "status": "timeout",
                "error": "Processor exceeded timeout limit",
            })
            _log_processor_run("corrections", "timeout", {})

        except Exception as exc:
            sanitized_error = _sanitize_error(str(exc))
            processors_run.append({
                "name": "corrections",
                "status": "error",
                "error": sanitized_error,
            })
            _log_processor_run("corrections", "error", {"error": sanitized_error})

        state["last_corrections"] = now
        _increment_rate_limit(state)

    # Processor 2: Digest generation
    if (t["digest_stale"] or t["interactions_exceeded"]) and _check_cooldown(state, "digest", cfg.cooldown_seconds):
        try:
            _log_processor_run("digest", "starting", {"stale": t["digest_stale"], "interactions": t["interaction_count"]})

            module = _safe_import("scripts.lib.generate_digest")
            generate_digest = module.generate_digest

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            logs_dir = os.path.join(project_dir, ".crux", "analytics", "interactions")
            corr_dir = os.path.join(project_dir, ".crux", "corrections")
            digest_dir = os.path.join(project_dir, ".crux", "analytics", "digests")

            result_digest = _run_with_timeout(
                generate_digest,
                cfg.timeout_seconds,
                logs_dir=logs_dir,
                reflections_dir=corr_dir,
                date_str=today,
                output_dir=digest_dir,
            )

            processors_run.append({
                "name": "digest",
                "status": "completed",
                "result": "generated",
            })
            _log_processor_run("digest", "completed", {})

        except ProcessorTimeoutError:
            processors_run.append({
                "name": "digest",
                "status": "timeout",
                "error": "Processor exceeded timeout limit",
            })
            _log_processor_run("digest", "timeout", {})

        except Exception as exc:
            sanitized_error = _sanitize_error(str(exc))
            processors_run.append({
                "name": "digest",
                "status": "error",
                "error": sanitized_error,
            })
            _log_processor_run("digest", "error", {"error": sanitized_error})

        state["last_digest"] = now
        _increment_rate_limit(state)

    # Processor 3: Mode audit
    if t["corrections_exceeded"] and _check_cooldown(state, "mode_audit", cfg.cooldown_seconds):
        try:
            _log_processor_run("mode_audit", "starting", {})

            audit_module = _safe_import("scripts.lib.audit_modes")
            audit_all_modes = audit_module.audit_all_modes

            paths_module = _safe_import("scripts.lib.crux_paths")
            get_user_paths = paths_module.get_user_paths

            user_paths = get_user_paths(home)

            audit_results = _run_with_timeout(
                audit_all_modes,
                cfg.timeout_seconds,
                modes_dir=user_paths.modes
            )

            processors_run.append({
                "name": "mode_audit",
                "status": "completed",
                "modes_audited": audit_results.get("total_modes", 0) if isinstance(audit_results, dict) else 0,
            })
            _log_processor_run("mode_audit", "completed", {"modes": audit_results.get("total_modes", 0) if isinstance(audit_results, dict) else 0})

        except ProcessorTimeoutError:
            processors_run.append({
                "name": "mode_audit",
                "status": "timeout",
                "error": "Processor exceeded timeout limit",
            })
            _log_processor_run("mode_audit", "timeout", {})

        except Exception as exc:
            sanitized_error = _sanitize_error(str(exc))
            processors_run.append({
                "name": "mode_audit",
                "status": "error",
                "error": sanitized_error,
            })
            _log_processor_run("mode_audit", "error", {"error": sanitized_error})

        state["last_mode_audit"] = now
        _increment_rate_limit(state)

    # Processor 4: BIP draft generation (PLAN-312)
    bip_dir = os.path.join(project_dir, ".crux", "bip")
    if os.path.isdir(bip_dir) and _check_cooldown(state, "bip_draft", cfg.cooldown_seconds):
        try:
            _log_processor_run("bip_draft", "starting", {})

            bip_module = _safe_import("scripts.lib.crux_bip_triggers")
            evaluate_triggers = bip_module.evaluate_triggers

            trigger_result = evaluate_triggers(bip_dir)

            if trigger_result.should_trigger:
                gather_module = _safe_import("scripts.lib.crux_bip_gather")
                gather_content = gather_module.gather_content

                bip_state_module = _safe_import("scripts.lib.crux_bip")
                record_history = bip_state_module.record_history
                reset_counters = bip_state_module.reset_counters

                content = _run_with_timeout(
                    gather_content,
                    cfg.timeout_seconds,
                    project_dir=project_dir,
                    bip_dir=bip_dir,
                )

                if content and content.get("draft"):
                    # Record in history and reset counters
                    source_key = f"auto:{_now_iso()}"
                    record_history(bip_dir, source_key, content["draft"][:200])
                    reset_counters(bip_dir)

                    processors_run.append({
                        "name": "bip_draft",
                        "status": "completed",
                        "reason": trigger_result.reason,
                        "draft_length": len(content.get("draft", "")),
                    })
                    _log_processor_run("bip_draft", "completed", {"reason": trigger_result.reason})
                # else: no content gathered, skip silently
            # else: triggers not met, skip silently (expected behavior)

        except ProcessorTimeoutError:
            processors_run.append({
                "name": "bip_draft",
                "status": "timeout",
                "error": "Processor exceeded timeout limit",
            })
            _log_processor_run("bip_draft", "timeout", {})

        except Exception as exc:
            sanitized_error = _sanitize_error(str(exc))
            processors_run.append({
                "name": "bip_draft",
                "status": "error",
                "error": sanitized_error,
            })
            _log_processor_run("bip_draft", "error", {"error": sanitized_error})

        state["last_bip_draft"] = now
        _increment_rate_limit(state)

    # Processor 5: BIP event → publish workflow (PLAN-324)
    # Wires detection to publishing: plan_implemented → blog + X + deploy
    events_file = os.path.join(bip_dir, "events.jsonl") if os.path.isdir(bip_dir) else None
    if events_file and os.path.exists(events_file) and _check_cooldown(state, "bip_publish", cfg.cooldown_seconds * 2):
        try:
            _log_processor_run("bip_publish", "starting", {})

            bip_module = _safe_import("scripts.lib.crux_bip")
            get_escalation_action = bip_module.get_escalation_action
            load_config = bip_module.load_config

            config = load_config(bip_dir)
            processed_events = state.get("processed_events", [])

            # Read unprocessed events
            unprocessed = []
            with open(events_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        event_key = f"{event.get('event')}:{event.get('timestamp', '')}"
                        if event_key not in processed_events:
                            unprocessed.append((event_key, event))
                    except json.JSONDecodeError:
                        continue

            published_count = 0
            for event_key, event in unprocessed:
                event_type = event.get("event", "")
                action = get_escalation_action(event_type, config)

                if action == "blog_post":
                    # Full publish workflow: blog + X + deploy
                    publish_module = _safe_import("scripts.lib.crux_bip_publish")

                    # Extract plan_id from event if available
                    plan_id = event.get("plan_id")
                    if not plan_id and "plan-" in event_type.lower():
                        # Try to extract from recent database updates
                        pass  # Will use generic publish

                    if plan_id:
                        result = _run_with_timeout(
                            publish_module.publish_for_plan,
                            cfg.timeout_seconds * 2,
                            plan_id=plan_id,
                        )
                        if result.success:
                            published_count += 1

                # Mark event as processed
                processed_events.append(event_key)
                # Keep only last 100 processed events
                if len(processed_events) > 100:
                    processed_events = processed_events[-100:]

            state["processed_events"] = processed_events

            if published_count > 0:
                processors_run.append({
                    "name": "bip_publish",
                    "status": "completed",
                    "published": published_count,
                })
                _log_processor_run("bip_publish", "completed", {"published": published_count})

        except ProcessorTimeoutError:
            processors_run.append({
                "name": "bip_publish",
                "status": "timeout",
                "error": "Processor exceeded timeout limit",
            })
            _log_processor_run("bip_publish", "timeout", {})

        except Exception as exc:
            sanitized_error = _sanitize_error(str(exc))
            processors_run.append({
                "name": "bip_publish",
                "status": "error",
                "error": sanitized_error,
            })
            _log_processor_run("bip_publish", "error", {"error": sanitized_error})

        state["last_bip_publish"] = now
        _increment_rate_limit(state)

    _save_processor_state(project_dir, state)

    return {
        "success": True,
        "processors_run": processors_run,
        "thresholds": t,
    }


def get_processor_status(project_dir: str) -> dict:
    """Return when each processor last ran."""
    state = _load_processor_state(project_dir)
    return {
        "last_digest": state.get("last_digest", "never"),
        "last_corrections": state.get("last_corrections", "never"),
        "last_mode_audit": state.get("last_mode_audit", "never"),
        "rate_limit": state.get("rate_limit", {}),
    }
