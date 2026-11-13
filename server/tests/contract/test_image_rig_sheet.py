"""
Contract: an image uploaded through the MCP client becomes rig parts.

The client cannot hand the server a path into its own filesystem, so it attaches
an ``ImageContent`` block (base64).  ``rig_sheet_from_image`` ingests that block,
hardens it into an authorized directory and slices it into named, rig-ready
parts with a manifest.  The test drives the public tool on both backends.
"""

from __future__ import annotations

import base64
import io
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from mcp.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent
from PIL import Image, ImageDraw

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer
from synfig_mcp.security.permissions import PermissionStore
from synfig_mcp.server import create_server


@pytest_asyncio.fixture(params=["headless", "live_fake"])
async def server(
    request: pytest.FixtureRequest,
) -> AsyncIterator[tuple[str, MCPServer]]:
    if request.param == "headless":
        yield ("headless", create_server(backend=HeadlessBackend(), profile="all"))
        return
    fake = FakeBridgeServer(port=0)
    await fake.start()
    client = BridgeClient(host=fake.host, port=fake.assigned_port, token=fake.token)
    await client.connect()
    try:
        yield ("live_fake", create_server(backend=LiveBackend(client=client), profile="all"))
    finally:
        await client.close()
        await fake.stop()


def _data(result: Any) -> dict[str, Any]:
    assert not result.is_error, result.content[0].text
    first = result.content[0]
    assert isinstance(first, TextContent)
    loaded: dict[str, Any] = json.loads(first.text)
    return loaded


def _sheet_b64() -> str:
    img = Image.new("RGBA", (260, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((20, 20, 100, 100), fill=(240, 200, 160, 255))
    draw.rectangle((150, 20, 240, 140), fill=(40, 90, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.fixture
def authorized(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> PermissionStore:
    fresh = PermissionStore()
    fresh.clear()
    fresh.grant(tmp_path)
    monkeypatch.setattr("synfig_mcp.security.permissions.permissions", fresh)
    monkeypatch.setattr(
        "synfig_mcp.security.sandbox.get_default_allowed_roots",
        lambda: [g.path for g in fresh.grants()],
    )
    return fresh


@pytest.mark.asyncio
async def test_uploaded_sheet_becomes_rig_parts(
    server: tuple[str, MCPServer], authorized: PermissionStore, tmp_path: Path
) -> None:
    _, app = server
    assert tmp_path.resolve() in authorized.roots()
    async with Client(app) as client:
        first = _data(
            await client.call_tool(
                "rig_sheet_from_image",
                {"image_base64": _sheet_b64(), "output_dir": str(tmp_path)},
            )
        )
        assert first["success"] is True
        assert first["ingested"]["source"] == "image_content"
        assert first["detected_parts"] == 2
        assert first["preview_base64"]

        named = _data(
            await client.call_tool(
                "rig_sheet_from_image",
                {
                    "image_base64": _sheet_b64(),
                    "output_dir": str(tmp_path),
                    "names": {"1": "head", "2": "torso"},
                    "preview": False,
                },
            )
        )
        assert [p["name"] for p in named["parts"]] == ["head", "torso"]
        assert named["parts"][0]["role"] == "head"
        assert named["parts"][0]["parent"] == "torso"
        assert named["rig_compatibility"]["level"] == "high"
        manifest = Path(named["manifest"])
        assert manifest.is_file()
        assert json.loads(manifest.read_text())["source"] == "image_content"


@pytest.mark.asyncio
async def test_uploaded_sheet_rejects_non_image(
    server: tuple[str, MCPServer],
    authorized: PermissionStore,  # noqa: ARG001 (grants tmp_path as a side effect)
    tmp_path: Path,
) -> None:
    _, app = server
    payload = base64.b64encode(b"not an image").decode()
    async with Client(app) as client:
        result = await client.call_tool(
            "rig_sheet_from_image", {"image_base64": payload, "output_dir": str(tmp_path)}
        )
    assert result.is_error
    assert "rejected" in result.content[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_upload_requires_exactly_one_source(
    server: tuple[str, MCPServer],
    authorized: PermissionStore,  # noqa: ARG001 (grants tmp_path as a side effect)
    tmp_path: Path,
) -> None:
    _, app = server
    async with Client(app) as client:
        result = await client.call_tool("rig_sheet_from_image", {"output_dir": str(tmp_path)})
    assert result.is_error
    assert "exactly one" in result.content[0].text  # type: ignore[union-attr]
