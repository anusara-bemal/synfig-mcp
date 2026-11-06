#!/usr/bin/env bash
# Fetch pinned Synfig source code at tag v1.5.5
set -e

PINNED_TAG="v1.5.5"
REPO_URL="https://github.com/synfig/synfig.git"
TARGET_DIR="${1:-./build_synfig/synfig_src}"

echo "=== Fetching Synfig at pinned tag ${PINNED_TAG} ==="
if [ -d "${TARGET_DIR}/.git" ]; then
    echo "Directory ${TARGET_DIR} already exists. Checking out ${PINNED_TAG}..."
    cd "${TARGET_DIR}"
    git fetch --tags
    git checkout "${PINNED_TAG}"
else
    mkdir -p "$(dirname "${TARGET_DIR}")"
    git clone --depth 1 --branch "${PINNED_TAG}" "${REPO_URL}" "${TARGET_DIR}"
fi

cd "${TARGET_DIR}"
COMMIT_HASH=$(git rev-parse HEAD)
echo "=== Pinned Synfig Commit: ${COMMIT_HASH} (${PINNED_TAG}) ==="
