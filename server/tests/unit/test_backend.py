"""Unit tests for backends."""

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.backend.select import get_backend


@pytest.mark.asyncio
async def test_headless_backend_crud(headless_backend: HeadlessBackend) -> None:
    health = await headless_backend.health_check()
    assert health.backend == "headless"
    assert health.connected is True

    doc = await headless_backend.doc_new(1920, 1080, 24.0)
    assert doc.width == 1920
    assert doc.height == 1080

    docs = await headless_backend.doc_list()
    assert len(docs) == 1
    assert docs[0].id == doc.id

    layer = await headless_backend.layer_add(doc.id, "circle")
    assert layer["layer_type"] == "circle"

    assert await headless_backend.undo(doc.id) is True
    assert await headless_backend.redo(doc.id) is True


@pytest.mark.asyncio
async def test_live_backend_interface(live_backend: LiveBackend) -> None:
    health = await live_backend.health_check()
    assert health.backend == "live"


def test_backend_select_modes() -> None:
    headless = get_backend("headless")
    assert headless.name == "headless"

    live = get_backend("live")
    assert live.name == "live"
