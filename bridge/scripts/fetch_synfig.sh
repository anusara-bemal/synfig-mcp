#!/usr/bin/env bash
# Fetch pinned Synfig source code using bridge/PINNED_COMMIT
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PINNED_FILE="${ROOT_DIR}/bridge/PINNED_COMMIT"

if [ ! -f "${PINNED_FILE}" ]; then
    echo "ERROR: Pinned commit file not found at ${PINNED_FILE}"
    exit 1
fi

PINNED_COMMIT="$(tr -d '[:space:]' < "${PINNED_FILE}")"
REPO_URL="https://github.com/synfig/synfig.git"
TARGET_DIR="${1:-${ROOT_DIR}/build_synfig/synfig_src}"

echo "=== Fetching Synfig at pinned commit ${PINNED_COMMIT} ==="

if [ -d "${TARGET_DIR}/.git" ]; then
    echo "Directory ${TARGET_DIR} already exists. Fetching commit..."
    cd "${TARGET_DIR}"
    git fetch origin "${PINNED_COMMIT}" || git fetch --all
    git checkout "${PINNED_COMMIT}"
else
    mkdir -p "$(dirname "${TARGET_DIR}")"
    git clone "${REPO_URL}" "${TARGET_DIR}"
    cd "${TARGET_DIR}"
    git checkout "${PINNED_COMMIT}"
fi

CURRENT_HASH="$(git rev-parse HEAD)"
echo "=== Synfig source ready at: ${CURRENT_HASH} ==="
