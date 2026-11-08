"""
Contract tests for Phase A4 Cut-out Characters and Storyboard tools across backends.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from mcp.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

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
        app = create_server(backend=backend, profile="all")
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
        app = create_server(backend=live_backend, profile="all")
        try:
            yield (mode, app)
        finally:
            await bridge_client.close()
            await fake_bridge.stop()


@pytest.mark.asyncio
async def test_character_rig_and_pose(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Create doc
        doc_res = await client.call_tool("doc_new", {"width": 320, "height": 240, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        rig_spec = {
            "character_id": "test_bot",
            "doc_id": doc_id,
            "parts": [
                {
                    "id": "torso",
                    "part_type": "torso",
                    "primitive_type": "rectangle",
                    "primitive_params": {"color": {"type": "color", "value": [0.2, 0.4, 0.8, 1.0]}},
                },
                {
                    "id": "head",
                    "part_type": "head",
                    "primitive_type": "circle",
                    "primitive_params": {"radius": {"type": "real", "value": 0.5}},
                },
            ],
            "bones": [
                {"name": "bone_root", "length": 1.0},
                {"name": "bone_head", "parent": "bone_root", "length": 0.5},
            ],
        }

        # Dry run
        dry_res = await client.call_tool(
            "character_rig_from_parts", {"spec": rig_spec, "dry_run": True}
        )
        assert dry_res.content
        first_dry = dry_res.content[0]
        assert isinstance(first_dry, TextContent)
        dry_data = json.loads(first_dry.text)
        assert dry_data["success"] is True
        assert dry_data["dry_run"] is True
        assert dry_data["parts_count"] == 2

        # Real assembly
        real_res = await client.call_tool(
            "character_rig_from_parts", {"spec": rig_spec, "dry_run": False}
        )
        assert real_res.content
        first_real = real_res.content[0]
        assert isinstance(first_real, TextContent)
        real_data = json.loads(first_real.text)
        assert real_data["success"] is True
        assert real_data["root_group"] == "Character_test_bot"

        # Apply pose
        pose_res = await client.call_tool(
            "character_pose_apply",
            {"doc_id": doc_id, "character_id": "test_bot", "pose_name": "punch", "time": 0.5},
        )
        assert pose_res.content
        first_pose = pose_res.content[0]
        assert isinstance(first_pose, TextContent)
        pose_data = json.loads(first_pose.text)
        assert pose_data["success"] is True
        assert pose_data["pose"] == "punch"


@pytest.mark.asyncio
async def test_character_motion_apply(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        doc_res = await client.call_tool("doc_new", {"width": 320, "height": 240, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        motion_res = await client.call_tool(
            "character_motion_apply",
            {
                "doc_id": doc_id,
                "character_id": "test_bot",
                "motion_name": "walk",
                "start_time": 0.0,
            },
        )
        assert motion_res.content
        first_m = motion_res.content[0]
        assert isinstance(first_m, TextContent)
        m_data = json.loads(first_m.text)
        assert m_data["success"] is True
        assert m_data["motion"] == "walk"
        assert len(m_data["keyframes"]) >= 4


@pytest.mark.asyncio
async def test_storyboard_from_script(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        doc_res = await client.call_tool("doc_new", {"width": 320, "height": 240, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        sb_spec = {
            "title": "Contract Storyboard",
            "doc_id": doc_id,
            "fps": 24.0,
            "shots": [
                {
                    "shot_id": "shot_01",
                    "description": "Hero arrives on rooftop.",
                    "duration_seconds": 2.0,
                    "camera_movement": "pan_left",
                },
                {
                    "shot_id": "shot_02",
                    "description": "Dramatic focus on eyes.",
                    "duration_seconds": 1.5,
                    "camera_movement": "zoom_in",
                },
            ],
        }

        sb_res = await client.call_tool(
            "storyboard_from_script", {"spec": sb_spec, "dry_run": False}
        )
        assert sb_res.content
        first_sb = sb_res.content[0]
        assert isinstance(first_sb, TextContent)
        sb_data = json.loads(first_sb.text)
        assert sb_data["success"] is True
        assert sb_data["total_shots"] == 2
        assert sb_data["total_duration_seconds"] == 3.5
        assert len(sb_data["shots"]) == 2
        assert sb_data["shots"][0]["camera"] == "pan_left"
