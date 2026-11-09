#!/usr/bin/env bash
# Apply mcp_bridge patches to Synfig Studio source tree
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="${1:-${ROOT_DIR}/build_synfig/synfig_src}"
PATCHES_DIR="${ROOT_DIR}/bridge/patches"

echo "=== Applying patches from ${PATCHES_DIR} to ${SRC_DIR} ==="

if [ ! -d "${SRC_DIR}" ]; then
    echo "ERROR: Synfig source directory not found at ${SRC_DIR}" >&2
    exit 1
fi

# Copy mcp_bridge sources into synfig-studio gui directory
mkdir -p "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge"
cp -r "${ROOT_DIR}/bridge/src/mcp_bridge/"* "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge/"

# Inject build commit SHA and version
COMMIT_SHA="${SYNFIG_MCP_COMMIT_SHA:-$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "dev")}"
VERSION="${SYNFIG_MCP_VERSION:-0.8.0-rc2}"
VERSION="${VERSION#v}"
sed -i "s/#define BUILD_COMMIT_SHA .*/#define BUILD_COMMIT_SHA \"${COMMIT_SHA}\"/" "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge/bridge_init.cpp"
sed -i "s/#define BUILD_VERSION .*/#define BUILD_VERSION \"${VERSION}\"/" "${SRC_DIR}/synfig-studio/src/gui/mcp_bridge/bridge_init.cpp"

# Apply git patches. Fail loudly if a patch cannot be applied: silently
# continuing here produces a vanilla Synfig Studio binary without the MCP
# bridge, which only shows up much later as a smoke-test timeout.
cd "${SRC_DIR}"
for patch in "${PATCHES_DIR}"/*.patch; do
    [ -f "$patch" ] || continue
    echo "Applying $(basename "$patch")..."
    if git apply --reverse --check "$patch" >/dev/null 2>&1; then
        echo "  Patch already applied, skipping."
    elif git apply --check "$patch" >/dev/null 2>&1; then
        git apply --whitespace=nowarn "$patch"
    else
        echo "ERROR: failed to apply $(basename "$patch") to ${SRC_DIR}" >&2
        echo "Re-run with: git apply --verbose '$patch'" >&2
        exit 1
    fi
done

# Hard guarantee that the GUI hook made it into the tree.
if ! grep -q "mcp_bridge::start()" "${SRC_DIR}/synfig-studio/src/gui/app.cpp"; then
    echo "ERROR: MCP bridge hook is missing from app.cpp after patching." >&2
    echo "The build would produce a Studio binary without the bridge." >&2
    exit 1
fi

echo "=== Patches applied successfully ==="
