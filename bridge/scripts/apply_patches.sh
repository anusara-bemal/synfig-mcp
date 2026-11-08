#!/usr/bin/env bash
# Apply mcp_bridge patches to Synfig Studio source tree
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="${1:-${ROOT_DIR}/build_synfig/synfig_src}"
PATCHES_DIR="${ROOT_DIR}/bridge/patches"

echo "=== Applying patches from ${PATCHES_DIR} to ${SRC_DIR} ==="

# Copy mcp_bridge sources into synfig-studio gui directory
mkdir -p "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge"
cp -r "${ROOT_DIR}/bridge/src/mcp_bridge/"* "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge/"

# Inject build commit SHA and version
COMMIT_SHA=$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "dev")
sed -i "s/#define BUILD_COMMIT_SHA .*/#define BUILD_COMMIT_SHA \"${COMMIT_SHA}\"/" "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge/bridge_init.cpp"
sed -i "s/#define BUILD_VERSION .*/#define BUILD_VERSION \"0.7.0-rc2\"/" "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge/bridge_init.cpp"

# Apply git patches
cd "${SRC_DIR}"
for patch in "${PATCHES_DIR}"/*.patch; do
    if [ -f "$patch" ]; then
        echo "Applying $(basename "$patch")..."
        git apply --check "$patch" && git apply "$patch" || echo "Patch already applied or failed check."
    fi
done

echo "=== Patches applied successfully ==="
