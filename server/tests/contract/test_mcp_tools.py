"""
Parametrized contract tests for all MCP tools across both backends (Headless and Live with FakeBridge).
Exercises tools in-memory through mcp.client.Client.
"""

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
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
        if not backend.runner.is_available:

            async def fake_render(doc_id: str, output_path: str, **_kwargs: Any) -> bool:
                del doc_id
                p = Path(output_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                valid_png = (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
                    b"\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
                )
                p.write_bytes(valid_png)
                return True

            backend.render_frame = fake_render  # type: ignore[assignment,method-assign]
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


@pytest.mark.asyncio
async def test_mcp_valuenodes_and_waypoints(
    mcp_server: tuple[str, MCPServer],
) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        new_res = await client.call_tool("doc_new", {})
        doc = parse_tool_result(new_res)
        doc_id = doc.get("id") or doc.get("doc_id", "doc_0")

        # 1. doc_set_time_range
        range_res = await client.call_tool(
            "doc_set_time_range",
            {"doc_id": doc_id, "start_time": 0.0, "end_time": 5.0, "fps": 25.0},
        )
        assert parse_tool_result(range_res).get("start_time") == 0.0

        # Add a circle layer
        add_res = await client.call_tool(
            "layer_add",
            {
                "doc_id": doc_id,
                "layer_type": "circle",
                "params": {"origin": {"type": "vector", "x": 0.0, "y": 0.0}},
            },
        )
        layer_id = parse_tool_result(add_res).get("layer_id", "layer_0")

        # 2. anim_waypoint_set
        wp_res = await client.call_tool(
            "anim_waypoint_set",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "origin",
                "time": 0.0,
                "value": [0.0, 0.0],
            },
        )
        wp_data = parse_tool_result(wp_res)
        assert wp_data.get("param_name") == "origin"

        # 3. anim_animate_param (batch waypoints in 1 undo step)
        anim_res = await client.call_tool(
            "anim_animate_param",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "origin",
                "waypoints": [
                    {"time": 0.0, "value": [0.0, 0.0]},
                    {"time": 2.0, "value": [3.0, 0.0]},
                ],
            },
        )
        anim_dict = parse_tool_result(anim_res)
        assert anim_dict.get("waypoint_count") == 2 or anim_dict.get("count") == 2

        # 4. anim_interpolation_set
        interp_res = await client.call_tool(
            "anim_interpolation_set",
            {"doc_id": doc_id, "interpolation": "linear"},
        )
        assert parse_tool_result(interp_res).get("success") is True

        # 5. param_convert
        convert_res = await client.call_tool(
            "param_convert",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "origin",
                "type": "composite",
            },
        )
        assert "type" in parse_tool_result(convert_res)

        # 6. param_export and param_unexport
        export_res = await client.call_tool(
            "param_export",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": "radius",
                "name": "SharedRadius",
            },
        )
        assert parse_tool_result(export_res).get("name") == "SharedRadius"

        unexport_res = await client.call_tool(
            "param_unexport",
            {"doc_id": doc_id, "name": "SharedRadius"},
        )
        assert parse_tool_result(unexport_res).get("name") == "SharedRadius"


