"""
The auto backend must follow Synfig Studio instead of freezing its choice.

The normal workflow is: an MCP client starts the server, the artist opens
Synfig Studio afterwards.  The server therefore has to notice the bridge when
it appears - and switch back when Studio closes.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from synfig_mcp.backend.auto import AutoBackend
from synfig_mcp.backend.base import BackendBase, DocumentInfo, HealthStatus


class _RecordingBackend:
    """Backend double that records the calls it receives."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    async def health_check(self) -> HealthStatus:
        """Return a fake health status."""
        self.calls.append("health_check")
        return HealthStatus(backend=self._name, connected=True)

    async def doc_list(self) -> list[DocumentInfo]:
        """Return a fake document list."""
        self.calls.append("doc_list")
        return [DocumentInfo(id=f"{self._name}-doc", name=self._name)]

    async def doc_new(
        self,
        width: int = 1920,  # noqa: ARG002 - part of the backend contract
        height: int = 1080,  # noqa: ARG002 - part of the backend contract
        fps: float = 24.0,  # noqa: ARG002 - part of the backend contract
    ) -> DocumentInfo:
        """Return a fake document."""
        self.calls.append("doc_new")
        return DocumentInfo(id=f"{self._name}-doc", name=self._name)


def _backend() -> AutoBackend:
    live = cast(BackendBase, _RecordingBackend("live"))
    headless = cast(BackendBase, _RecordingBackend("headless"))
    return AutoBackend(live=live, headless=headless, probe_interval=0.0)


@pytest.mark.asyncio
async def test_auto_backend_uses_the_live_bridge_when_it_is_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _backend()
    monkeypatch.setattr("synfig_mcp.backend.auto.probe_live_bridge", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("synfig_mcp.backend.auto.is_studio_running", lambda: True)

    docs = await backend.doc_list()
    assert docs[0].id == "live-doc"
    assert backend.name == "live"


@pytest.mark.asyncio
async def test_auto_backend_falls_back_to_headless_without_studio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _backend()
    monkeypatch.setattr(
        "synfig_mcp.backend.auto.probe_live_bridge", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr("synfig_mcp.backend.auto.is_studio_running", lambda: False)

    docs = await backend.doc_list()
    assert docs[0].id == "headless-doc"
    assert backend.name == "headless"


@pytest.mark.asyncio
async def test_auto_backend_switches_when_studio_starts_later(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The server must pick the live bridge up when Studio appears after startup."""
    backend = _backend()
    reachable = {"value": False}
    running = {"value": False}
    monkeypatch.setattr(
        "synfig_mcp.backend.auto.probe_live_bridge", lambda *_args, **_kwargs: reachable["value"]
    )
    monkeypatch.setattr("synfig_mcp.backend.auto.is_studio_running", lambda: running["value"])

    # No Studio at all: the headless engine is used.
    assert (await backend.doc_list())[0].id == "headless-doc"

    # The artist opens Studio and enables the bridge.
    running["value"] = True
    reachable["value"] = True
    assert (await backend.doc_list())[0].id == "live-doc"

    # Studio is closed again.
    running["value"] = False
    reachable["value"] = False
    assert (await backend.doc_list())[0].id == "headless-doc"


@pytest.mark.asyncio
async def test_auto_backend_keeps_live_when_the_bridge_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Studio is open but the bridge is off: fail loudly instead of editing invisibly."""
    backend = _backend()
    monkeypatch.setattr(
        "synfig_mcp.backend.auto.probe_live_bridge", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr("synfig_mcp.backend.auto.is_studio_running", lambda: True)

    assert (await backend.doc_list())[0].id == "live-doc"


@pytest.mark.asyncio
async def test_auto_backend_reports_the_active_backend_in_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _backend()
    monkeypatch.setattr("synfig_mcp.backend.auto.probe_live_bridge", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("synfig_mcp.backend.auto.is_studio_running", lambda: True)

    status = await backend.health_check()
    assert status.backend == "live"
    assert status.connected is True


def test_auto_backend_is_used_in_auto_mode() -> None:
    """The auto mode must return the dynamic backend."""
    from synfig_mcp.backend.select import get_backend

    backend: Any = get_backend("auto")
    assert isinstance(backend, AutoBackend)
