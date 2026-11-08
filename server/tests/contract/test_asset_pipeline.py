"""
Contract tests for Phase A5 Licensed Asset Pipeline across backends.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

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
async def test_asset_search_mock(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        res = await client.call_tool("asset_search", {"query": "cloud", "provider": "mock"})
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)
        assert "results" in data
        assert len(data["results"]) >= 1
        assert data["results"][0]["license"] == "cc0"
        assert "_security_notice" in data


@pytest.mark.asyncio
async def test_asset_preview_mock(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        res = await client.call_tool(
            "asset_preview", {"asset_id": "mock_cloud_01", "provider": "mock"}
        )
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        data = json.loads(first.text)
        assert data["success"] is True
        assert "thumbnail_base64" in data
        assert len(data["thumbnail_base64"]) > 20


@pytest.mark.asyncio
async def test_asset_import_local_rights_validation(
    mcp_server: tuple[str, MCPServer], tmp_path: Path
) -> None:
    _, app = mcp_server
    test_img = tmp_path / "custom_prop.png"
    # Write 1x1 valid png
    test_img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
        b"\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    async with Client(app) as client:
        # Invalid rights declaration must be rejected
        bad_res = await client.call_tool(
            "asset_import_local",
            {
                "file_path": str(test_img),
                "rights": "unknown_rights",
                "title": "Custom Prop",
            },
        )
        assert bad_res.content
        first_bad = bad_res.content[0]
        assert isinstance(first_bad, TextContent)
        bad_data = json.loads(first_bad.text)
        assert bad_data["success"] is False
        assert "Invalid rights declaration" in bad_data["error"]

        # Valid rights declaration must succeed
        good_res = await client.call_tool(
            "asset_import_local",
            {
                "file_path": str(test_img),
                "rights": "own",
                "title": "Original Character Hat",
                "creator": "Project Artist",
            },
        )
        assert good_res.content
        first_good = good_res.content[0]
        assert isinstance(first_good, TextContent)
        good_data = json.loads(first_good.text)
        assert good_data["success"] is True
        assert good_data["rights"] == "own"
        assert len(good_data["sha256"]) == 64
