"""
Contract: the rig sheet preview reaches the client as an image, not as a blob.

A 2K sheet used to be previewed as a base64 PNG inside the tool result.  That
alone was over the 1 MB a client accepts, so the whole call was rejected and
the agent lost the numbered preview it needs to name the parts.  The preview
now travels as an MCP image block (and is written to disk), and the JSON stays
small.
"""

from __future__ import annotations

import json
import random
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import ImageContent, TextContent
from PIL import Image, ImageDraw

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server

#: The ceiling MCP clients enforce on a single tool result.
CLIENT_RESULT_LIMIT = 1024 * 1024


@pytest_asyncio.fixture
async def server() -> AsyncIterator[MCPServer]:
    yield create_server(backend=HeadlessBackend(), profile="all")


def _text(result: Any) -> str:
    """The JSON text of a tool result (the first content block)."""
    first = result.content[0]
    assert isinstance(first, TextContent)
    return first.text


def _noisy_sheet(path: Path) -> Path:
    """A detailed 2K sheet: the worst case for a lossless preview."""
    image = Image.new("RGB", (2048, 2048), (250, 250, 250))
    draw = ImageDraw.Draw(image)
    for index in range(8):
        draw.ellipse(
            (
                60 + (index % 4) * 480,
                60 + (index // 4) * 900,
                420 + (index % 4) * 480,
                840 + (index // 4) * 900,
            ),
            fill=(180 + index * 7, 90, 160),
        )
    pixels = image.load()
    rng = random.Random(3)
    for _ in range(200_000):
        pixels[rng.randrange(2048), rng.randrange(2048)] = (
            rng.randrange(256),
            rng.randrange(256),
            rng.randrange(256),
        )
    image.save(path)
    return path


@pytest.mark.asyncio
async def test_preview_arrives_as_an_image_block(server: MCPServer, tmp_path: Path) -> None:
    sheet = _noisy_sheet(tmp_path / "sheet.png")
    async with Client(server) as client:
        result = await client.call_tool("rig_sheet_slice", {"file_path": str(sheet)})

    assert not result.is_error, _text(result)

    text = result.content[0]
    assert isinstance(text, TextContent)
    data: dict[str, Any] = json.loads(text.text)
    assert "preview_base64" not in data, "the preview must not be inlined in the JSON"
    assert data["detected_parts"] >= 1
    assert data["preview_mime"] in {"image/png", "image/jpeg"}

    images = [block for block in result.content if isinstance(block, ImageContent)]
    assert len(images) == 1, "the numbered preview must be delivered as an image"
    assert images[0].mime_type == data["preview_mime"]

    preview_file = Path(data["preview_path"])
    assert preview_file.is_file()
    assert preview_file.stat().st_size == data["preview_bytes"]

    # The whole result has to stay below what a client accepts.
    assert len(result.model_dump_json(by_alias=True)) < CLIENT_RESULT_LIMIT


@pytest.mark.asyncio
async def test_named_slice_without_preview_stays_json(server: MCPServer, tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    image = Image.new("RGBA", (260, 160), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((20, 20, 120, 120), fill=(240, 200, 160, 255))
    image.save(sheet)
    async with Client(server) as client:
        result = await client.call_tool(
            "rig_sheet_slice",
            {"file_path": str(sheet), "names": {"1": "head"}, "preview": False},
        )

    assert not result.is_error, _text(result)
    assert isinstance(result.content[0], TextContent)
    data: dict[str, Any] = json.loads(result.content[0].text)
    assert "preview_base64" not in data
    assert not [block for block in result.content if isinstance(block, ImageContent)]
