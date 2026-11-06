#!/usr/bin/env bash
export MSYSTEM=UCRT64
. /etc/profile || true
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/../../build_synfig/build_ucrt64"

cd "${BUILD_DIR}"
ninja synfigstudio
cmake --install .
