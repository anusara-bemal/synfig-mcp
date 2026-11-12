"""
CI Token Budget Gate: Asserts token baseline measurements and response ceilings.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from mcp.client import Client
from mcp.types import TextContent

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
TOKEN_BUDGET_MD = DOCS_DIR / "TOKEN_BUDGET.md"

try:
    import tiktoken

    enc_cl100k = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(enc_cl100k.encode(text))
except Exception:

    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)


def test_token_budget_artifact_exists() -> None:
    """TOKEN_BUDGET.md must exist and contain verified baseline numbers."""
    assert TOKEN_BUDGET_MD.exists(), "docs/TOKEN_BUDGET.md is missing"
    content = TOKEN_BUDGET_MD.read_text(encoding="utf-8")
    assert "cl100k_base" in content
    assert "Contact Sheet Efficiency" in content
    assert "core" in content


@pytest.mark.asyncio
async def test_tools_list_core_profile_budget() -> None:
    """Default 'core' profile must stay strictly below 3,000 tokens."""
    backend = HeadlessBackend()
    app = create_server(backend=backend, profile="core")
    async with Client(app) as client:
        tools_res = await client.list_tools()

    tools_raw = [t.model_dump() for t in tools_res.tools]
    dumped = json.dumps(tools_raw)
    tokens = count_tokens(dumped)

    # Core budget ceiling enforced by CI
    assert tokens <= 3000, f"core profile exceeded 3,000 token budget: {tokens} tokens"
    assert len(tools_res.tools) <= 15, f"core profile tool count bloated: {len(tools_res.tools)}"


@pytest.mark.asyncio
async def test_tools_list_token_ceiling() -> None:
    """Assert tools/list does not silently balloon without profile gating."""
    backend = HeadlessBackend()
    app = create_server(backend=backend, profile="all")
    async with Client(app) as client:
        tools_res = await client.list_tools()

    tools_raw = [t.model_dump() for t in tools_res.tools]
    dumped = json.dumps(tools_raw)
    tokens = count_tokens(dumped)

    # Full studio ceiling.  Raised from 22,000 to 24,000 when the anime
    # production pipeline (produce_anime_project and friends) was added.
    assert tokens <= 24000, f"tools/list token bloat detected: {tokens} > 24000"


@pytest.mark.asyncio
async def test_common_tool_call_response_ceilings() -> None:
    """Typical scalar mutations and inspect calls must stay strictly under 500 tokens."""
    backend = HeadlessBackend()
    app = create_server(backend=backend, profile="all")

    async with Client(app) as client:
        # health_check
        res = await client.call_tool("health_check", {})
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        assert count_tokens(text) < 200

        # doc_new
        res = await client.call_tool("doc_new", {"width": 160, "height": 120, "fps": 24.0})
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        data: dict[str, Any] = json.loads(text)
        doc_id = data.get("id", "doc_0")
        assert count_tokens(text) < 200

        # layer_add
        res = await client.call_tool(
            "layer_add",
            {"doc_id": doc_id, "layer_type": "circle", "description": "BudgetCircle"},
        )
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        assert count_tokens(text) < 250

        # anim_time_set
        res = await client.call_tool("anim_time_set", {"doc_id": doc_id, "time": 0.5})
        first = res.content[0] if res.content else None
        text = first.text if isinstance(first, TextContent) else ""
        assert count_tokens(text) < 100
