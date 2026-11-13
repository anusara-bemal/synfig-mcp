"""
Phase 6: live Studio view control, layer appearance, and event-driven sync.

These tests exercise the real code paths: the headless engine for the
document-backed operations, and the live backend against the in-process
protocol fake for the GUI-only operations (view/zoom/pan and event polling).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.errors import SynfigError
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer


@pytest_asyncio.fixture
async def live_backend() -> AsyncIterator[LiveBackend]:
    bridge = FakeBridgeServer(port=0)
    await bridge.start()
    client = BridgeClient(host=bridge.host, port=bridge.assigned_port, token=bridge.token)
    await client.connect()
    backend = LiveBackend(client=client)
    try:
        yield backend
    finally:
        await client.close()
        await bridge.stop()


# ---------------------------------------------------------------------------
# Headless: honest document-backed behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_headless_view_reports_no_gui() -> None:
    backend = HeadlessBackend()
    doc = await backend.doc_new(320, 240, 24.0)
    state = await backend.view_get(doc.id)
    assert state["gui"] is False
    assert state["zoom"] == 1.0


@pytest.mark.asyncio
async def test_headless_view_set_requires_gui() -> None:
    backend = HeadlessBackend()
    doc = await backend.doc_new(320, 240, 24.0)
    with pytest.raises(SynfigError):
        await backend.view_set(doc.id, zoom=2.0)


@pytest.mark.asyncio
async def test_headless_layer_visibility_toggles_active() -> None:
    backend = HeadlessBackend()
    doc = await backend.doc_new(320, 240, 24.0)
    await backend.layer_add(doc.id, "circle", description="C1")

    res = await backend.layer_set_visibility(doc.id, "C1", False)
    assert res["visible"] is False

    res = await backend.layer_set_visibility(doc.id, "C1", True)
    assert res["visible"] is True


@pytest.mark.asyncio
async def test_headless_blend_rejects_non_composite_layer() -> None:
    backend = HeadlessBackend()
    doc = await backend.doc_new(320, 240, 24.0)
    await backend.layer_add(doc.id, "circle", description="C1")
    with pytest.raises(SynfigError, match="amount"):
        await backend.layer_set_blend(doc.id, "C1", amount=0.5)


@pytest.mark.asyncio
async def test_headless_recent_events_is_empty() -> None:
    backend = HeadlessBackend()
    doc = await backend.doc_new(320, 240, 24.0)
    res = await backend.recent_events(doc.id)
    assert res["events"] == []
    assert res["state_version"] == "headless"


# ---------------------------------------------------------------------------
# Live backend against the protocol fake
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_view_zoom_reports_gui(live_backend: LiveBackend) -> None:
    state = await live_backend.view_set("doc_0", mode="in")
    assert state["gui"] is True
    assert state["zoom"] == 2.0


@pytest.mark.asyncio
async def test_live_view_pan_uses_pan_method(live_backend: LiveBackend) -> None:
    state = await live_backend.view_set("doc_0", x=12.0, y=-4.0)
    assert state["focus"] == {"x": 12.0, "y": -4.0}


@pytest.mark.asyncio
async def test_live_layer_visibility_roundtrips(live_backend: LiveBackend) -> None:
    res = await live_backend.layer_set_visibility("doc_0", "Circle001", False)
    assert res["visible"] is False
    assert res["layer_id"] == "Circle001"


@pytest.mark.asyncio
async def test_live_layer_blend_roundtrips(live_backend: LiveBackend) -> None:
    res = await live_backend.layer_set_blend("doc_0", "Group001", amount=0.25, blend_method=3)
    assert res["amount"] == 0.25
    assert res["blend_method"] == 3


@pytest.mark.asyncio
async def test_live_layer_align_returns_moved_list(live_backend: LiveBackend) -> None:
    res = await live_backend.layer_align("doc_0", ["Circle001"], edge="left")
    assert res["edge"] == "left"
    assert isinstance(res["moved"], list)


@pytest.mark.asyncio
async def test_live_recent_events_tracks_state_version() -> None:
    bridge = FakeBridgeServer(port=0)
    await bridge.start()
    client = BridgeClient(host=bridge.host, port=bridge.assigned_port, token=bridge.token)
    await client.connect()
    backend = LiveBackend(client=client)
    try:
        before = await backend.recent_events("doc_0")
        assert before["state_version"] == 0

        await bridge.broadcast_event(
            "event.document_changed", {"doc_id": "doc_0", "action": "LayerAdd"}
        )

        after = before
        for _ in range(50):
            after = await backend.recent_events("doc_0")
            if after["state_version"] >= 1:
                break
            await asyncio.sleep(0.02)

        assert after["state_version"] >= 1
        assert any(e["method"] == "event.document_changed" for e in after["events"])
    finally:
        await client.close()
        await bridge.stop()
