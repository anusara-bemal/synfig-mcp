"""
Abstract Base Class defining the contract for synfig-mcp backends.
Both LiveBackend (Studio) and HeadlessBackend (pure-Python + CLI) implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health status and capabilities of the active backend."""

    backend: str
    connected: bool
    version: str | None = None
    studio_running: bool = False
    details: dict[str, Any] = {}


class DocumentInfo(BaseModel):
    """Metadata describing an open or loaded Synfig document."""

    id: str
    name: str
    file_path: str | None = None
    width: int
    height: int
    fps: float
    duration_frames: int


class BackendBase(ABC):
    """Unified interface for Synfig operations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the backend ('live' or 'headless')."""
        ...

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check backend readiness, connection, and capabilities."""
        ...

    @abstractmethod
    async def doc_list(self) -> list[DocumentInfo]:
        """List currently open/loaded documents."""
        ...

    @abstractmethod
    async def doc_new(
        self, width: int = 1920, height: int = 1080, fps: float = 24.0
    ) -> DocumentInfo:
        """Create a new document."""
        ...

    @abstractmethod
    async def doc_open(self, file_path: str) -> DocumentInfo:
        """Open a .sif/.sifz/.sfg document."""
        ...

    @abstractmethod
    async def doc_save(self, doc_id: str, file_path: str | None = None) -> str:
        """Save document to disk."""
        ...

    @abstractmethod
    async def scene_tree(self, doc_id: str) -> dict[str, Any]:
        """Get hierarchical layer tree for the document."""
        ...

    @abstractmethod
    async def layer_add(
        self,
        doc_id: str,
        layer_type: str,
        canvas_path: str = "",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a new layer to the specified canvas/group."""
        ...

    @abstractmethod
    async def undo(self, doc_id: str) -> bool:
        """Undo the last action."""
        ...

    @abstractmethod
    async def redo(self, doc_id: str) -> bool:
        """Redo the previously undone action."""
        ...
