"""
Contract tests for MCP prompts and concrete resources.

LobeHub (and any MCP scanner) requires the server to advertise at least one
working prompt and at least one readable resource, not just tools. These tests
lock in that behaviour so it cannot silently regress.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from mcp.client import Client

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server


@asynccontextmanager
async def _client() -> AsyncIterator[Client]:
    app = create_server(backend=HeadlessBackend(), profile="all")
    async with Client(app) as session:
        yield session


# ---------------------------------------------------------------------------
# Capability advertisement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_advertises_prompts_and_resources() -> None:
    async with _client() as client:
        caps = client.server_capabilities
        assert caps.tools is not None
        assert caps.prompts is not None
        assert caps.resources is not None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lists_expected_prompts() -> None:
    async with _client() as client:
        result = await client.list_prompts()
        names = {p.name for p in result.prompts}
    assert {
        "create_animation_scene",
        "rig_and_animate_character",
        "render_and_review",
        "produce_anime_project",
        "troubleshoot_connection",
    } <= names


@pytest.mark.asyncio
async def test_prompt_exposes_arguments() -> None:
    async with _client() as client:
        result = await client.list_prompts()
        by_name = {p.name: p for p in result.prompts}
    args = {a.name for a in (by_name["create_animation_scene"].arguments or [])}
    assert args == {"title", "style"}
    assert not (by_name["troubleshoot_connection"].arguments or [])


@pytest.mark.asyncio
async def test_get_prompt_returns_messages() -> None:
    async with _client() as client:
        result = await client.get_prompt(
            "create_animation_scene", {"title": "Sunset", "style": "vector"}
        )
    assert result.messages
    text = result.messages[0].content.text  # type: ignore[union-attr]
    assert "Sunset" in text
    assert "vector" in text
    # The workflow must reference real tools, not invented ones.
    assert "scene_build" in text
    assert "render_frame" in text


@pytest.mark.asyncio
async def test_get_prompt_without_arguments() -> None:
    async with _client() as client:
        result = await client.get_prompt("troubleshoot_connection")
    assert result.messages
    assert "health_check" in result.messages[0].content.text  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lists_concrete_resources() -> None:
    async with _client() as client:
        result = await client.list_resources()
    uris = {str(r.uri) for r in result.resources}
    # One concrete resource per guide topic, template and rubric.
    assert "synfig://index" in uris
    assert "synfig://guide/overview" in uris
    assert "synfig://guide/characters" in uris
    assert "synfig://templates/bouncing_ball" in uris
    assert "synfig://rubrics/general" in uris
    assert len(result.resources) >= 10


@pytest.mark.asyncio
async def test_lists_resource_templates() -> None:
    async with _client() as client:
        result = await client.list_resource_templates()
    templates = {t.uri_template for t in result.resource_templates}
    assert {
        "synfig://guide/{topic}",
        "synfig://templates/{template}",
        "synfig://rubrics/{style}",
    } <= templates


@pytest.mark.asyncio
async def test_read_index_resource() -> None:
    async with _client() as client:
        result = await client.read_resource("synfig://index")
    text = result.contents[0].text  # type: ignore[union-attr]
    assert "synfig://guide/overview" in text
    assert "synfig://templates/bouncing_ball" in text


@pytest.mark.asyncio
async def test_read_guide_resource() -> None:
    async with _client() as client:
        result = await client.read_resource("synfig://guide/characters")
    text = result.contents[0].text  # type: ignore[union-attr]
    assert "character" in text.lower()
    assert len(text) > 100


@pytest.mark.asyncio
async def test_read_unknown_guide_falls_back() -> None:
    async with _client() as client:
        result = await client.read_resource("synfig://guide/does_not_exist")
    assert "not found" in result.contents[0].text.lower()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_template_resource_is_valid_scene_build_spec() -> None:
    async with _client() as client:
        result = await client.read_resource("synfig://templates/bouncing_ball")
    spec = json.loads(result.contents[0].text)  # type: ignore[union-attr]
    assert spec["doc_id"] == "doc_0"
    assert any(layer["id"] == "ball" for layer in spec["layers"])
    assert spec["waypoints"]


@pytest.mark.asyncio
async def test_all_templates_are_valid_json() -> None:
    async with _client() as client:
        for key in ("bouncing_ball", "logo_sting", "lower_third"):
            result = await client.read_resource(f"synfig://templates/{key}")
            spec = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert "layers" in spec


@pytest.mark.asyncio
async def test_unknown_template_reports_error() -> None:
    async with _client() as client:
        result = await client.read_resource("synfig://templates/nope")
    payload = json.loads(result.contents[0].text)  # type: ignore[union-attr]
    assert "error" in payload


@pytest.mark.asyncio
async def test_read_rubric_resource() -> None:
    async with _client() as client:
        result = await client.read_resource("synfig://rubrics/cinematic")
    assert result.contents[0].text.strip()  # type: ignore[union-attr]
