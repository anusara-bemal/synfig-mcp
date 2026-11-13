"""
Contract tests for client request/response, correlation, reconnect, and event streaming.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from synfig_mcp.protocol.client import BridgeClient
from tests.support.fake_bridge import FakeBridgeServer

TEST_TOKEN = "valid_token_0123456789abcdef"


@pytest_asyncio.fixture
async def running_bridge() -> AsyncIterator[FakeBridgeServer]:
    server = FakeBridgeServer(token=TEST_TOKEN, protocol_version="1.0")
    await server.start()
    yield server
    await server.stop()


@pytest_asyncio.fixture
async def connected_client(running_bridge: FakeBridgeServer) -> AsyncIterator[BridgeClient]:
    client = BridgeClient(
        host="127.0.0.1",
        port=running_bridge.assigned_port,
        token=TEST_TOKEN,
        protocol_version="1.0",
    )
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_client_crud_methods(connected_client: BridgeClient) -> None:
    # 1. doc.info
    doc_info = await connected_client.call("doc.info", {"doc_id": "doc_0"})
    assert doc_info["doc_id"] == "doc_0"
    assert doc_info["width"] == 1920

    # 2. layer.add
    layer_res = await connected_client.call(
        "layer.add",
        {"doc_id": "doc_0", "layer_type": "circle", "depth": 0},
    )
    assert layer_res["layer_id"] == "circle_001"
    assert layer_res["diff"]["action"] == "layer.add"

    # 3. param.set
    param_res = await connected_client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": "circle_001",
            "param_name": "color",
            "value": {"type": "color", "r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
        },
    )
    assert param_res["after"]["r"] == 1.0

    # 4. history.undo
    undo_res = await connected_client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_res["success"] is True


@pytest.mark.asyncio
async def test_client_concurrent_id_correlation(connected_client: BridgeClient) -> None:
    """Test that concurrent requests resolve to the exact correct responses using id correlation."""

    async def make_call(doc_id: str) -> dict[str, object]:
        res = await connected_client.call("doc.info", {"doc_id": doc_id})
        return res  # type: ignore[no-any-return]

    results = await asyncio.gather(
        make_call("doc_1"),
        make_call("doc_2"),
        make_call("doc_3"),
        make_call("doc_4"),
        make_call("doc_5"),
    )

    assert len(results) == 5
    for i, r in enumerate(results, 1):
        assert r["doc_id"] == f"doc_{i}"


@pytest.mark.asyncio
async def test_client_event_streaming(
    running_bridge: FakeBridgeServer, connected_client: BridgeClient
) -> None:
    """Test server-to-client notifications streaming."""
    # Start consumer
    received_events = []

    async def consume_one() -> None:
        async for event in connected_client.events():
            received_events.append(event)
            break

    task = asyncio.create_task(consume_one())
    await asyncio.sleep(0.05)

    # Broadcast event from fake bridge
    await running_bridge.broadcast_event(
        "event.time_changed",
        {"doc_id": "doc_0", "time": 3.0, "frame": 72},
    )

    await asyncio.wait_for(task, timeout=2.0)
    assert len(received_events) == 1
    assert received_events[0].method == "event.time_changed"
    assert received_events[0].params["time"] == 3.0


@pytest.mark.asyncio
async def test_client_reconnect_retry(running_bridge: FakeBridgeServer) -> None:
    """Test reconnect_with_retry connects cleanly."""
    client = BridgeClient(
        host="127.0.0.1",
        port=running_bridge.assigned_port,
        token=TEST_TOKEN,
    )
    await client.connect_with_retry(max_attempts=3, initial_backoff=0.05)
    assert client.is_connected
    await client.close()
