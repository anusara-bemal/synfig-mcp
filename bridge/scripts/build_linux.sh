#!/usr/bin/env bash
# Build script for Synfig Studio on Linux (Ubuntu/Debian)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="${ROOT_DIR}/build_synfig/synfig_src"
BUILD_DIR="${ROOT_DIR}/build_synfig/build_linux"

echo "=== Synfig Studio Linux Build ==="

# 1. Fetch pinned commit if missing
if [ ! -d "${SRC_DIR}/.git" ]; then
    bash "${SCRIPT_DIR}/fetch_synfig.sh" "${SRC_DIR}"
fi

# 2. Apply bridge patches if present
if [ -f "${SCRIPT_DIR}/apply_patches.sh" ]; then
    bash "${SCRIPT_DIR}/apply_patches.sh" "${SRC_DIR}"
fi

# 3. Configure CMake
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

cmake -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_TESTS=OFF \
    -DCMAKE_INSTALL_PREFIX=./install \
    "${SRC_DIR}"

ninja synfigstudio
cmake --install .

echo "=== Linux Build Completed ==="
