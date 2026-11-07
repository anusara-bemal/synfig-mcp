"""
Parametrized contract tests for all MCP tools across both backends (Headless and Live with FakeBridge).
Exercises tools in-memory through mcp.client.Client.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from mcp.client import Client
from mcp.server.mcpserver import MCPServer

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer
from synfig_mcp.server import create_server


@pytest_asyncio.fixture(params=["headless", "live_fake"])
async def mcp_server(request: pytest.FixtureRequest) -> AsyncIterator[tuple[str, MCPServer]]:
    """Yields backend mode string ('headless' or 'live_fake') and configured MCPServer."""
    mode: str = request.param
    if mode == "headless":
        backend = HeadlessBackend()
        app = create_server(backend=backend)
        yield (mode, app)
    else:
        fake_bridge = FakeBridgeServer(port=0)
        await fake_bridge.start()

        bridge_client = BridgeClient(
            host=fake_bridge.host,
            port=fake_bridge.assigned_port,
            token=fake_bridge.token,
        )
        await bridge_client.connect()

        live_backend = LiveBackend(client=bridge_client)
        app = create_server(backend=live_backend)
        yield (mode, app)

        await bridge_client.close()
        await fake_bridge.stop()


def parse_tool_result(res: Any) -> Any:
    """Helper to extract and parse JSON text content from an MCP CallToolResult."""
    assert len(res.content) > 0
    if len(res.content) == 1:
        text = res.content[0].text
        try:
            return json.loads(text)
        except Exception:
            return text
    return [c.text for c in res.content]


# ---------------------------------------------------------------------------
# Test Cases Parametrized Across Both Backends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_tools_listing_and_annotations(
    mcp_server: tuple[str, MCPServer],
) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        res = await client.list_tools()
        tools = res.tools
        assert len(tools) >= 25

        tool_names = [t.name for t in tools]
        assert "health_check" in tool_names
        assert "doc_list" in tool_names
        assert "doc_new" in tool_names
        assert "layer_add" in tool_names
        assert "param_set" in tool_names
        assert "history_undo" in tool_names
        assert "schema_list_layers" in tool_names

        # Verify ToolAnnotations hints
        health_tool = next(t for t in tools if t.name == "health_check")
        assert health_tool.annotations is not None
        assert health_tool.annotations.read_only_hint is True
        assert health_tool.annotations.destructive_hint is False

        layer_add_tool = next(t for t in tools if t.name == "layer_add")
        assert layer_add_tool.annotations is not None
        assert layer_add_tool.annotations.read_only_hint is False
        assert layer_add_tool.annotations.destructive_hint is True


@pytest.mark.asyncio
async def test_mcp_health_check(mcp_server: tuple[str, MCPServer]) -> None:
    mode, app = mcp_server
    async with Client(app) as client:
        res = await client.call_tool("health_check", {})
        data = parse_tool_result(res)

        assert "backend" in data
        assert data["connected"] is True
        if mode == "headless":
            assert data["backend"] == "headless"
        else:
            assert data["backend"] == "live"


@pytest.mark.asyncio
async def test_mcp_doc_workflow(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # 1. doc_new
        new_res = await client.call_tool("doc_new", {"width": 1280, "height": 720, "fps": 30.0})
        new_doc = parse_tool_result(new_res)
        doc_id = new_doc.get("id") or new_doc.get("doc_id", "doc_0")
        assert new_doc["width"] == 1280

        # 2. doc_list
        list_res = await client.call_tool("doc_list", {})
        docs = parse_tool_result(list_res)
        assert len(docs) >= 1

        # 3. doc_info
        info_res = await client.call_tool("doc_info", {"doc_id": doc_id})
        info = parse_tool_result(info_res)
        assert info["width"] == 1280

        # 4. doc_set_properties
        set_res = await client.call_tool(
            "doc_set_properties", {"doc_id": doc_id, "width": 1920, "height": 1080}
        )
        updated = parse_tool_result(set_res)
        assert updated["width"] == 1920


@pytest.mark.asyncio
async def test_mcp_layer_and_param_workflow(
    mcp_server: tuple[str, MCPServer],
) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # doc setup
        new_res = await client.call_tool("doc_new", {})
        doc = parse_tool_result(new_res)
        doc_id = doc.get("id") or doc.get("doc_id", "doc_0")

        # 1. layer_add
        add_res = await client.call_tool(
            "layer_add",
            {
                "doc_id": doc_id,
                "layer_type": "circle",
                "description": "MyCircle",
                "params": {"radius": {"type": "real", "value": 2.0}},
            },
        )
        layer = parse_tool_result(add_res)
        layer_id = layer.get("layer_id") or "MyCircle"
        assert layer["layer_type"] == "circle"

        # 2. param_get
        p_res = await client.call_tool(
            "param_get", {"doc_id": doc_id, "layer_id": layer_id, "param_name": "radius"}
        )
        p_val = parse_tool_result(p_res)
        assert "value" in p_val or "type" in p_val

        # 3. param_set
        set_p_res = await client.call_tool(
            "param_set",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "radius",
                "value": {"type": "real", "value": 4.5},
            },
        )
        set_p = parse_tool_result(set_p_res)
        assert set_p["after"]["value"] == 4.5

        # 4. scene_tree
        tree_res = await client.call_tool("scene_tree", {"doc_id": doc_id})
        tree = parse_tool_result(tree_res)
        assert "layers" in tree
        assert len(tree["layers"]) >= 1

        # 5. layer_reorder
        reorder_res = await client.call_tool(
            "layer_reorder", {"doc_id": doc_id, "layer_id": layer_id, "new_depth": 0}
        )
        reorder = parse_tool_result(reorder_res)
        assert reorder["depth"] == 0

        # 6. layer_remove
        del_res = await client.call_tool("layer_remove", {"doc_id": doc_id, "layer_id": layer_id})
        deleted = parse_tool_result(del_res)
        assert deleted["removed"] is True


@pytest.mark.asyncio
async def test_mcp_timeline_and_keyframes(
    mcp_server: tuple[str, MCPServer],
) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        new_res = await client.call_tool("doc_new", {})
        doc = parse_tool_result(new_res)
        doc_id = doc.get("id") or doc.get("doc_id", "doc_0")

        # 1. anim_time_set and anim_time_get
        await client.call_tool("anim_time_set", {"doc_id": doc_id, "time": 1.5})
        t_res = await client.call_tool("anim_time_get", {"doc_id": doc_id})
        t_val = parse_tool_result(t_res)
        assert t_val["time"] == 1.5

        # 2. anim_keyframe_add
        kf_res = await client.call_tool(
            "anim_keyframe_add", {"doc_id": doc_id, "time": 1.5, "description": "Jump"}
        )
        kf = parse_tool_result(kf_res)
        assert "time" in kf

        # 3. anim_keyframe_list
        kfs_res = await client.call_tool("anim_keyframe_list", {"doc_id": doc_id})
        kfs = parse_tool_result(kfs_res)
        assert len(kfs) >= 1

        # 4. anim_keyframe_remove
        del_kf_res = await client.call_tool("anim_keyframe_remove", {"doc_id": doc_id, "time": 1.5})
        del_kf = parse_tool_result(del_kf_res)
        assert del_kf["removed"] is True


@pytest.mark.asyncio
async def test_mcp_history_undo_redo(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        new_res = await client.call_tool("doc_new", {})
        doc = parse_tool_result(new_res)
        doc_id = doc.get("id") or doc.get("doc_id", "doc_0")

        # Mutate
        await client.call_tool("layer_add", {"doc_id": doc_id, "layer_type": "circle"})

        # Undo
        undo_res = await client.call_tool("history_undo", {"doc_id": doc_id})
        undo = parse_tool_result(undo_res)
        assert undo["success"] is True

        # Redo
        redo_res = await client.call_tool("history_redo", {"doc_id": doc_id})
        redo = parse_tool_result(redo_res)
        assert redo["success"] is True

        # History list
        h_res = await client.call_tool("history_list", {"doc_id": doc_id})
        h = parse_tool_result(h_res)
        assert "undo_count" in h


@pytest.mark.asyncio
async def test_mcp_schema_tools(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # List layers
        layers_res = await client.call_tool("schema_list_layers", {})
        layers = parse_tool_result(layers_res)
        assert "circle" in layers
        assert "rectangle" in layers

        # Get layer details
        circle_res = await client.call_tool("schema_get_layer", {"layer_type": "circle"})
        circle_info = parse_tool_result(circle_res)
        assert circle_info["name"] == "circle"
        assert "radius" in circle_info["params"]

        # Valuenodes, targets, renderers
        vn_res = await client.call_tool("schema_list_valuenodes", {})
        assert len(parse_tool_result(vn_res)) > 0

        target_res = await client.call_tool("schema_list_targets", {})
        assert "png" in parse_tool_result(target_res)

        renderer_res = await client.call_tool("schema_list_renderers", {})
        assert len(parse_tool_result(renderer_res)) > 0


@pytest.mark.asyncio
async def test_mcp_invalid_inputs_and_errors(
    mcp_server: tuple[str, MCPServer],
) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Querying non-existent document
        info_res = await client.call_tool("doc_info", {"doc_id": "non_existent_doc_id"})
        info = parse_tool_result(info_res)
        assert "error" in info or "doc_id" in info

        # Querying non-existent layer type schema
        bad_schema_res = await client.call_tool("schema_get_layer", {"layer_type": "unknown_xxx"})
        bad_schema = parse_tool_result(bad_schema_res)
        assert "error" in bad_schema
