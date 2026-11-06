"""
[STUB - P1 Prototype] HeadlessBackend: pure-Python .sif/.sifz/.sfg document engine + synfig CLI.

NOTE: This is a P1 prototype in-memory stub. The complete headless document engine
with full XML AST transformations and synfig CLI execution will be developed in Phase P6.
"""

from typing import Any

from synfig_mcp.backend.base import BackendBase, DocumentInfo, HealthStatus


class HeadlessBackend(BackendBase):
    """[STUB - P1 Prototype] Secondary backend operating on files via lxml and invoking synfig CLI."""

    def __init__(self) -> None:
        self._documents: dict[str, DocumentInfo] = {}

    @property
    def name(self) -> str:
        return "headless"

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            backend="headless",
            connected=True,
            studio_running=False,
            details={"engine": "lxml_sif_stub"},
        )

    async def doc_list(self) -> list[DocumentInfo]:
        return list(self._documents.values())

    async def doc_new(
        self, width: int = 1920, height: int = 1080, fps: float = 24.0
    ) -> DocumentInfo:
        doc_id = f"doc_{len(self._documents) + 1}"
        doc = DocumentInfo(
            id=doc_id,
            name=f"Untitled {len(self._documents) + 1}",
            width=width,
            height=height,
            fps=fps,
            duration_frames=120,
        )
        self._documents[doc_id] = doc
        return doc

    async def doc_open(self, file_path: str) -> DocumentInfo:
        doc_id = f"doc_{len(self._documents) + 1}"
        doc = DocumentInfo(
            id=doc_id,
            name=file_path,
            file_path=file_path,
            width=1920,
            height=1080,
            fps=24.0,
            duration_frames=120,
        )
        self._documents[doc_id] = doc
        return doc

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
