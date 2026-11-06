"""
Edge case and resilience tests: timeouts, cancellation, oversized payloads, malformed JSON.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from synfig_mcp.errors import BridgeConnectionError, SynfigError
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer

TEST_TOKEN = "valid_token_0123456789abcdef"


@pytest_asyncio.fixture
async def running_bridge() -> AsyncIterator[FakeBridgeServer]:
    server = FakeBridgeServer(token=TEST_TOKEN, protocol_version="1.0")
    await server.start()
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_request_timeout(running_bridge: FakeBridgeServer) -> None:
    client = BridgeClient(
        host="127.0.0.1",
        port=running_bridge.assigned_port,
        token=TEST_TOKEN,
        default_timeout=5.0,
    )
    await client.connect()

    # Delay subsequent responses so call() times out
    running_bridge.delay_response_seconds = 1.0
    with pytest.raises(SynfigError, match="timed out"):
        await client.call("doc.info", {"doc_id": "doc_0"}, timeout=0.1)

    await client.close()


@pytest.mark.asyncio
async def test_oversized_payload_rejected(running_bridge: FakeBridgeServer) -> None:
    client = BridgeClient(
        host="127.0.0.1",
        port=running_bridge.assigned_port,
        token=TEST_TOKEN,
    )
    await client.connect()

    # Create oversized parameter (> 10MB)
    huge_str = "x" * (11 * 1024 * 1024)
    with pytest.raises(SynfigError, match="maximum allowed size"):
        await client.call("layer.add", {"huge": huge_str})

    await client.close()


@pytest.mark.asyncio
async def test_connection_drop_mid_request(running_bridge: FakeBridgeServer) -> None:
    client = BridgeClient(
        host="127.0.0.1",
        port=running_bridge.assigned_port,
        token=TEST_TOKEN,
    )
    await client.connect()

    running_bridge.close_on_next_request = True
    with pytest.raises(BridgeConnectionError):
        await client.call("doc.info", {"doc_id": "doc_0"})

    assert not client.is_connected
    await client.close()


@pytest.mark.asyncio
async def test_client_task_cancellation(running_bridge: FakeBridgeServer) -> None:
    running_bridge.delay_response_seconds = 0.5
    client = BridgeClient(
        host="127.0.0.1",
        port=running_bridge.assigned_port,
        token=TEST_TOKEN,
    )
    await client.connect()

    task = asyncio.create_task(client.call("doc.info", {"doc_id": "doc_0"}))
    await asyncio.sleep(0.05)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Connection should still be healthy for subsequent requests
    running_bridge.delay_response_seconds = 0.0
    res = await client.call("doc.info", {"doc_id": "doc_0"})
    assert res["doc_id"] == "doc_0"

    await client.close()
