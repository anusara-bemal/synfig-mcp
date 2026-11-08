"""
Contract tests for Phase A3 Effects Recipes and Styles across backends.
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
async def test_recipe_list_and_info(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        res = await client.call_tool("recipe_list", {})
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        recipes_data = json.loads(first.text)
        assert "recipes" in recipes_data
        recipes = recipes_data["recipes"]
        assert len(recipes) >= 12

        info_res = await client.call_tool("recipe_info", {"name": "vignette"})
        assert info_res.content
        first_info = info_res.content[0]
        assert isinstance(first_info, TextContent)
        manifest = json.loads(first_info.text)
        assert manifest["name"] == "vignette"
        assert manifest["category"] == "lens"
        assert "_security_notice" in manifest


@pytest.mark.asyncio
async def test_recipe_apply_dry_run_and_real(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        # Create doc
        doc_res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        # Dry run recipe apply
        dry_res = await client.call_tool(
            "recipe_apply",
            {"doc_id": doc_id, "name": "vignette", "params": {"opacity": 0.8}, "dry_run": True},
        )
        assert dry_res.content
        first_dry = dry_res.content[0]
        assert isinstance(first_dry, TextContent)
        dry_data = json.loads(first_dry.text)
        assert dry_data["success"] is True
        assert dry_data["dry_run"] is True
        assert len(dry_data["created_layers"]) == 1

        # Real recipe apply
        real_res = await client.call_tool(
            "recipe_apply",
            {"doc_id": doc_id, "name": "vignette", "params": {"opacity": 0.8}, "dry_run": False},
        )
        assert real_res.content
        first_real = real_res.content[0]
        assert isinstance(first_real, TextContent)
        real_data = json.loads(first_real.text)
        assert real_data["success"] is True
        assert len(real_data["created_layers"]) == 1
        assert "Vignette" in real_data["created_layers"][0]


@pytest.mark.asyncio
async def test_style_presets_and_apply(mcp_server: tuple[str, MCPServer]) -> None:
    _, app = mcp_server
    async with Client(app) as client:
        res = await client.call_tool("style_list", {})
        assert res.content
        first = res.content[0]
        assert isinstance(first, TextContent)
        styles_data = json.loads(first.text)
        assert "styles" in styles_data
        styles = styles_data["styles"]
        assert len(styles) >= 5

        # Get style info
        style_info = await client.call_tool("style_get", {"name": "dark_fantasy"})
        assert style_info.content
        first_si = style_info.content[0]
        assert isinstance(first_si, TextContent)
        preset = json.loads(first_si.text)
        assert preset["name"] == "dark_fantasy"
        assert preset["contrast"] == "crushed"

        # Apply style to document
        doc_res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        doc_id = json.loads(doc_res.content[0].text)["id"]  # type: ignore[union-attr]

        apply_res = await client.call_tool(
            "style_apply", {"doc_id": doc_id, "name": "dark_fantasy"}
        )
        assert apply_res.content
        first_sa = apply_res.content[0]
        assert isinstance(first_sa, TextContent)
        apply_data = json.loads(first_sa.text)
        assert apply_data["success"] is True
        assert len(apply_data["applied_recipes"]) == 3
