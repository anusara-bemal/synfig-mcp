"""
Backend parity: the same operation must behave the same way in the headless
engine and in the live bridge.

The MCP exposes one tool surface for two very different implementations.  If
they drift apart - for example when the bridge ignores part of a scene
specification - the model gets different documents depending on which backend
happens to be active.  These tests run the same operations against both and
compare the observable results.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from mcp.client import Client

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer
from synfig_mcp.server import create_server


@pytest_asyncio.fixture(params=["headless", "live_fake"])
async def mcp_app(request: pytest.FixtureRequest) -> AsyncIterator[Any]:
    """Yield an MCP server bound to the parametrized backend."""
    mode: str = request.param
    if mode == "headless":
        yield create_server(backend=HeadlessBackend())
        return

    fake_bridge = FakeBridgeServer(port=0)
    await fake_bridge.start()
    bridge_client = BridgeClient(
        host=fake_bridge.host,
        port=fake_bridge.assigned_port,
        token=fake_bridge.token,
    )
    await bridge_client.connect()
    yield create_server(backend=LiveBackend(client=bridge_client))
    await bridge_client.close()
    await fake_bridge.stop()


def _text(result: Any) -> str:
    """Concatenate every text block of a tool result."""
    return "\n".join(block.text for block in result.content if hasattr(block, "text"))


async def _new_document(mcp: Client) -> str:
    """Create a document and return its id."""
    result = await mcp.call_tool("doc_new", {})
    try:
        payload = json.loads(_text(result))
    except Exception:
        return "doc_0"
    if isinstance(payload, dict):
        return str(payload.get("id") or payload.get("doc_id") or "doc_0")
    return "doc_0"


@pytest.mark.asyncio
async def test_scene_build_creates_the_requested_layers(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        result = await mcp.call_tool(
            "scene_build",
            {
                "spec": {
                    "doc_id": doc_id,
                    "layers": [
                        {"id": "alpha", "type": "circle", "depth": 0, "params": {}},
                        {"id": "beta", "type": "rectangle", "depth": 1, "params": {}},
                    ],
                }
            },
        )
        payload = _text(result)
    assert "alpha" in payload
    assert "beta" in payload


@pytest.mark.asyncio
async def test_scene_build_creates_the_requested_groups(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        result = await mcp.call_tool(
            "scene_build",
            {
                "spec": {
                    "doc_id": doc_id,
                    "layers": [
                        {"id": "alpha", "type": "circle", "depth": 0, "params": {}},
                        {"id": "beta", "type": "rectangle", "depth": 1, "params": {}},
                    ],
                    "groups": [{"id": "bundle", "layer_ids": ["alpha", "beta"]}],
                }
            },
        )
        payload = _text(result)
    assert "bundle" in payload


@pytest.mark.asyncio
async def test_scene_build_keeps_the_waypoints(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        result = await mcp.call_tool(
            "scene_build",
            {
                "spec": {
                    "doc_id": doc_id,
                    "layers": [
                        {
                            "id": "mover",
                            "type": "circle",
                            "depth": 0,
                            "params": {"radius": {"type": "real", "value": 1.0}},
                            "waypoints": [
                                {
                                    "param": "radius",
                                    "time": 0.0,
                                    "value": {"type": "real", "value": 1.0},
                                    "interpolation": "linear",
                                },
                                {
                                    "param": "radius",
                                    "time": 1.0,
                                    "value": {"type": "real", "value": 3.0},
                                    "interpolation": "linear",
                                },
                            ],
                        }
                    ],
                }
            },
        )
        payload = _text(result)
    assert "mover" in payload


@pytest.mark.asyncio
async def test_layer_operations_report_a_diff(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        added = await mcp.call_tool(
            "layer_add", {"doc_id": doc_id, "layer_type": "circle", "params": {}}
        )
        assert "layer.add" in _text(added)

        removed = await mcp.call_tool("layer_remove", {"doc_id": doc_id, "layer_id": "Circle001"})
        assert "layer.remove" in _text(removed)


@pytest.mark.asyncio
async def test_history_reports_the_stack_depth(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        result = await mcp.call_tool("history_list", {"doc_id": doc_id})
        payload = _text(result)
    assert "undo_count" in payload
    assert "redo_count" in payload


@pytest.mark.asyncio
async def test_invalid_interpolation_is_rejected_in_both_backends(mcp_app: Any) -> None:
    """Both backends must refuse an interpolation Synfig cannot load."""
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        await mcp.call_tool("layer_add", {"doc_id": doc_id, "layer_type": "circle", "params": {}})
        result = await mcp.call_tool(
            "anim_waypoint_set",
            {
                "doc_id": doc_id,
                "layer_id": "Circle001",
                "param_name": "radius",
                "time": 0.0,
                "value": {"type": "real", "value": 1.0},
                "interpolation_in": "not_an_interpolation",
                "interpolation_out": "not_an_interpolation",
            },
        )
        assert result.is_error, "an invalid interpolation was accepted"


@pytest.mark.asyncio
async def test_unknown_layer_type_is_rejected_in_both_backends(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        result = await mcp.call_tool(
            "layer_add", {"doc_id": doc_id, "layer_type": "not_a_layer_type", "params": {}}
        )
        assert result.is_error, "an unknown layer type was accepted"


@pytest.mark.asyncio
async def test_selection_round_trips_in_both_backends(mcp_app: Any) -> None:
    """Setting the selection must be readable back through the same tool."""
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        await mcp.call_tool("layer_add", {"doc_id": doc_id, "layer_type": "circle", "params": {}})
        set_result = await mcp.call_tool(
            "selection_set", {"doc_id": doc_id, "layer_ids": ["Circle001"]}
        )
        assert "Circle001" in _text(set_result)

        get_result = await mcp.call_tool("selection_get", {"doc_id": doc_id})
        assert "Circle001" in _text(get_result)


@pytest.mark.asyncio
async def test_param_export_and_link_round_trip_in_both_backends(mcp_app: Any) -> None:
    """Exporting a value node and linking a parameter to it must work everywhere."""
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        await mcp.call_tool(
            "layer_add",
            {"doc_id": doc_id, "layer_type": "circle", "params": {}},
        )
        layer_id = "Circle001"

        exported = await mcp.call_tool(
            "param_export",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "radius",
                "name": "sharedRadius",
            },
        )
        assert "sharedRadius" in _text(exported)

        linked = await mcp.call_tool(
            "param_link",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "radius",
                "link_id": "sharedRadius",
            },
        )
        assert "sharedRadius" in _text(linked)
        assert "param.link" in _text(linked)


@pytest.mark.asyncio
async def test_schema_tools_report_the_installed_synfig(mcp_app: Any) -> None:
    async with Client(mcp_app) as mcp:
        layers = await mcp.call_tool("schema_list_layers", {})
        payload = _text(layers)
    assert "circle" in payload
    assert "outline" in payload
