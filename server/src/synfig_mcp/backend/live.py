"""
[STUB - P1 Prototype] LiveBackend: communicates with patched Synfig Studio over local TCP socket.

NOTE: This is a P1 prototype in-memory stub. The live protocol client connecting to
mcp_bridge via JSON-RPC 2.0 will be fully wired in Phase P3.
"""

from typing import Any

from synfig_mcp.backend.base import BackendBase, DocumentInfo, HealthStatus
from synfig_mcp.config import settings


class LiveBackend(BackendBase):
    """[STUB - P1 Prototype] Primary backend connecting to running Synfig Studio via native C++ bridge."""

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or settings.bridge_host
        self.port = port or settings.bridge_port
        self._connected = False

    @property
    def name(self) -> str:
        return "live"

    async def health_check(self) -> HealthStatus:
        """Probe the live bridge socket."""
        return HealthStatus(
            backend="live",
            connected=self._connected,
            studio_running=self._connected,
            details={"host": self.host, "port": self.port, "status": "p1_prototype_stub"},
        )

    async def doc_list(self) -> list[DocumentInfo]:
        return []

    async def doc_new(
        self, width: int = 1920, height: int = 1080, fps: float = 24.0
    ) -> DocumentInfo:
        return DocumentInfo(
            id="doc_0",
            name="Synfig Animation 1",
            width=width,
            height=height,
            fps=fps,
            duration_frames=120,
        )

    async def doc_open(self, file_path: str) -> DocumentInfo:
        return DocumentInfo(
            id="doc_opened",
            name=file_path,
            file_path=file_path,
            width=1920,
            height=1080,
            fps=24.0,
            duration_frames=120,
        )

    async def doc_save(self, doc_id: str, file_path: str | None = None) -> str:
        return file_path or f"{doc_id}.sifz"

    async def scene_tree(self, doc_id: str) -> dict[str, Any]:
        return {"doc_id": doc_id, "layers": []}

    async def layer_add(
        self,
        doc_id: str,
        layer_type: str,
        canvas_path: str = "",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "doc_id": doc_id,
            "layer_type": layer_type,
            "canvas_path": canvas_path,
            "params": params or {},
        }

    async def undo(self, _doc_id: str) -> bool:
        return True

    async def redo(self, _doc_id: str) -> bool:
        return True
