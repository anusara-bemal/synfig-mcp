"""
LiveBackend: communicates with running Synfig Studio via native C++ bridge (mcp_bridge).

Implements the unified BackendBase interface by translating requests to JSON-RPC 2.0 calls
marshalled into Studio's GTK main thread and action system.
"""

from typing import Any

from pydantic import TypeAdapter

from synfig_mcp.backend.base import BackendBase, DocumentInfo, HealthStatus
from synfig_mcp.config import settings
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.models import SynfigValue

synfig_value_adapter: TypeAdapter[SynfigValue] = TypeAdapter(SynfigValue)


class LiveBackend(BackendBase):
    """Primary backend connecting to running Synfig Studio via native C++ bridge."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        token: str | None = None,
        client: BridgeClient | None = None,
    ) -> None:
        self.host = host or settings.bridge_host
        self.port = port or settings.bridge_port
        self.token = token
        self._client = client

    @property
    def name(self) -> str:
        return "live"

    def _get_token(self) -> str:
        if self.token:
            return self.token
        if settings.bridge_token_path.is_file():
            return settings.bridge_token_path.read_text(encoding="utf-8").strip()
        return ""

    async def _ensure_client(self) -> BridgeClient:
        if self._client is None or not self._client.is_connected:
            token = self._get_token()
            self._client = BridgeClient(host=self.host, port=self.port, token=token)
            await self._client.connect(timeout=settings.bridge_connect_timeout_seconds)
        return self._client

    async def health_check(self) -> HealthStatus:
        """Probe the live bridge socket and report capabilities."""
        try:
            client = await self._ensure_client()
            return HealthStatus(
                backend="live",
                connected=True,
                studio_running=True,
                details={
                    "host": self.host,
                    "port": self.port,
                    "capabilities": client.capabilities,
                },
            )
        except Exception as e:
            return HealthStatus(
                backend="live",
                connected=False,
                studio_running=False,
                details={"host": self.host, "port": self.port, "error": str(e)},
            )

    async def doc_list(self) -> list[DocumentInfo]:
        client = await self._ensure_client()
        res = await client.call("doc.list")
        return [DocumentInfo.model_validate(d) for d in res]

    async def doc_new(
        self, width: int = 1920, height: int = 1080, fps: float = 24.0
    ) -> DocumentInfo:
        client = await self._ensure_client()
        res = await client.call("doc.new", {"width": width, "height": height, "fps": fps})
        return DocumentInfo.model_validate(res)

    async def doc_open(self, file_path: str) -> DocumentInfo:
        client = await self._ensure_client()
        res = await client.call("doc.open", {"file_path": file_path})
        return DocumentInfo.model_validate(res)

    async def doc_save(self, doc_id: str, file_path: str | None = None) -> str:
        client = await self._ensure_client()
        params: dict[str, Any] = {"doc_id": doc_id}
        if file_path:
            params["file_path"] = file_path
        res = await client.call("doc.save", params)
        return str(res.get("file_path", file_path or ""))

    async def doc_close(self, doc_id: str) -> bool:
        client = await self._ensure_client()
        res = await client.call("doc.close", {"doc_id": doc_id})
        return bool(res.get("closed", True))

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
        client = await self._ensure_client()
        params: dict[str, Any] = {"doc_id": doc_id}
        if name is not None:
            params["name"] = name
        if desc is not None:
            params["description"] = desc
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        if fps is not None:
            params["fps"] = fps
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time

        res = await client.call("doc.set_properties", params)
        return DocumentInfo.model_validate(res)

    async def canvas_list(self, doc_id: str) -> list[str]:
        client = await self._ensure_client()
        res = await client.call("canvas.list", {"doc_id": doc_id})
        return list(res.get("canvases", []))

    async def scene_tree(self, doc_id: str, canvas_path: str = "") -> dict[str, Any]:
        client = await self._ensure_client()
        res = await client.call("scene.tree", {"doc_id": doc_id, "canvas_path": canvas_path})
        return dict(res)

    async def layer_add(
        self,
        doc_id: str,
        layer_type: str,
        canvas_path: str = "",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        p: dict[str, Any] = {
            "doc_id": doc_id,
            "layer_type": layer_type,
            "canvas_path": canvas_path,
        }
        if params:
            p["params"] = params
        res = await client.call("layer.add", p)
        return dict(res)

    async def layer_remove(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        client = await self._ensure_client()
        res = await client.call(
            "layer.remove",
            {"doc_id": doc_id, "layer_id": layer_id, "canvas_path": canvas_path},
        )
        return bool(res.get("removed", True))

    async def layer_duplicate(
        self, doc_id: str, layer_id: str, canvas_path: str = ""
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        res = await client.call(
            "layer.duplicate",
            {"doc_id": doc_id, "layer_id": layer_id, "canvas_path": canvas_path},
        )
        return dict(res)

    async def layer_reorder(
        self, doc_id: str, layer_id: str, new_depth: int, canvas_path: str = ""
    ) -> bool:
        client = await self._ensure_client()
        res = await client.call(
            "layer.reorder",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "new_depth": new_depth,
                "canvas_path": canvas_path,
            },
        )
        return bool(res.get("reordered", True))

    async def layer_raise(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        client = await self._ensure_client()
        res = await client.call(
            "layer.raise",
            {"doc_id": doc_id, "layer_id": layer_id, "canvas_path": canvas_path},
        )
        return bool(res.get("raised", True))

    async def layer_lower(self, doc_id: str, layer_id: str, canvas_path: str = "") -> bool:
        client = await self._ensure_client()
        res = await client.call(
            "layer.lower",
            {"doc_id": doc_id, "layer_id": layer_id, "canvas_path": canvas_path},
        )
        return bool(res.get("lowered", True))

    async def layer_group(
        self,
        doc_id: str,
        layer_ids: list[str],
        group_name: str = "Group",
        canvas_path: str = "",
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        res = await client.call(
            "layer.group",
            {
                "doc_id": doc_id,
                "layer_ids": layer_ids,
                "group_name": group_name,
                "canvas_path": canvas_path,
            },
        )
        return dict(res)

    async def layer_ungroup(self, doc_id: str, layer_id: str, canvas_path: str = "") -> list[str]:
        client = await self._ensure_client()
        res = await client.call(
            "layer.ungroup",
            {"doc_id": doc_id, "layer_id": layer_id, "canvas_path": canvas_path},
        )
        return list(res.get("ungrouped_layers", []))

    async def param_get(
        self, doc_id: str, layer_id: str, param_name: str, canvas_path: str = ""
    ) -> SynfigValue | None:
        client = await self._ensure_client()
        res = await client.call(
            "param.get",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": param_name,
                "canvas_path": canvas_path,
            },
        )
        val = res.get("value")
        return synfig_value_adapter.validate_python(val) if val else None

    async def param_set(
        self,
        doc_id: str,
        layer_id: str,
        param_name: str,
        value: SynfigValue | Any,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        val_dict = value.model_dump() if hasattr(value, "model_dump") else value
        res = await client.call(
            "param.set",
            {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "param_name": param_name,
                "value": val_dict,
                "canvas_path": canvas_path,
            },
        )
        return dict(res)

    async def anim_time_get(self, doc_id: str) -> float:
        client = await self._ensure_client()
        res = await client.call("anim.time_get", {"doc_id": doc_id})
        t_val = res.get("time")
        if isinstance(t_val, dict):
            return float(t_val.get("seconds", 0.0))
        return float(t_val or 0.0)

    async def anim_time_set(self, doc_id: str, time: float | str) -> float:
        client = await self._ensure_client()
        t_in = float(time) if isinstance(time, (int, float)) else time
        res = await client.call("anim.time_set", {"doc_id": doc_id, "time": t_in})
        t_val = res.get("time")
        if isinstance(t_val, dict):
            return float(t_val.get("seconds", 0.0))
        return float(t_val or 0.0)

    async def anim_keyframe_add(
        self,
        doc_id: str,
        time: float | str,
        description: str = "",
        active: bool = True,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        t_val = float(time) if isinstance(time, (int, float)) else time
        res = await client.call(
            "anim.keyframe_add",
            {
                "doc_id": doc_id,
                "time": t_val,
                "description": description,
                "active": active,
                "canvas_path": canvas_path,
            },
        )
        return dict(res)

    async def anim_keyframe_remove(
        self, doc_id: str, time: float | str, canvas_path: str = ""
    ) -> bool:
        client = await self._ensure_client()
        t_val = float(time) if isinstance(time, (int, float)) else time
        res = await client.call(
            "anim.keyframe_remove",
            {"doc_id": doc_id, "time": t_val, "canvas_path": canvas_path},
        )
        return bool(res.get("removed", True))

    async def anim_keyframe_list(self, doc_id: str, canvas_path: str = "") -> list[dict[str, Any]]:
        client = await self._ensure_client()
        res = await client.call(
            "anim.keyframe_list", {"doc_id": doc_id, "canvas_path": canvas_path}
        )
        return list(res.get("keyframes", []))

    async def undo(self, doc_id: str) -> bool:
        client = await self._ensure_client()
        res = await client.call("history.undo", {"doc_id": doc_id})
        return bool(res.get("success", True))

    async def redo(self, doc_id: str) -> bool:
        client = await self._ensure_client()
        res = await client.call("history.redo", {"doc_id": doc_id})
        return bool(res.get("success", True))

    async def history_list(self, doc_id: str) -> dict[str, Any]:
        client = await self._ensure_client()
        res = await client.call("history.list", {"doc_id": doc_id})
        return dict(res)

    async def render_frame(
        self,
        doc_id: str,
        output_path: str,
        time: float | str = 0.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
    ) -> bool:
        client = await self._ensure_client()
        p: dict[str, Any] = {
            "doc_id": doc_id,
            "output_path": output_path,
            "time": time,
            "target": target,
        }
        if width is not None:
            p["width"] = width
        if height is not None:
            p["height"] = height
        res = await client.call("render.frame", p)
        return bool(res.get("success", True))
