"""
Contract tests for handshake and authentication against FakeBridgeServer.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from synfig_mcp.errors import BridgeAuthError, ProtocolVersionMismatchError
from synfig_mcp.protocol.client import BridgeClient
from tests.support.fake_bridge import FakeBridgeServer

TEST_TOKEN = "valid_token_0123456789abcdef"


@pytest_asyncio.fixture
async def fake_bridge() -> AsyncIterator[FakeBridgeServer]:
    server = FakeBridgeServer(token=TEST_TOKEN, protocol_version="1.0")
    await server.start()
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_handshake_success(fake_bridge: FakeBridgeServer) -> None:
    client = BridgeClient(
        host="127.0.0.1",
        port=fake_bridge.assigned_port,
        token=TEST_TOKEN,
        protocol_version="1.0",
    )
    await client.connect()
    assert client.is_connected
    assert "layer" in client.capabilities
    assert "param" in client.capabilities
    await client.close()


@pytest.mark.asyncio
async def test_handshake_invalid_token(fake_bridge: FakeBridgeServer) -> None:
    client = BridgeClient(
        host="127.0.0.1",
        port=fake_bridge.assigned_port,
        token="wrong_token_invalid_12345",
        protocol_version="1.0",
    )
    with pytest.raises(BridgeAuthError):
        await client.connect()
    await client.close()


@pytest.mark.asyncio
async def test_handshake_incompatible_version(fake_bridge: FakeBridgeServer) -> None:
    client = BridgeClient(
        host="127.0.0.1",
        port=fake_bridge.assigned_port,
        token=TEST_TOKEN,
        protocol_version="2.0",  # Major version mismatch
    )
    with pytest.raises(ProtocolVersionMismatchError):
        await client.connect()
    await client.close()
