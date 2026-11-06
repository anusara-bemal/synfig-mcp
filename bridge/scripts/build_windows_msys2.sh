#!/usr/bin/env bash
export MSYSTEM=UCRT64
. /etc/profile || true
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="${ROOT_DIR}/build_synfig/synfig_src"
BUILD_DIR="${ROOT_DIR}/build_synfig/build_ucrt64"

echo "=== Root Directory:   ${ROOT_DIR} ==="
echo "=== Source Directory: ${SRC_DIR} ==="
echo "=== Build Directory:  ${BUILD_DIR} ==="

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

echo "=== Running CMake Configure ==="
cmake -GNinja \
    -DMSYS=1 \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_TESTS=OFF \
    -DCMAKE_INSTALL_PREFIX=./install \
    "${SRC_DIR}"

echo "=== Building Synfig Studio ==="
ninja synfigstudio

echo "=== Build Finished Successfully ==="
