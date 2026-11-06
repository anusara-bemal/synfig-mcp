#!/usr/bin/env bash
# Run GTK-free C++ unit tests and protocol fixture test suite
export MSYSTEM=UCRT64
. /etc/profile || true
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${ROOT_DIR}"
echo "=== 1. Compiling and running protocol fixture test ==="
g++ -std=c++17 -O2 bridge/tests/test_protocol_fixtures.cpp -o bridge/tests/test_protocol_fixtures.exe
./bridge/tests/test_protocol_fixtures.exe protocol/fixtures

echo "=== 2. Compiling and running standalone bridge test ==="
g++ -std=c++17 -O2 -DMCP_BRIDGE_STANDALONE=1 \
    bridge/tests/test_bridge_standalone.cpp \
    bridge/src/mcp_bridge/auth.cpp \
    bridge/src/mcp_bridge/types_serializer.cpp \
    bridge/src/mcp_bridge/dispatcher.cpp \
    bridge/src/mcp_bridge/handlers.cpp \
    -o bridge/tests/test_bridge_standalone.exe
./bridge/tests/test_bridge_standalone.exe

echo "=== All C++ bridge unit tests completed successfully ==="
