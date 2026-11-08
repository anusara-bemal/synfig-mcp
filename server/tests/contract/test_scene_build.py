"""
Contract tests for Phase A1 declarative scene tools across both backends:
- scene_build (including dry_run and validation)
- scene_export_spec
- scene_summary
- synfig_help and synfig://guide/{topic} resource
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from mcp.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent, TextResourceContents

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
async def test_synfig_help_tool(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        res = await client.call_tool("synfig_help", {"topic": "overview"})
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)
        assert data["topic"] == "overview"
        assert "Synfig MCP Overview" in data["content"]
        assert "_security_notice" in data


@pytest.mark.asyncio
async def test_synfig_guide_resource(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        content = await client.read_resource("synfig://guide/declarative_build")
        assert content.contents
        first = content.contents[0]
        assert isinstance(first, TextResourceContents)
        assert "Declarative Scene Building" in first.text


@pytest.mark.asyncio
async def test_scene_build_basic(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Create a document first
        doc_res = await client.call_tool("doc_new", {"width": 320, "height": 240, "fps": 24.0})
        first = doc_res.content[0]
        assert isinstance(first, TextContent)
        doc_data = json.loads(first.text)
        doc_id = doc_data["id"]

        spec = {
            "version": "1.0",
            "doc_id": doc_id,
            "layers": [
                {
                    "id": "HeroCircle",
                    "type": "circle",
                    "params": {
                        "radius": {"type": "real", "value": 2.5},
                        "color": {"type": "color", "value": [1.0, 0.0, 0.0, 1.0]},
                    },
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
                },
                {
                    "id": "BackgroundRect",
                    "type": "rectangle",
                    "params": {
                        "color": {"type": "color", "value": [0.1, 0.1, 0.2, 1.0]},
                    },
                },
            ],
            "groups": [
                {
                    "id": "HeroGroup",
                    "layer_ids": ["HeroCircle"],
                }
            ],
        }

        # Test dry_run=True first
        dry_res = await client.call_tool("scene_build", {"spec": spec, "dry_run": True})
        assert dry_res.content
        first_dry = dry_res.content[0]
        assert isinstance(first_dry, TextContent)
        dry_data = json.loads(first_dry.text)
        assert dry_data.get("dry_run") is True
        assert dry_data.get("valid") is True
        diff = dry_data.get("diff", {})
        assert "HeroCircle" in diff.get("created", [])

        # Apply real build
        build_res = await client.call_tool("scene_build", {"spec": spec, "dry_run": False})
        assert build_res.content
        first_build = build_res.content[0]
        assert isinstance(first_build, TextContent)
        build_data = json.loads(first_build.text)
        assert build_data.get("diff", {}).get("action") == "scene.build"
        assert "HeroCircle" in build_data.get("diff", {}).get("created", [])


@pytest.mark.asyncio
async def test_scene_build_invalid_schema(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Pass invalid spec (missing doc_id, invalid layers format)
        bad_spec: dict[str, Any] = {
            "version": "invalid_version",
            "layers": "not_a_list",
        }
        res = await client.call_tool("scene_build", {"spec": bad_spec})
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)
        assert data.get("valid") is False or "Invalid" in data.get("error", "")


@pytest.mark.asyncio
async def test_scene_export_spec(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Create document
        doc_res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        first = doc_res.content[0]
        assert isinstance(first, TextContent)
        doc_id = json.loads(first.text)["id"]

        # Export spec
        export_res = await client.call_tool(
            "scene_export_spec",
            {"doc_id": doc_id, "scope": "canvas", "fields": ["layers", "canvas"]},
        )
        assert export_res.content
        first_exp = export_res.content[0]
        assert isinstance(first_exp, TextContent)
        exp_data = json.loads(first_exp.text)
        assert "layers" in exp_data
        assert "_security_notice" in exp_data


@pytest.mark.asyncio
async def test_scene_summary(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Create document
        doc_res = await client.call_tool("doc_new", {"width": 1920, "height": 1080, "fps": 24.0})
        first = doc_res.content[0]
        assert isinstance(first, TextContent)
        doc_id = json.loads(first.text)["id"]

        # Call scene_summary
        sum_res = await client.call_tool("scene_summary", {"doc_id": doc_id, "budget_tokens": 300})
        assert sum_res.content
        first_sum = sum_res.content[0]
        assert isinstance(first_sum, TextContent)
        sum_data = json.loads(first_sum.text)
        assert "canvas" in sum_data
        assert "1920x1080" in sum_data["canvas"]
        assert "_security_notice" in sum_data
