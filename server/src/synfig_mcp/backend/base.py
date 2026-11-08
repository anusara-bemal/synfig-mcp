"""
Abstract Base Class defining the contract for synfig-mcp backends.
Both LiveBackend (Studio) and HeadlessBackend (pure-Python + CLI) implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from synfig_mcp.protocol.models import SynfigValue


class HealthStatus(BaseModel):
    """Health status and capabilities of the active backend."""

    backend: str
    connected: bool
    version: str | None = None
    studio_running: bool = False
    details: dict[str, Any] = {}


class DocumentInfo(BaseModel):
    """Metadata describing an open or loaded Synfig document."""

    id: str = Field(validation_alias=AliasChoices("id", "doc_id"))
    name: str = ""
    file_path: str | None = None
    width: int = 1920
    height: int = 1080
    fps: float = 24.0
    start_time: float = 0.0
    end_time: float = 5.0
    duration_frames: int = 120

    model_config = ConfigDict(populate_by_name=True)


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

    # -----------------------------------------------------------------------
    # Document Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def doc_list(self) -> list[DocumentInfo]:
        """List currently open/loaded documents."""
        ...

    async def doc_info(self, doc_id: str) -> DocumentInfo | None:
        """Get info for a specific open document."""
        docs = await self.doc_list()
        for d in docs:
            if d.id == doc_id:
                return d
        return None

    async def get_doc_state(self, doc_id: str) -> str:
        """Return a string or hash representing the current document revision/state."""
        return doc_id

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
    async def doc_close(self, doc_id: str, force: bool = False) -> bool:
        """Close an open document."""
        ...

    @abstractmethod
    async def doc_set_properties(
        self,
        doc_id: str,
        name: str | None = None,
        desc: str | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> DocumentInfo:
        """Update canvas properties."""
        ...

    @abstractmethod
    async def doc_set_time_range(
        self,
        doc_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
    ) -> DocumentInfo:
        """Update canvas animation timeline range (start_time, end_time, fps)."""
        ...

    # -----------------------------------------------------------------------
    # Canvas Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def canvas_list(self, doc_id: str) -> list[str]:
        """List canvas hierarchy paths."""
        ...

    @abstractmethod
    async def scene_tree(self, doc_id: str, canvas_path: str = "") -> dict[str, Any]:
        """Get hierarchical layer tree for the document."""
        ...

    # -----------------------------------------------------------------------
    # Layer Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def layer_add(
        self,
        doc_id: str,
        layer_type: str,
        canvas_path: str = "",
        params: dict[str, Any] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Add a new layer to the specified canvas/group."""
        ...

    @abstractmethod
    async def layer_remove(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        """Remove a layer."""
        ...

    @abstractmethod
    async def layer_duplicate(
        self, doc_id: str, layer_id: str, canvas_path: str = ""
    ) -> dict[str, Any]:
        """Duplicate an existing layer."""
        ...

    @abstractmethod
    async def layer_reorder(
        self, doc_id: str, layer_id: str, new_depth: int, canvas_path: str = ""
    ) -> bool:
        """Move layer to a new depth."""
        ...

    @abstractmethod
    async def layer_raise(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        """Raise layer by 1 position."""
        ...

    @abstractmethod
    async def layer_lower(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        """Lower layer by 1 position."""
        ...

    @abstractmethod
    async def layer_group(
        self,
        doc_id: str,
        layer_ids: list[str],
        group_name: str = "Group",
        canvas_path: str = "",
    ) -> dict[str, Any]:
        """Group layers into a PasteCanvas layer."""
        ...

    @abstractmethod
    async def layer_ungroup(self, doc_id: str, layer_id: str, canvas_path: str = "") -> list[str]:
        """Ungroup a PasteCanvas layer."""
        ...

    @abstractmethod
    async def import_asset(
        self, doc_id: str, file_path: str, canvas_path: str = ""
    ) -> dict[str, Any]:
        """Import an external image or media asset into the canvas."""
        ...

    # -----------------------------------------------------------------------
    # Parameter Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def param_get(
        self, doc_id: str, layer_id: str, param_name: str, canvas_path: str = ""
    ) -> SynfigValue | None:
        """Get a layer parameter value."""
        ...

    @abstractmethod
    async def param_set(
        self,
        doc_id: str,
        layer_id: str,
        param_name: str,
        value: SynfigValue | Any,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        """Set a layer parameter value."""
        ...

    @abstractmethod
    async def param_convert(
        self, doc_id: str, layer_id: str, param_name: str, type: str
    ) -> dict[str, Any]:
        """Convert a parameter to a linkable ValueNode type (e.g. scale, add, sine, linear, timeloop, composite)."""
        ...

    @abstractmethod
    async def param_export(
        self, doc_id: str, layer_id: str, param_name: str, name: str
    ) -> dict[str, Any]:
        """Export a parameter ValueNode to the canvas value node library."""
        ...

    @abstractmethod
    async def param_unexport(self, doc_id: str, name: str) -> dict[str, Any]:
        """Unexport a previously exported ValueNode."""
        ...

    # -----------------------------------------------------------------------
    # Animation & Keyframe Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def anim_time_get(self, doc_id: str) -> float:
        """Get current timeline cursor position in seconds."""
        ...

    @abstractmethod
    async def anim_time_set(self, doc_id: str, time: float | str) -> float:
        """Seek timeline cursor to a position."""
        ...

    @abstractmethod
    async def anim_keyframe_add(
        self,
        doc_id: str,
        time: float | str,
        description: str = "",
        active: bool = True,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        """Add a keyframe."""
        ...

    @abstractmethod
    async def anim_keyframe_remove(
        self, doc_id: str, time: float | str, canvas_path: str = ""
    ) -> bool:
        """Remove a keyframe."""
        ...

    @abstractmethod
    async def anim_keyframe_list(self, doc_id: str, canvas_path: str = "") -> list[dict[str, Any]]:
        """List keyframes."""
        ...

    @abstractmethod
    async def anim_waypoint_set(
        self,
        doc_id: str,
        layer_id: str,
        param_name: str,
        time: float,
        value: SynfigValue | Any,
        interpolation: str | None = None,
        interpolation_in: str | None = None,
        interpolation_out: str | None = None,
    ) -> dict[str, Any]:
        """Insert or update a waypoint at a specific time with optional interpolation."""
        ...

    @abstractmethod
    async def anim_waypoint_remove(
        self, doc_id: str, layer_id: str, param_name: str, time: float
    ) -> dict[str, Any]:
        """Remove a waypoint at a specific time."""
        ...

    @abstractmethod
    async def anim_animate_param(
        self,
        doc_id: str,
        layer_id: str,
        param_name: str,
        waypoints: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply a bulk list of waypoints as a single undo step."""
        ...

    @abstractmethod
    async def anim_interpolation_set(
        self,
        doc_id: str,
        interpolation: str,
        layer_id: str | None = None,
        param_name: str | None = None,
    ) -> dict[str, Any]:
        """Set default interpolation or update interpolation for all waypoints of a parameter."""
        ...

    # -----------------------------------------------------------------------
    # History (Undo / Redo) Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def undo(self, doc_id: str) -> bool:
        """Undo the last action."""
        ...

    @abstractmethod
    async def redo(self, doc_id: str) -> bool:
        """Redo the previously undone action."""
        ...

    @abstractmethod
    async def history_list(self, doc_id: str) -> dict[str, Any]:
        """List undo and redo stacks."""
        ...

    # -----------------------------------------------------------------------
    # Rendering Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    async def render_frame(
        self,
        doc_id: str,
        output_path: str,
        time: float | str = 0.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
    ) -> bool:
        """Render a single frame of the document to an image."""
        ...

    @abstractmethod
    async def render_sequence(
        self,
        doc_id: str,
        output_dir: str,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
        progress_cb: Any = None,
        cancel_token: Any = None,
    ) -> list[str]:
        """Render an image sequence for the document timeline to an output directory."""
        ...

    @abstractmethod
    async def render_video(
        self,
        doc_id: str,
        output_path: str,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> bool:
        """Render the animation to a video file (.mp4, .avi, or .gif)."""
        ...

    @abstractmethod
    async def render_contact_sheet(
        self,
        doc_id: str,
        output_path: str,
        cols: int = 4,
        rows: int = 3,
        width: int | None = None,
        height: int | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> bool:
        """Render a grid contact sheet of timeline key moments/frames into a single image."""
        ...
