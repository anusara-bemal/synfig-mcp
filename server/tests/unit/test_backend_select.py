"""Backend selection must never hide an open Studio behind headless documents."""

from __future__ import annotations

from typing import Any

import pytest

from synfig_mcp.backend import select
from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend


def _patch(monkeypatch: pytest.MonkeyPatch, *, bridge: bool, studio: bool) -> None:
    monkeypatch.setattr(select, "probe_live_bridge", lambda *_, **__: bridge)
    monkeypatch.setattr(select, "is_studio_running", lambda *_, **__: studio)


def test_auto_uses_live_when_bridge_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, bridge=True, studio=True)
    backend = select.get_backend("auto")
    assert isinstance(backend, LiveBackend)


def test_auto_stays_live_when_studio_is_open_but_bridge_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, bridge=False, studio=True)
    backend = select.get_backend("auto")
    assert isinstance(backend, LiveBackend)
    assert backend.studio_detected is True


def test_auto_uses_headless_only_when_no_studio_is_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, bridge=False, studio=False)
    assert isinstance(select.get_backend("auto"), HeadlessBackend)


def test_forced_headless_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, bridge=True, studio=True)
    assert isinstance(select.get_backend("headless"), HeadlessBackend)


def test_forced_live_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, bridge=False, studio=False)
    assert isinstance(select.get_backend("live"), LiveBackend)


def test_bridge_error_explains_patched_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("synfig_mcp.backend.live.is_studio_running", lambda *_, **__: True)
    message = LiveBackend().bridge_unavailable_message()
    assert "MCP bridge" in message
    assert "patched" in message.lower()
    assert "Tools -> MCP Bridge" in message


def test_bridge_error_handles_no_studio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("synfig_mcp.backend.live.is_studio_running", lambda *_, **__: False)
    message = LiveBackend().bridge_unavailable_message()
    assert "no Studio process" in message
    assert "headless" in message.lower()


@pytest.mark.asyncio
async def test_live_health_reports_detected_studio(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = LiveBackend(studio_detected=True)

    async def fail() -> Any:
        raise OSError("connection refused")

    # Avoid a real socket attempt.
    monkeypatch.setattr(backend, "_ensure_client", fail)
    status = await backend.health_check()
    assert status.backend == "live"
    assert status.connected is False
    assert status.studio_running is True
    assert status.details["bridge_reachable"] is False
    assert "warning" in status.details
