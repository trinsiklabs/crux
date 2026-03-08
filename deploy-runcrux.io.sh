#!/bin/bash
set -euo pipefail

###############################################################################
# Deploy Script
# Name: deploy-site
# Risk: medium
# Created: 2026-03-05
# Status: active
# Description: Build and deploy 11ty site to runcrux.io
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="runcrux.io"
USER="runcrux.io"
DEST_DIR="/home/runcrux.io/public_html/"
SRC_DIR="${SCRIPT_DIR}/site/_site"

BUILD=0
DRY_RUN=0
VERBOSE=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case $1 in
    --build)
      BUILD=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

build() {
  echo "Building site..."
  cd "${SCRIPT_DIR}/site"
  npm install
  npm run build
  echo "Build complete: ${SRC_DIR}"
}

check_links() {
  echo "Checking for broken links..."
  if [[ -x "${SCRIPT_DIR}/scripts/check-links.sh" ]]; then
    "${SCRIPT_DIR}/scripts/check-links.sh" "${SRC_DIR}" || {
      echo "ERROR: Broken links detected. Fix them before deploying."
      exit 1
    }
  else
    echo "Warning: Link checker not found, skipping check"
  fi
}

deploy() {
  local rsync_opts=("-avz")

  if [[ "${VERBOSE}" -eq 1 ]]; then
    rsync_opts+=("-v" "--progress")
  fi

  rsync_opts+=("--delete")

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    rsync_opts+=("--dry-run")
    echo "[DRY RUN] Would deploy:"
  else
    if [[ "${FORCE}" -eq 0 ]]; then
      echo "Deploy ${SRC_DIR} → ${USER}@${SERVER}:${DEST_DIR}"
      read -p "Continue? [y/N] " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
      fi
    fi
  fi

  rsync_opts+=(
    --exclude ".git/"
    --exclude "*.map"
  )

  rsync "${rsync_opts[@]}" \
    "${SRC_DIR}/" \
    "${USER}@${SERVER}:${DEST_DIR}"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY RUN] Deploy complete (no files transferred)"
  else
    echo "Deployed successfully!"
  fi
}

main() {
  if [[ "${BUILD}" -eq 1 ]]; then
    build
  elif [[ ! -d "${SRC_DIR}" ]]; then
    echo "Error: ${SRC_DIR} not found. Run with --build or build manually."
    exit 1
  fi

  # PLAN-328: Check for broken links before deploying
  check_links

  deploy
}

main "$@"
