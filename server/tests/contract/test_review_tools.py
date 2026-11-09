"""
Contract tests for Phase A2 Visual Review Loop tools:
- review_frame
- review_sequence
- review_compare
- synfig://rubrics/{style} resource
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from mcp.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent, TextResourceContents
from PIL import Image

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.cli.runner import CliRunner
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer
from synfig_mcp.server import create_server


class _FakeRenderCliRunner(CliRunner):
    """Hermetic CLI stub that renders a deterministic PNG without invoking Synfig."""

    async def render_frame(
        self,
        sif_path: Path,
        output_path: Path,
        time: float | str = 0.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
        antialias: int = 2,
    ) -> bool:
        del sif_path, time, target, antialias
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (width or 160, height or 120), (80, 120, 200)).save(output_path)
        return True


@pytest_asyncio.fixture(params=["headless", "live_fake"])
async def mcp_server(request: pytest.FixtureRequest) -> AsyncIterator[tuple[str, MCPServer]]:
    """Yields backend mode string ('headless' or 'live_fake') and configured MCPServer."""
    mode: str = request.param
    if mode == "headless":
        backend = HeadlessBackend(runner=_FakeRenderCliRunner())
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
async def test_rubric_resource_contract(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        content = await client.read_resource("synfig://rubrics/shonen_action")
        assert content.contents
        first = content.contents[0]
        assert isinstance(first, TextResourceContents)
        assert "Shonen Action" in first.text
        assert "Speed Lines" in first.text


@pytest.mark.asyncio
async def test_review_frame_tool(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Create doc with a layer
        doc_res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        # Review frame
        res = await client.call_tool(
            "review_frame",
            {"doc_id": doc_id, "time": 0.0, "width": 160, "height": 120},
        )
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)

        assert "image_base64" in data
        assert len(data["image_base64"]) > 50
        assert "metrics" in data
        assert "empty_canvas" in data["metrics"]
        assert "dominant_palette" in data["metrics"]
        assert "_security_notice" in data


@pytest.mark.asyncio
async def test_review_sequence_tool(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        doc_res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        res = await client.call_tool(
            "review_sequence",
            {
                "doc_id": doc_id,
                "start_time": 0.0,
                "end_time": 0.5,
                "frame_count": 3,
                "width": 160,
                "height": 120,
            },
        )
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)

        assert "contact_sheet_base64" in data
        assert "strobe_check" in data
        assert "motion_stats" in data
        assert "_security_notice" in data


@pytest.mark.asyncio
async def test_review_compare_tool(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        doc_res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        res = await client.call_tool(
            "review_compare",
            {
                "doc_id_a": doc_id,
                "time_a": 0.0,
                "doc_id_b": doc_id,
                "time_b": 0.5,
                "width": 160,
                "height": 120,
            },
        )
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)

        assert "ssim" in data
        assert "heatmap_composite_base64" in data
        assert "_security_notice" in data
