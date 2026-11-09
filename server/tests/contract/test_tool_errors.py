"""Tool-level error surfacing tests.

The MCP SDK converts uncaught exceptions into a generic
``Error executing tool <name>`` crash. Synfig errors must instead reach the
model as anticipated tool errors with an actionable diagnostic.
"""

from __future__ import annotations

import pytest
from mcp.client import Client
from mcp.types import TextContent

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server


@pytest.mark.asyncio
async def test_missing_document_error_is_actionable() -> None:
    app = create_server(backend=HeadlessBackend(), profile="all")
    async with Client(app) as client:
        res = await client.call_tool("scene_summary", {"doc_id": "doc_1"})

    assert res.is_error is True
    text = "".join(c.text for c in res.content if isinstance(c, TextContent))
    assert "Document 'doc_1' not found" in text
    assert "doc_list()" in text
    assert "doc_new()" in text
