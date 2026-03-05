#!/bin/bash
################################################################################
# Script Template
#
# This is the standard template for all Crux scripts. Copy this file and
# replace the template sections with your implementation.
#
# Name: [descriptive-kebab-case-name]
# Risk: low|medium|high
# Created: YYYY-MM-DD
# Status: active|deprecated|archived
# Description: [What this script does in one line]
################################################################################

set -euo pipefail

################################################################################
# Configuration
################################################################################

# Support dry-run mode for safety testing
DRY_RUN="${DRY_RUN:-0}"

# Script directory for sourcing utilities
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
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

# Execute a command, respecting DRY_RUN
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
# Main Implementation
################################################################################

main() {
    log_info "Starting script execution"

    # Add your implementation here
    # Use run_cmd for operations that modify state
    # Example: run_cmd "Copying file" cp source.txt destination.txt

    if [[ "$DRY_RUN" == "1" ]]; then
        log_warn "Running in DRY_RUN mode - no changes were made"
    fi

    log_success "Script completed successfully"
}

################################################################################
# Error Handling & Cleanup
################################################################################

# Trap errors for cleanup
trap 'log_error "Script failed on line $LINENO"' ERR

################################################################################
# Entry Point
################################################################################

# Show usage information if --help requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat << 'USAGE'
Usage: script-template.sh [OPTIONS]

Options:
    --help, -h          Show this help message
    --dry-run           Show what would be done without making changes
    --debug             Enable debug output

Environment Variables:
    DRY_RUN             Set to 1 to enable dry-run mode
    DEBUG               Set to 1 to enable debug output

Examples:
    # Run normally
    ./script-template.sh

    # Test without making changes
    ./script-template.sh --dry-run

    # Run with debug output
    ./script-template.sh --debug

USAGE
    exit 0
fi

# Parse optional arguments
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

# Execute main function
main "$@"
