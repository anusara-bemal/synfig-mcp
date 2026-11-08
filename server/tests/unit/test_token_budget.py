"""
CI Token Budget Gate: Asserts token baseline measurements and response ceilings.
"""

import json
from pathlib import Path
from typing import Any

import pytest
import tiktoken
from mcp.client import Client
from mcp.types import TextContent

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
TOKEN_BUDGET_MD = DOCS_DIR / "TOKEN_BUDGET.md"

enc_cl100k = tiktoken.get_encoding("cl100k_base")


def test_token_budget_artifact_exists() -> None:
    """TOKEN_BUDGET.md must exist and contain verified baseline numbers."""
    assert TOKEN_BUDGET_MD.exists(), "docs/TOKEN_BUDGET.md is missing"
    content = TOKEN_BUDGET_MD.read_text(encoding="utf-8")
    assert "15,498 tokens" in content
    assert "cl100k_base" in content
    assert "Contact Sheet Efficiency" in content


@pytest.mark.asyncio
async def test_tools_list_token_ceiling() -> None:
    """Assert tools/list does not silently balloon without profile gating."""
    backend = HeadlessBackend()
    app = create_server(backend=backend)
    async with Client(app) as client:
        tools_res = await client.list_tools()

    tools_raw = [t.model_dump() for t in tools_res.tools]
    dumped = json.dumps(tools_raw)
    tokens = len(enc_cl100k.encode(dumped))

    # Current baseline: 15,498 tokens for 52 tools.
    # Ceiling allows reasonable variation but fails if bloated beyond 18k without profiles.
    assert tokens <= 18000, f"tools/list token bloat detected: {tokens} > 18000"


@pytest.mark.asyncio
async def test_common_tool_call_response_ceilings() -> None:
    """Typical scalar mutations and inspect calls must stay strictly under 500 tokens."""
    backend = HeadlessBackend()
    app = create_server(backend=backend)

    async with Client(app) as client:
        # health_check
        res = await client.call_tool("health_check", {})
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        assert len(enc_cl100k.encode(text)) < 200

        # doc_new
        res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        data: dict[str, Any] = json.loads(text)
        doc_id = data.get("id", "doc_0")
        assert len(enc_cl100k.encode(text)) < 200

        # layer_add
        res = await client.call_tool(
            "layer_add",
            {"doc_id": doc_id, "layer_type": "circle", "description": "BudgetCircle"},
        )
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        assert len(enc_cl100k.encode(text)) < 250

        # anim_time_set
        res = await client.call_tool("anim_time_set", {"doc_id": doc_id, "time": 0.5})
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        assert len(enc_cl100k.encode(text)) < 100
