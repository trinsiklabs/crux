"""Cross-domain knowledge flows for Crux.

Bidirectional knowledge transfer between security, testing, and design domains:
- Security findings become test patterns
- Test failures inform design patterns
- Design validation findings feed security knowledge

Security improvements (PLAN-166):
- Input validation for all cross-domain transfers
- Field length limits to prevent memory exhaustion
- Structured logging for audit trail
"""

from __future__ import annotations

import logging
from typing import Any

from scripts.lib.crux_knowledge_categories import (
    KnowledgeStore,
    TestPatternEntry,
    SecurityPatternEntry,
    DesignPatternEntry,
    create_test_pattern,
    create_security_pattern,
    create_design_pattern,
)
from scripts.lib.crux_security_audit import SecurityFinding
from scripts.lib.crux_design_validation import ValidationFinding

# Configure structured logging
_logger = logging.getLogger("crux.cross_domain")

# Maximum field sizes (bytes)
_MAX_TITLE_LENGTH = 500
_MAX_DESCRIPTION_LENGTH = 10240  # 10KB
_MAX_CODE_LENGTH = 51200  # 50KB
_MAX_VALUE_LENGTH = 1024
_MAX_LIST_ITEMS = 100


def _truncate_field(value: str, max_length: int, field_name: str = "field") -> str:
    """Truncate a field to max length with warning."""
    if len(value) > max_length:
        _logger.warning(
            "Truncating %s from %d to %d characters",
            field_name, len(value), max_length
        )
        return value[:max_length] + "...[truncated]"
    return value


