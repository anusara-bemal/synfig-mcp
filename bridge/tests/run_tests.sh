#!/usr/bin/env bash
# Run GTK-free C++ protocol fixture test suite
export MSYSTEM=UCRT64
. /etc/profile || true
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${ROOT_DIR}"
g++ -std=c++17 -O2 bridge/tests/test_protocol_fixtures.cpp -o bridge/tests/test_protocol_fixtures.exe
./bridge/tests/test_protocol_fixtures.exe protocol/fixtures