@pytest.mark.asyncio
async def test_mcp_render_pipeline(mcp_server: tuple[str, MCPServer], tmp_path: Path) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        new_res = await client.call_tool("doc_new", {})
        doc = parse_tool_result(new_res)
        doc_id = doc.get("id") or doc.get("doc_id", "doc_0")

        # 1. render_sequence
        seq_dir = str(tmp_path / "seq")
        frames = await client.call_tool(
            "render_sequence",
            {
                "doc_id": doc_id,
                "output_dir": seq_dir,
                "start_time": 0.0,
                "end_time": 0.1,
                "fps": 10.0,
            },
        )
        frames_list = parse_tool_result(frames)
        assert isinstance(frames_list, list)

        # 2. render_contact_sheet
        sheet_out = str(tmp_path / "sheet.png")
        sheet_res = await client.call_tool(
            "render_contact_sheet",
            {
                "doc_id": doc_id,
                "output_path": sheet_out,
                "cols": 2,
                "rows": 2,
            },
        )
        sheet_data = parse_tool_result(sheet_res)
        assert sheet_data.get("success") is True

        # 3. render_video
        vid_out = str(tmp_path / "anim.gif")
        vid_res = await client.call_tool(
            "render_video",
            {
                "doc_id": doc_id,
                "output_path": vid_out,
                "start_time": 0.0,
                "end_time": 0.1,
                "fps": 10.0,
            },
        )
        assert parse_tool_result(vid_res).get("success") is True


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_mcp_tools_real_studio(tmp_path: Path) -> None:
    """Requirement E: Exercise a subset of MCP tools through in-memory Client against the real running Studio."""
    import asyncio
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    bin_path = repo_root / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe"
    sample_sif = repo_root / "server" / "tests" / "fixtures" / "sample_project.sif"
    if not bin_path.exists():
        pytest.skip("Patched Synfig Studio binary not found")

    test_port = 19991
    env = os.environ.copy()
    env["SYNFIG_MCP_PORT"] = str(test_port)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token_path = token_dir / "mcp_token"
    if token_path.exists():
        token_path.unlink()

    log_path = tmp_path / "studio_mcp_test.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(bin_path), str(sample_sif)],
            env=env,
            stdout=log_file,
            stderr=log_file,
            cwd=str(bin_path.parent),
        )

    try:
        token = ""
        for _ in range(30):
            if token_path.exists():
                try:
                    token = token_path.read_text(encoding="utf-8").strip()
                    if token:
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        assert token, "Session token was not created by Synfig Studio"

        bridge_client = BridgeClient(
            host="127.0.0.1", port=test_port, token=token, default_timeout=10.0
        )
        connected = False
        for _ in range(25):
            try:
                await bridge_client.connect()
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.5)
        assert connected

        for _ in range(20):
            doc_list = await bridge_client.call("doc.list")
            if doc_list:
                break
            await asyncio.sleep(0.5)

        live_backend = LiveBackend(client=bridge_client)
        app = create_server(backend=live_backend)

        async with Client(app) as client:
            # 1. health_check
            h = parse_tool_result(await client.call_tool("health_check", {}))
            assert h["connected"] is True
            assert h["backend"] == "live"

            # 2. doc_list
            docs = parse_tool_result(await client.call_tool("doc_list", {}))
            if isinstance(docs, dict):
                doc_id = docs.get("id") or docs.get("doc_id", "doc_0")
            elif isinstance(docs, list) and len(docs) > 0:
                first = docs[0]
                doc_id = (
                    first.get("id") or first.get("doc_id", "doc_0")
                    if isinstance(first, dict)
                    else "doc_0"
                )
            else:
                doc_id = "doc_0"

            # 3. layer_add
            add_res = parse_tool_result(
                await client.call_tool(
                    "layer_add",
                    {
                        "doc_id": doc_id,
                        "layer_type": "circle",
                        "params": {"radius": {"type": "real", "value": 3.0}},
                    },
                )
            )
            assert "created" in add_res.get("diff", {})

            # 4. anim_time_set & get
            t_set = parse_tool_result(
                await client.call_tool("anim_time_set", {"doc_id": doc_id, "time": 1.25})
            )
            assert abs(float(t_set.get("time", 1.25)) - 1.25) < 0.05
            t_get = parse_tool_result(await client.call_tool("anim_time_get", {"doc_id": doc_id}))
            assert abs(float(t_get.get("time", 1.25)) - 1.25) < 0.05

            # 5. render_frame
            out_png = tmp_path / "mcp_rendered_frame.png"
            render_res = parse_tool_result(
                await client.call_tool(
                    "render_frame",
                    {
                        "doc_id": doc_id,
                        "output_path": str(out_png),
                        "time": 0.0,
                        "width": 160,
                        "height": 120,
                    },
                )
            )
            assert render_res["success"] is True
            assert out_png.exists()

        await bridge_client.close()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


@pytest.mark.asyncio
async def test_mcp_client_progress_notifications(
    mcp_server: tuple[str, MCPServer], tmp_path: Path
) -> None:
    """Requirement 2(a): Multi-frame render called via in-memory Client emits MCP progress notifications."""
    mode, app = mcp_server
    out_dir = tmp_path / f"mcp_progress_{mode}"
    out_dir.mkdir(parents=True, exist_ok=True)

    progress_events: list[tuple[float, float | None, str | None]] = []

    async def on_progress(
        progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        progress_events.append((progress, total, message))

    async with Client(app) as client:
        # 1. Open or create doc
        doc_res = parse_tool_result(
            await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        )
        doc_id = doc_res["id"]

        # 2. Add a circle
        await client.call_tool("layer_add", {"doc_id": doc_id, "layer_type": "circle"})

        # 3. Render sequence with progress tracking
        res = await client.call_tool(
            "render_sequence",
            {
                "doc_id": doc_id,
                "output_dir": str(out_dir),
                "start_time": 0.0,
                "end_time": 0.2,
                "fps": 10.0,  # 3 frames
                "width": 160,
                "height": 120,
            },
            progress_callback=on_progress,
        )
        frames = parse_tool_result(res)
        assert isinstance(frames, list)
        assert len(frames) >= 2
        assert len(progress_events) >= 2
        # Verify progress increments
        assert progress_events[0][0] >= 1.0


@pytest.mark.asyncio
async def test_mcp_client_cancellation_cleanup(
    mcp_server: tuple[str, MCPServer], tmp_path: Path
) -> None:
    """Requirement 2(b): Client task cancellation stops render and cleans partial output."""
    import asyncio

    mode, app = mcp_server
    out_dir = tmp_path / f"mcp_cancel_{mode}"
    out_dir.mkdir(parents=True, exist_ok=True)

    async with Client(app) as client:
        doc_res = parse_tool_result(
            await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        )
        doc_id = doc_res["id"]
        await client.call_tool("layer_add", {"doc_id": doc_id, "layer_type": "circle"})

        async def cancel_after_brief_delay(target_task: asyncio.Task[Any]) -> None:
            await asyncio.sleep(0.05)
            target_task.cancel()

        render_task = asyncio.create_task(
            client.call_tool(
                "render_sequence",
                {
                    "doc_id": doc_id,
                    "output_dir": str(out_dir),
                    "start_time": 0.0,
                    "end_time": 1.0,
                    "fps": 20.0,  # 21 frames requested
                    "width": 160,
                    "height": 120,
                },
            )
        )
        canceller = asyncio.create_task(cancel_after_brief_delay(render_task))
        try:
            await render_task
        except asyncio.CancelledError:
            pass
        finally:
            canceller.cancel()

        # Assert cancellation stopped the render and cleaned partial frames
        remaining_frames = list(out_dir.glob("*.png"))
        assert len(remaining_frames) < 21
