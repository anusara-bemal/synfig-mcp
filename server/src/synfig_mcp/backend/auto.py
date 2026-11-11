"""
Backend that follows Synfig Studio.

The backend of an MCP server used to be chosen once, when the process started.
That is wrong for the normal workflow: an artist starts the MCP client first
and opens Synfig Studio afterwards, and the server then keeps working on an
invisible headless document.

``AutoBackend`` re-evaluates the choice on every call (rate limited), so the
server switches to the live bridge as soon as Studio appears and back to the
headless engine when it closes - without a restart.
"""

from __future__ import annotations

import time
from typing import Any

from synfig_mcp.backend.base import BackendBase, DocumentInfo, HealthStatus
from synfig_mcp.backend.detect import is_studio_running
from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.backend.select import probe_live_bridge
from synfig_mcp.config import settings
from synfig_mcp.logging import get_logger
from synfig_mcp.protocol.models import SynfigValue

logger = get_logger("synfig_mcp.backend.auto")


class AutoBackend(BackendBase):
    """Uses the live bridge when it is reachable, the headless engine otherwise."""

    def __init__(
        self,
        live: BackendBase | None = None,
        headless: BackendBase | None = None,
        probe_interval: float = 2.0,
    ) -> None:
        self._live: BackendBase = live if live is not None else LiveBackend()
        self._headless: BackendBase = headless if headless is not None else HeadlessBackend()
        self._active: BackendBase = self._headless
        self._last_probe: float = 0.0
        self._probe_interval = probe_interval

    # -- selection ---------------------------------------------------------

    def _current(self) -> BackendBase:
        """Return the backend to use, re-probing the bridge when needed."""
        now = time.monotonic()
        if now - self._last_probe >= self._probe_interval:
            self._last_probe = now
            reachable = probe_live_bridge(
                settings.bridge_host,
                settings.bridge_port,
                settings.bridge_connect_timeout_seconds,
            )
            if reachable:
                if self._active is not self._live:
                    logger.info(
                        "Live bridge detected, switching to LiveBackend",
                        host=settings.bridge_host,
                        port=settings.bridge_port,
                    )
                self._active = self._live
            elif is_studio_running():
                # Studio is open but the bridge is off: keep the live backend so
                # the operation fails loudly instead of editing an invisible
                # headless document.
                if self._active is not self._live:
                    logger.warning(
                        "Synfig Studio is running but the MCP bridge is unreachable; "
                        "using LiveBackend so operations fail loudly"
                    )
                self._active = self._live
            else:
                if self._active is not self._headless:
                    logger.info("Synfig Studio is gone, switching to HeadlessBackend")
                self._active = self._headless
        return self._active

    @property
    def name(self) -> str:
        """The name of the backend that is currently used."""
        return self._current().name

    @property
    def active_backend(self) -> BackendBase:
        """The backend that is currently used (for diagnostics)."""
        return self._current()

    # -- delegation --------------------------------------------------------

    async def health_check(
        self,
    ) -> HealthStatus:
        """Delegate to the active backend."""
        return await self._current().health_check()

    async def doc_list(
        self,
    ) -> list[DocumentInfo]:
        """Delegate to the active backend."""
        return await self._current().doc_list()

    async def doc_new(
        self, width: int = 1920, height: int = 1080, fps: float = 24.0
    ) -> DocumentInfo:
        """Delegate to the active backend."""
        return await self._current().doc_new(width=width, height=height, fps=fps)

    async def doc_open(self, file_path: str) -> DocumentInfo:
        """Delegate to the active backend."""
        return await self._current().doc_open(file_path=file_path)

    async def doc_save(self, doc_id: str, file_path: str | None = None) -> str:
        """Delegate to the active backend."""
        return await self._current().doc_save(doc_id=doc_id, file_path=file_path)

    async def doc_close(self, doc_id: str, force: bool = False) -> bool:
        """Delegate to the active backend."""
        return await self._current().doc_close(doc_id=doc_id, force=force)

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
        """Delegate to the active backend."""
        return await self._current().doc_set_properties(
            doc_id=doc_id,
            name=name,
            desc=desc,
            width=width,
            height=height,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
        )

    async def doc_set_time_range(
        self,
        doc_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
    ) -> DocumentInfo:
        """Delegate to the active backend."""
        return await self._current().doc_set_time_range(
            doc_id=doc_id, start_time=start_time, end_time=end_time, fps=fps
        )

    async def canvas_list(self, doc_id: str) -> list[str]:
        """Delegate to the active backend."""
        return await self._current().canvas_list(doc_id=doc_id)

    async def scene_tree(self, doc_id: str, canvas_path: str = "") -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().scene_tree(doc_id=doc_id, canvas_path=canvas_path)

    async def schema_list_layers(self) -> list[dict[str, Any]]:
        """Delegate to the active backend (live factory probe when Studio is up)."""
        return await self._current().schema_list_layers()

    async def layer_add(
        self,
        doc_id: str,
        layer_type: str,
        canvas_path: str = "",
        params: dict[str, Any] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().layer_add(
            doc_id=doc_id,
            layer_type=layer_type,
            canvas_path=canvas_path,
            params=params,
            description=description,
        )

    async def layer_remove(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        """Delegate to the active backend."""
        return await self._current().layer_remove(
            doc_id=doc_id, layer_id=layer_id, canvas_path=canvas_path
        )

    async def layer_duplicate(
        self, doc_id: str, layer_id: str, canvas_path: str = ""
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().layer_duplicate(
            doc_id=doc_id, layer_id=layer_id, canvas_path=canvas_path
        )

    async def layer_reorder(
        self, doc_id: str, layer_id: str, new_depth: int, canvas_path: str = ""
    ) -> bool:
        """Delegate to the active backend."""
        return await self._current().layer_reorder(
            doc_id=doc_id, layer_id=layer_id, new_depth=new_depth, canvas_path=canvas_path
        )

    async def layer_raise(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        """Delegate to the active backend."""
        return await self._current().layer_raise(
            doc_id=doc_id, layer_id=layer_id, canvas_path=canvas_path
        )

    async def layer_lower(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        """Delegate to the active backend."""
        return await self._current().layer_lower(
            doc_id=doc_id, layer_id=layer_id, canvas_path=canvas_path
        )

    async def layer_group(
        self, doc_id: str, layer_ids: list[str], group_name: str = "Group", canvas_path: str = ""
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().layer_group(
            doc_id=doc_id, layer_ids=layer_ids, group_name=group_name, canvas_path=canvas_path
        )

    async def layer_ungroup(self, doc_id: str, layer_id: str, canvas_path: str = "") -> list[str]:
        """Delegate to the active backend."""
        return await self._current().layer_ungroup(
            doc_id=doc_id, layer_id=layer_id, canvas_path=canvas_path
        )

    async def import_asset(
        self, doc_id: str, file_path: str, canvas_path: str = ""
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().import_asset(
            doc_id=doc_id, file_path=file_path, canvas_path=canvas_path
        )

    async def param_get(
        self, doc_id: str, layer_id: str, param_name: str, canvas_path: str = ""
    ) -> SynfigValue | None:
        """Delegate to the active backend."""
        return await self._current().param_get(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name, canvas_path=canvas_path
        )

    async def param_set(
        self,
        doc_id: str,
        layer_id: str,
        param_name: str,
        value: SynfigValue | Any,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().param_set(
            doc_id=doc_id,
            layer_id=layer_id,
            param_name=param_name,
            value=value,
            canvas_path=canvas_path,
        )

    async def param_convert(
        self, doc_id: str, layer_id: str, param_name: str, type: str
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().param_convert(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name, type=type
        )

    async def param_export(
        self, doc_id: str, layer_id: str, param_name: str, name: str
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().param_export(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name, name=name
        )

    async def param_unexport(self, doc_id: str, name: str) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().param_unexport(doc_id=doc_id, name=name)

    async def param_link(
        self, doc_id: str, layer_id: str, param_name: str, link_id: str
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().param_link(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name, link_id=link_id
        )

    async def param_list(
        self, doc_id: str, layer_id: str, canvas_path: str = ""
    ) -> list[dict[str, Any]]:
        """Delegate to the active backend."""
        return await self._current().param_list(
            doc_id=doc_id, layer_id=layer_id, canvas_path=canvas_path
        )

    async def anim_waypoint_list(
        self, doc_id: str, layer_id: str, param_name: str
    ) -> list[dict[str, Any]]:
        """Delegate to the active backend."""
        return await self._current().anim_waypoint_list(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name
        )

    async def canvas_create(self, doc_id: str, canvas_id: str) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().canvas_create(doc_id=doc_id, canvas_id=canvas_id)

    async def canvas_rename(self, doc_id: str, canvas_id: str, name: str) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().canvas_rename(doc_id=doc_id, canvas_id=canvas_id, name=name)

    async def canvas_delete(self, doc_id: str, canvas_id: str) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().canvas_delete(doc_id=doc_id, canvas_id=canvas_id)

    async def canvas_set_properties(
        self,
        doc_id: str,
        canvas_id: str,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        background_color: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().canvas_set_properties(
            doc_id=doc_id,
            canvas_id=canvas_id,
            width=width,
            height=height,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
            background_color=background_color,
        )

    async def bone_add(
        self,
        doc_id: str,
        layer_id: str,
        time: float = 0.0,
        origin: tuple[float, float] = (0.0, 0.0),
        angle: float = 0.0,
        width: float = 1.0,
        tip_width: float = 1.0,
        parent_index: int = -1,
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().bone_add(
            doc_id=doc_id,
            layer_id=layer_id,
            time=time,
            origin=origin,
            angle=angle,
            width=width,
            tip_width=tip_width,
            parent_index=parent_index,
        )

    async def anim_time_get(self, doc_id: str) -> float:
        """Delegate to the active backend."""
        return await self._current().anim_time_get(doc_id=doc_id)

    async def anim_time_set(self, doc_id: str, time: float | str) -> float:
        """Delegate to the active backend."""
        return await self._current().anim_time_set(doc_id=doc_id, time=time)

    async def anim_keyframe_add(
        self,
        doc_id: str,
        time: float | str,
        description: str = "",
        active: bool = True,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().anim_keyframe_add(
            doc_id=doc_id,
            time=time,
            description=description,
            active=active,
            canvas_path=canvas_path,
        )

    async def anim_keyframe_remove(
        self, doc_id: str, time: float | str, canvas_path: str = ""
    ) -> bool:
        """Delegate to the active backend."""
        return await self._current().anim_keyframe_remove(
            doc_id=doc_id, time=time, canvas_path=canvas_path
        )

    async def anim_keyframe_list(self, doc_id: str, canvas_path: str = "") -> list[dict[str, Any]]:
        """Delegate to the active backend."""
        return await self._current().anim_keyframe_list(doc_id=doc_id, canvas_path=canvas_path)

    async def anim_waypoint_set(
        self,
        doc_id: str,
        layer_id: str,
        param_name: str,
        time: float | str,
        value: SynfigValue | Any,
        interpolation: str | None = None,
        interpolation_in: str | None = None,
        interpolation_out: str | None = None,
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().anim_waypoint_set(
            doc_id=doc_id,
            layer_id=layer_id,
            param_name=param_name,
            time=time,
            value=value,
            interpolation=interpolation,
            interpolation_in=interpolation_in,
            interpolation_out=interpolation_out,
        )

    async def anim_waypoint_remove(
        self, doc_id: str, layer_id: str, param_name: str, time: float | str
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().anim_waypoint_remove(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name, time=time
        )

    async def anim_animate_param(
        self, doc_id: str, layer_id: str, param_name: str, waypoints: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().anim_animate_param(
            doc_id=doc_id, layer_id=layer_id, param_name=param_name, waypoints=waypoints
        )

    async def anim_interpolation_set(
        self,
        doc_id: str,
        interpolation: str,
        layer_id: str | None = None,
        param_name: str | None = None,
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().anim_interpolation_set(
            doc_id=doc_id, interpolation=interpolation, layer_id=layer_id, param_name=param_name
        )

    async def undo(self, doc_id: str) -> bool:
        """Delegate to the active backend."""
        return await self._current().undo(doc_id=doc_id)

    async def redo(self, doc_id: str) -> bool:
        """Delegate to the active backend."""
        return await self._current().redo(doc_id=doc_id)

    async def history_list(self, doc_id: str) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().history_list(doc_id=doc_id)

    async def selection_get(self, doc_id: str) -> list[str]:
        """Delegate to the active backend."""
        return await self._current().selection_get(doc_id=doc_id)

    async def selection_set(self, doc_id: str, layer_ids: list[str]) -> list[str]:
        """Delegate to the active backend."""
        return await self._current().selection_set(doc_id=doc_id, layer_ids=layer_ids)

    async def render_frame(
        self,
        doc_id: str,
        output_path: str,
        time: float | str = 0.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
    ) -> bool:
        """Delegate to the active backend."""
        return await self._current().render_frame(
            doc_id=doc_id,
            output_path=output_path,
            time=time,
            width=width,
            height=height,
            target=target,
        )

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
        """Delegate to the active backend."""
        return await self._current().render_sequence(
            doc_id=doc_id,
            output_dir=output_dir,
            start_time=start_time,
            end_time=end_time,
            fps=fps,
            width=width,
            height=height,
            target=target,
            progress_cb=progress_cb,
            cancel_token=cancel_token,
        )

    async def render_video(
        self,
        doc_id: str,
        output_path: str,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
        progress_cb: Any = None,
        cancel_token: Any = None,
    ) -> bool:
        """Delegate to the active backend."""
        return await self._current().render_video(
            doc_id=doc_id,
            output_path=output_path,
            start_time=start_time,
            end_time=end_time,
            fps=fps,
            width=width,
            height=height,
            progress_cb=progress_cb,
            cancel_token=cancel_token,
        )

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
        """Delegate to the active backend."""
        return await self._current().render_contact_sheet(
            doc_id=doc_id,
            output_path=output_path,
            cols=cols,
            rows=rows,
            width=width,
            height=height,
            start_time=start_time,
            end_time=end_time,
        )

    async def scene_build(self, spec: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().scene_build(spec=spec, dry_run=dry_run)

    async def scene_export_spec(
        self, doc_id: str, scope: str = "canvas", fields: list[str] | None = None
    ) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().scene_export_spec(doc_id=doc_id, scope=scope, fields=fields)

    async def scene_summary(self, doc_id: str, budget_tokens: int = 500) -> dict[str, Any]:
        """Delegate to the active backend."""
        return await self._current().scene_summary(doc_id=doc_id, budget_tokens=budget_tokens)