def _validate_string(value: Any, field_name: str, max_length: int) -> str:
    """Validate and sanitize a string field."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return _truncate_field(value, max_length, field_name)


def _validate_list(value: Any, field_name: str, max_items: int = _MAX_LIST_ITEMS) -> list:
    """Validate a list field."""
    if value is None:
        return []
    if not isinstance(value, list):
        _logger.warning("Expected list for %s, got %s", field_name, type(value).__name__)
        return []
    if len(value) > max_items:
        _logger.warning(
            "Truncating %s list from %d to %d items",
            field_name, len(value), max_items
        )
        return value[:max_items]
    return value


def security_to_test_pattern(
    finding: SecurityFinding,
    store: KnowledgeStore,
) -> TestPatternEntry:
    """Convert a security finding into a test pattern.

    When a vulnerability is found, we create a test pattern so future
    test generation includes checks for the same class of vulnerability.
    """
    # Validate inputs
    title = _validate_string(finding.title, "title", _MAX_TITLE_LENGTH)
    category = _validate_string(finding.category, "category", _MAX_VALUE_LENGTH)
    finding_id = _validate_string(finding.finding_id, "finding_id", _MAX_VALUE_LENGTH)
    remediation = _validate_string(finding.remediation, "remediation", _MAX_DESCRIPTION_LENGTH)

    test_code = _truncate_field(
        f"# Regression test for {finding_id}: {title}\n"
        f"# Remediation: {remediation}",
        _MAX_CODE_LENGTH,
        "test_code"
    )

    entry = create_test_pattern(
        title=f"Test for: {title}",
        applies_to=[category] if category else [],
        test_code=test_code,
        prevented_bugs=[finding_id] if finding_id else [],
    )
    store.add(entry)

    _logger.info(
        "Created test pattern from security finding: %s -> %s",
        finding_id, entry.entry_id if hasattr(entry, 'entry_id') else "new"
    )

    return entry


def testing_to_design_pattern(
    component: str,
    property_name: str,
    preferred_value: str,
    reason: str,
    store: KnowledgeStore,
) -> DesignPatternEntry:
    """Convert a test failure insight into a design pattern.

    When UI tests fail due to design issues (e.g., touch targets too small),
    we create a design pattern so future design generation avoids the issue.
    """
    # Validate inputs
    component = _validate_string(component, "component", _MAX_VALUE_LENGTH)
    property_name = _validate_string(property_name, "property_name", _MAX_VALUE_LENGTH)
    preferred_value = _validate_string(preferred_value, "preferred_value", _MAX_VALUE_LENGTH)
    reason = _validate_string(reason, "reason", _MAX_DESCRIPTION_LENGTH)

    title = _truncate_field(
        f"{component}: {property_name} ({reason})",
        _MAX_TITLE_LENGTH,
        "title"
    )

    entry = create_design_pattern(
        title=title,
        component=component,
        property_name=property_name,
        preferred_value=preferred_value,
    )
    store.add(entry)

    _logger.info(
        "Created design pattern from test insight: %s.%s",
        component, property_name
    )

    return entry


def design_to_security_pattern(
    finding: ValidationFinding,
    store: KnowledgeStore,
) -> SecurityPatternEntry:
    """Convert a design validation finding into a security pattern.

    WCAG violations and accessibility issues are tracked as security-adjacent
    patterns so future security audits also check for them.
    """
    # Validate inputs
    title = _validate_string(finding.title, "title", _MAX_TITLE_LENGTH)
    remediation = _validate_string(finding.remediation, "remediation", _MAX_DESCRIPTION_LENGTH)

    entry = create_security_pattern(
        title=f"Accessibility: {title}",
        vulnerability_type="accessibility",
        cwe="",
        remediation=remediation,
    )
    store.add(entry)

    _logger.info(
        "Created security pattern from design finding: %s",
        title[:50]
    )

    return entry


def cross_domain_sync(
    store: KnowledgeStore,
    security_findings: list[SecurityFinding] | None = None,
    design_findings: list[ValidationFinding] | None = None,
    test_design_updates: list[dict] | None = None,
) -> dict:
    """Perform all cross-domain knowledge transfers in one operation.

    Args:
        store: Knowledge store to update.
        security_findings: Security findings to convert to test patterns.
        design_findings: Design findings to convert to security patterns.
        test_design_updates: Test failure insights to convert to design patterns.
            Each dict has: component, property_name, preferred_value, reason.

    Security features:
        - Input validation on all fields
        - List size limits to prevent memory exhaustion
        - Structured logging for audit trail
    """
    test_created = 0
    security_created = 0
    design_created = 0
    errors: list[str] = []

    # Validate list sizes
    if security_findings:
        security_findings = _validate_list(security_findings, "security_findings", _MAX_LIST_ITEMS)

    if design_findings:
        design_findings = _validate_list(design_findings, "design_findings", _MAX_LIST_ITEMS)

    if test_design_updates:
        test_design_updates = _validate_list(test_design_updates, "test_design_updates", _MAX_LIST_ITEMS)

    if security_findings:
        for finding in security_findings:
            try:
                security_to_test_pattern(finding, store)
                test_created += 1
            except Exception as e:
                error_msg = f"Failed to convert security finding: {str(e)[:100]}"
                _logger.warning(error_msg)
                errors.append(error_msg)

    if design_findings:
        for finding in design_findings:
            try:
                design_to_security_pattern(finding, store)
                security_created += 1
            except Exception as e:
                error_msg = f"Failed to convert design finding: {str(e)[:100]}"
                _logger.warning(error_msg)
                errors.append(error_msg)

    if test_design_updates:
        for update in test_design_updates:
            try:
                # Validate required fields exist
                if not isinstance(update, dict):
                    _logger.warning("Skipping non-dict test_design_update")
                    continue

                required_fields = ["component", "property_name", "preferred_value", "reason"]
                missing = [f for f in required_fields if f not in update]
                if missing:
                    _logger.warning("Skipping update missing fields: %s", missing)
                    continue

                testing_to_design_pattern(
                    component=update["component"],
                    property_name=update["property_name"],
                    preferred_value=update["preferred_value"],
                    reason=update["reason"],
                    store=store,
                )
                design_created += 1
            except Exception as e:
                error_msg = f"Failed to convert test insight: {str(e)[:100]}"
                _logger.warning(error_msg)
                errors.append(error_msg)

    _logger.info(
        "Cross-domain sync complete: test=%d, security=%d, design=%d, errors=%d",
        test_created, security_created, design_created, len(errors)
    )

    return {
        "test_patterns_created": test_created,
        "security_patterns_created": security_created,
        "design_patterns_created": design_created,
        "errors": errors if errors else None,
    }
