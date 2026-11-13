"""
Unit tests for the capability registry and its compact meta-tools.

These exercise the real registration + MCP client path (no mocks) to confirm the
registry is honest: it advertises exactly what the server can serve, execution
round-trips, and profile load/unload changes the live surface.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp.client import Client
from mcp.types import TextContent

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.capabilities import CapabilityRegistry, build_capabilities
from synfig_mcp.server import create_server


def _data(result: Any) -> Any:
    assert not result.is_error, result
    for item in result.content:
        if isinstance(item, TextContent):
            try:
                return json.loads(item.text)
            except ValueError:
                return item.text
    return None


@pytest.fixture
def core_server() -> Any:
    return create_server(backend=HeadlessBackend(), profile="all")


@pytest.mark.asyncio
async def test_discover_reports_real_surface(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(await client.call_tool("capability_discover", {}))
    assert data["backend"] == "headless"
    assert data["tool_count"] > 0
    assert any(w["id"] == "new_document" for w in data["workflows"])


@pytest.mark.asyncio
async def test_search_finds_capability_by_keyword(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(await client.call_tool("capability_search", {"query": "render"}))
    ids = {c["id"] for c in data["capabilities"]}
    assert ids & {"render_frame", "render_sequence", "render_video"}


@pytest.mark.asyncio
async def test_inspect_returns_full_descriptor(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(await client.call_tool("capability_inspect", {"capability_id": "doc_new"}))
    assert data["id"] == "doc_new"
    assert "width" in data["input_schema"]["properties"]
    assert data["permission"] in ("read", "write", "destructive")


@pytest.mark.asyncio
async def test_inspect_unknown_capability(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(await client.call_tool("capability_inspect", {"capability_id": "nope"}))
    assert "error" in data


@pytest.mark.asyncio
async def test_validate_detects_missing_and_unexpected(core_server: Any) -> None:
    async with Client(core_server) as client:
        good = _data(
            await client.call_tool(
                "capability_validate", {"capability_id": "doc_new", "args": {"width": 100}}
            )
        )
        bad = _data(
            await client.call_tool(
                "capability_validate",
                {"capability_id": "doc_new", "args": {"bogus": 1}},
            )
        )
    assert good["valid"] is True
    assert bad["valid"] is False and bad["unexpected"] == ["bogus"]


@pytest.mark.asyncio
async def test_execute_round_trips_real_tool(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(
            await client.call_tool(
                "capability_execute",
                {"capability_id": "doc_new", "args": {"width": 200, "height": 100}},
            )
        )
    assert data["capability"] == "doc_new"
    assert data["result"]["width"] == 200


@pytest.mark.asyncio
async def test_execute_rejects_unknown(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(
            await client.call_tool("capability_execute", {"capability_id": "does_not_exist"})
        )
    assert "error" in data


@pytest.mark.asyncio
async def test_batch_execute_runs_in_sequence(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(
            await client.call_tool(
                "capability_batch_execute",
                {
                    "operations": [
                        {"capability": "doc_new", "args": {"width": 111, "height": 111}},
                        {"capability": "doc_list", "args": {}},
                    ]
                },
            )
        )
    assert data["completed"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_batch_execute_stops_on_error(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(
            await client.call_tool(
                "capability_batch_execute",
                {
                    "operations": [
                        {"capability": "not_a_tool", "args": {}},
                        {"capability": "doc_list", "args": {}},
                    ]
                },
            )
        )
    assert data["completed"] == 0
    assert len(data["results"]) == 1


@pytest.mark.asyncio
async def test_workflow_execute_and_resume(core_server: Any) -> None:
    async with Client(core_server) as client:
        data = _data(
            await client.call_tool(
                "capability_workflow_execute",
                {"workflow_id": "new_document", "run_id": "unit_test_run"},
            )
        )
    assert data["status"] == "completed"
    assert data["context"]["doc"]["width"] == 1920


@pytest.mark.asyncio
async def test_workflow_resume_unknown_run(core_server: Any) -> None:
    async with Client(core_server) as client:
        result = await client.call_tool("capability_workflow_resume", {"run_id": "no_such_run_xyz"})
    assert result.is_error


def test_registry_is_honest_about_availability() -> None:
    """Every advertised 'tool' capability must be a tool the server registers."""
    from mcp.server.mcpserver import MCPServer

    from synfig_mcp.tools import register_all_tools

    server = MCPServer("probe")
    backend = HeadlessBackend()
    register_all_tools(server, backend, profile="all")
    caps = build_capabilities(server)
    registered = {t.name for t in server._tool_manager.list_tools()}
    tool_caps = {c.id for c in caps if c.kind == "tool"}
    assert tool_caps == registered
    registry = CapabilityRegistry(caps)
    assert registry.get("doc_new") is not None
