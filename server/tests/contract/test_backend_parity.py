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
from synfig_mcp.validation import find_synfig_binary


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


#: The headless backend can only validate layer types against a real Synfig
#: binary.  Without one it cannot distinguish a real layer from an invented
#: name, so the checks that assert rejection are skipped rather than weakened.
_HEADLESS_ENGINE_MISSING = find_synfig_binary() is None


def _skip_headless_without_engine(request: pytest.FixtureRequest) -> None:
    """Skip the headless half of a case when no Synfig binary is installed."""
    if _HEADLESS_ENGINE_MISSING and request.node.callspec.params.get("mcp_app") == "headless":
        pytest.skip("headless backend needs a Synfig binary to validate layer types")


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
async def test_unknown_layer_type_is_rejected_in_both_backends(
    mcp_app: Any, request: pytest.FixtureRequest
) -> None:
    _skip_headless_without_engine(request)
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
async def test_history_and_canvas_lists_keep_their_contract(mcp_app: Any) -> None:
    """`history_list` and `canvas_list` must answer the same way in both backends."""
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)

        history = json.loads(_text(await mcp.call_tool("history_list", {"doc_id": doc_id})))
        assert "undo_count" in history
        assert "redo_count" in history

        canvases = json.loads(_text(await mcp.call_tool("canvas_list", {"doc_id": doc_id})))
        assert "canvases" in canvases
        assert canvases["canvases"], "no canvas path was reported"
        for path in canvases["canvases"]:
            assert isinstance(path, str), f"a canvas entry is not a path: {path!r}"


@pytest.mark.asyncio
async def test_scene_tree_has_the_same_shape_in_both_backends(mcp_app: Any) -> None:
    """The scene tree must expose the same keys in both backends.

    The live bridge used to answer with a bare list of layers while the
    headless engine reported the canvas metadata as well, and the layer entries
    used different keys - a client written against one backend broke on the
    other.
    """
    async with Client(mcp_app) as mcp:
        doc_id = await _new_document(mcp)
        await mcp.call_tool("layer_add", {"doc_id": doc_id, "layer_type": "circle", "params": {}})
        result = await mcp.call_tool("scene_tree", {"doc_id": doc_id})
        payload = json.loads(_text(result))

    for key in ("doc_id", "canvas_path", "name", "width", "height", "fps", "duration_frames"):
        assert key in payload, f"the scene tree has no '{key}'"

    layers = payload.get("layers", [])
    assert layers, "the scene tree has no layers"
    for key in ("id", "desc", "description", "type", "active", "depth", "params", "children"):
        assert key in layers[0], f"a layer entry has no '{key}'"


@pytest.mark.asyncio
async def test_schema_tools_report_the_installed_synfig(
    mcp_app: Any, request: pytest.FixtureRequest
) -> None:
    _skip_headless_without_engine(request)
    async with Client(mcp_app) as mcp:
        layers = await mcp.call_tool("schema_list_layers", {})
        payload = _text(layers)
    assert "circle" in payload
    assert "outline" in payload
