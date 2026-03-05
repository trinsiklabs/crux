#!/bin/bash
################################################################################
# Transaction Script Template
#
# This template implements atomic multi-file operations with rollback capability.
# Use this when a task requires coordinated changes to multiple files that must
# either all succeed or all fail (no partial state).
#
# Name: [descriptive-kebab-case-name]
# Risk: medium|high
# Created: YYYY-MM-DD
# Status: active|deprecated|archived
# Description: [What this script does in one line]
################################################################################

set -euo pipefail

################################################################################
# Configuration
################################################################################

DRY_RUN="${DRY_RUN:-0}"
DEBUG="${DEBUG:-0}"

# Temporary directory for staging changes
TEMP_DIR="${TEMP_DIR:-$(mktemp -d)}"

# Track files modified for potential rollback
declare -a MODIFIED_FILES=()
declare -a CREATED_FILES=()

# Script directory for utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo "[INFO] $*" >&2
}

log_warn() {
    echo "[WARN] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_success() {
    echo "[SUCCESS] $*" >&2
}

log_debug() {
    if [[ "$DEBUG" == "1" ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

# Record a file that will be modified (for rollback tracking)
track_modified() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cp "$file" "${TEMP_DIR}/backup_$(basename "$file").bak"
        MODIFIED_FILES+=("$file")
        log_debug "Tracking modified file: $file"
    fi
}

# Record a file that will be created (for rollback tracking)
track_created() {
    local file="$1"
    CREATED_FILES+=("$file")
    log_debug "Tracking created file: $file"
}

# Execute a command in dry-run aware mode
run_cmd() {
    local cmd_desc="$1"
    shift

    if [[ "$DRY_RUN" == "1" ]]; then
        log_info "[DRY_RUN] Would execute: $cmd_desc"
        log_debug "  Command: $@"
        return 0
    else
        log_debug "Executing: $cmd_desc"
        log_debug "  Command: $@"
        "$@" || {
            log_error "Command failed: $cmd_desc"
            return 1
        }
        log_success "Completed: $cmd_desc"
    fi
}

################################################################################
# Transaction Stages
################################################################################

# Stage 1: Validation
# Check preconditions and validate inputs
validate_transaction() {
    log_info "=== STAGE 1: Validation ==="

    # Add your validation logic here
    # Example: check that required files exist
    # Example: verify permissions
    # Example: check for conflicting state

    log_info "Validation passed"
}

# Stage 2: Preparation
# Create temporary copies and prepare changes
prepare_transaction() {
    log_info "=== STAGE 2: Preparation ==="

    # Track files that will be modified
    # Example: track_modified "/path/to/file1.txt"
    # Example: track_modified "/path/to/file2.txt"

    # Prepare changes in temp directory
    # Example: mkdir -p "${TEMP_DIR}/changes"

    log_info "Preparation complete"
}

# Stage 3: Apply Changes
# Make all modifications
apply_transaction() {
    log_info "=== STAGE 3: Apply Changes ==="

    # Apply all changes in a coordinated manner
    # These should be atomic or grouped logically

    # Example:
    # run_cmd "Updating file 1" cp "${TEMP_DIR}/file1.new" "/path/to/file1.txt"
    # run_cmd "Updating file 2" cp "${TEMP_DIR}/file2.new" "/path/to/file2.txt"
    # run_cmd "Creating file 3" touch "/path/to/file3.txt"

    log_info "Changes applied"
}

# Stage 4: Verification
# Verify that changes were applied correctly
verify_transaction() {
    log_info "=== STAGE 4: Verification ==="

    # Verify all changes were applied as expected
    # Example: check file contents
    # Example: verify file permissions
    # Example: test functionality

    log_info "Verification passed"
}

# Stage 5: Commit
# Finalize changes (git commit, etc.)
commit_transaction() {
    log_info "=== STAGE 5: Commit ==="

    # Perform any final commits or state changes
    # Example: git add and commit
    # Example: update metadata

    if [[ "$DRY_RUN" != "1" ]]; then
        log_success "Transaction committed successfully"
    fi
}

################################################################################
# Rollback Logic
################################################################################

# Rollback all changes if something failed
rollback_transaction() {
    log_warn "=== ROLLBACK IN PROGRESS ==="

    # Restore modified files from backups
    for file in "${MODIFIED_FILES[@]}"; do
        backup="${TEMP_DIR}/backup_$(basename "$file").bak"
        if [[ -f "$backup" ]]; then
            log_warn "Restoring: $file"
            if [[ "$DRY_RUN" != "1" ]]; then
                cp "$backup" "$file"
            fi
        fi
    done

    # Delete created files
    for file in "${CREATED_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            log_warn "Deleting: $file"
            if [[ "$DRY_RUN" != "1" ]]; then
                rm -f "$file"
            fi
        fi
    done

    log_error "Transaction rolled back"
}

# Cleanup temporary directory
cleanup() {
    if [[ -d "$TEMP_DIR" ]] && [[ "$TEMP_DIR" == *"/tmp"* ]]; then
        rm -rf "$TEMP_DIR"
        log_debug "Cleaned up temporary directory: $TEMP_DIR"
    fi
}

################################################################################
# Main Transaction Orchestration
################################################################################

main() {
    log_info "Starting transaction: $(basename "$0")"

    if [[ "$DRY_RUN" == "1" ]]; then
        log_warn "Running in DRY_RUN mode"
    fi

    # Execute transaction stages
    if ! validate_transaction; then
        log_error "Validation failed"
        cleanup
        return 1
    fi

    if ! prepare_transaction; then
        log_error "Preparation failed"
        rollback_transaction
        cleanup
        return 1
    fi

    if ! apply_transaction; then
        log_error "Failed to apply changes"
        rollback_transaction
        cleanup
        return 1
    fi

    if ! verify_transaction; then
        log_error "Verification failed"
        rollback_transaction
        cleanup
        return 1
    fi

    if ! commit_transaction; then
        log_error "Commit failed"
        rollback_transaction
        cleanup
        return 1
    fi

    cleanup
    log_success "Transaction completed successfully"
}

################################################################################
# Error Handling
################################################################################

# Trap errors to trigger rollback
trap 'log_error "Transaction interrupted on line $LINENO"; rollback_transaction; cleanup; exit 1' ERR

################################################################################
# Help & Entry Point
################################################################################

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat << 'USAGE'
Usage: transaction-template.sh [OPTIONS]

A transaction script for atomic multi-file operations with rollback capability.

Options:
    --help, -h          Show this help message
    --dry-run           Show what would be done without making changes
    --debug             Enable debug output

Environment Variables:
    DRY_RUN             Set to 1 to enable dry-run mode
    DEBUG               Set to 1 to enable debug output
    TEMP_DIR            Override temporary directory (default: auto-generated)

Transaction Stages:
    1. Validation       - Check preconditions
    2. Preparation      - Prepare changes
    3. Apply Changes    - Make modifications
    4. Verification     - Verify success
    5. Commit           - Finalize state

If any stage fails, all changes are rolled back automatically.

Examples:
    # Preview changes without applying them
    ./transaction-template.sh --dry-run

    # Apply changes with debug output
    ./transaction-template.sh --debug

    # Normal execution
    ./transaction-template.sh

USAGE
    exit 0
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --debug)
            DEBUG=1
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Execute transaction
main "$@"
