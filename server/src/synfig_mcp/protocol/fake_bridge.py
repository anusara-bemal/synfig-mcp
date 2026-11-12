"""
In-process Fake Bridge Server for contract tests and local development without Synfig Studio.
Fully implements the protocol/schema/*.json specification.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from synfig_mcp.logging import get_logger

logger = get_logger("synfig_mcp.protocol.fake_bridge")

MAX_MESSAGE_SIZE = 10 * 1024 * 1024
DEFAULT_FAKE_TOKEN = "0123456789abcdef0123456789abcdef"  # nosec B105

#: Layer types of Synfig 1.5.5.  The fake bridge rejects unknown types exactly
#: like the native bridge does, so the contract tests exercise the same paths.
KNOWN_LAYER_TYPES: frozenset[str] = frozenset(
    {
        "advanced_outline",
        "bevel",
        "blur",
        "checker_board",
        "chromakey",
        "circle",
        "clamp",
        "colorcorrect",
        "conical_gradient",
        "curve_gradient",
        "curve_warp",
        "duplicate",
        "filter_group",
        "freetime",
        "group",
        "halftone2",
        "halftone3",
        "import",
        "inside_out",
        "julia",
        "linear_gradient",
        "lumakey",
        "mandelbrot",
        "metaballs",
        "motion_blur",
        "noise",
        "noise_distort",
        "outline",
        "PasteCanvas",
        "plant",
        "polygon",
        "radial_blur",
        "radial_gradient",
        "rectangle",
        "region",
        "rotate",
        "shade",
        "simple_circle",
        "skeleton",
        "skeleton_deformation",
        "solid_color",
        "sound",
        "spherize",
        "spiral_gradient",
        "star",
        "stretch",
        "stroboscope",
        "super_sample",
        "switch",
        "text",
        "timeloop",
        "translate",
        "twirl",
        "warp",
        "xor_pattern",
        "zoom",
    }
)


class FakeBridgeServer:
    """In-process TCP server simulating Synfig Studio's C++ mcp_bridge."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,  # 0 binds to an ephemeral OS-assigned free port
        token: str = DEFAULT_FAKE_TOKEN,
        protocol_version: str = "1.0",
        studio_version: str = "1.5.5",
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.protocol_version = protocol_version
        self.studio_version = studio_version

        self._server: asyncio.Server | None = None
        self._clients: set[asyncio.StreamWriter] = set()
        self._authenticated_clients: set[asyncio.StreamWriter] = set()
        self.assigned_port: int = 0

        # Injectable behaviors for edge case testing
        self.delay_response_seconds: float = 0.0
        self.close_on_next_request: bool = False
        self.send_malformed_json: bool = False

        self._fake_docs: dict[str, dict[str, Any]] = {}
        self._fake_time: float = 0.0
        self._fake_keyframes: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start the fake bridge TCP server."""
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        sockets = self._server.sockets
        if sockets:
            self.assigned_port = sockets[0].getsockname()[1]
        logger.info("Fake bridge started", host=self.host, port=self.assigned_port)

    async def stop(self) -> None:
        """Stop server and disconnect all clients."""
        for writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.debug("Error stopping client writer", error=str(e))
        self._clients.clear()
        self._authenticated_clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("Fake bridge stopped")

    async def broadcast_event(self, method: str, params: dict[str, Any]) -> None:
        """Broadcast notification event to all authenticated clients."""
        event = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        payload = (json.dumps(event) + "\n").encode("utf-8")
        for writer in list(self._authenticated_clients):
            try:
                writer.write(payload)
                await writer.drain()
            except Exception:
                self._authenticated_clients.discard(writer)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle individual client connection."""
        self._clients.add(writer)
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                if len(line) > MAX_MESSAGE_SIZE:
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": 1005, "message": "Oversized message"},
                    }
                    writer.write((json.dumps(err_resp) + "\n").encode("utf-8"))
                    await writer.drain()
                    break

                if self.close_on_next_request:
                    break

                if self.send_malformed_json:
                    writer.write(b"INVALID_JSON_CORRUPTED_LINE\n")
                    await writer.drain()
                    continue

                if self.delay_response_seconds > 0:
                    await asyncio.sleep(self.delay_response_seconds)

                text = line.decode("utf-8").strip()
                if not text:
                    continue

                try:
                    req = json.loads(text)
                except Exception:
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    }
                    writer.write((json.dumps(err_resp) + "\n").encode("utf-8"))
                    await writer.drain()
                    continue

                resp = self._dispatch(req, writer)
                writer.write((json.dumps(resp) + "\n").encode("utf-8"))
                await writer.drain()
        except Exception as e:
            logger.debug("Client handler error", error=str(e))
        finally:
            self._clients.discard(writer)
            self._authenticated_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.debug("Error closing client handler", error=str(e))

    def _dispatch(self, req: dict[str, Any], writer: asyncio.StreamWriter) -> dict[str, Any]:
        """Dispatch JSON-RPC request to mock handlers."""
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        # Handshake
        if method == "hello":
            client_token = params.get("token")
            client_version = params.get("protocol_version", "")
            if client_token != self.token:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": 1002, "message": "Authentication failed: invalid token"},
                }

            client_major = client_version.split(".")[0] if client_version else ""
            server_major = self.protocol_version.split(".")[0]
            if client_major != server_major:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": 1003,
                        "message": f"Incompatible protocol version: client {client_version} vs server {self.protocol_version}",
                    },
                }

            self._authenticated_clients.add(writer)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocol_version": self.protocol_version,
                    "studio_version": self.studio_version,
                    "capabilities": [
                        "doc",
                        "canvas",
                        "layer",
                        "param",
                        "anim",
                        "history",
                        "selection",
                    ],
                    "session_id": "sess_fake_1234",
                },
            }

        # Check authentication for all other calls
        if writer not in self._authenticated_clients:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": 1002, "message": "Client not authenticated. Call hello first."},
            }

        # Document methods
        if method == "doc.list":
            if not self._fake_docs:
                self._fake_docs["doc_0"] = {
                    "id": "doc_0",
                    "doc_id": "doc_0",
                    "name": "Synfig Animation 1",
                    "file_path": None,
                    "width": 1920,
                    "height": 1080,
                    "fps": 24.0,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "duration_frames": 120,
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": list(self._fake_docs.values()),
            }

        if method == "doc.new":
            d_id = f"doc_{len(self._fake_docs)}"
            doc_obj = {
                "id": d_id,
                "doc_id": d_id,
                "name": params.get("name", f"Synfig Animation {len(self._fake_docs) + 1}"),
                "file_path": None,
                "width": params.get("width", 1920),
                "height": params.get("height", 1080),
                "fps": params.get("fps", 24.0),
                "start_time": 0.0,
                "end_time": 5.0,
                "duration_frames": 120,
            }
            self._fake_docs[d_id] = doc_obj
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": doc_obj,
            }

        if method in ("doc.info", "doc.open"):
            doc_id = params.get("doc_id", "doc_0")
            cached_doc = self._fake_docs.get(doc_id)
            if not cached_doc:
                cached_doc = {
                    "id": doc_id,
                    "doc_id": doc_id,
                    "name": "Synfig Animation 1",
                    "file_path": params.get("file_path", None),
                    "width": 1920,
                    "height": 1080,
                    "fps": 24.0,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "duration_frames": 120,
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": cached_doc,
            }

        if method == "doc.set_properties":
            doc_id = params.get("doc_id", "doc_0")
            cached_doc = self._fake_docs.get(doc_id)
            if not cached_doc:
                cached_doc = {
                    "id": doc_id,
                    "doc_id": doc_id,
                    "name": "Synfig Animation 1",
                    "file_path": None,
                    "width": 1920,
                    "height": 1080,
                    "fps": 24.0,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "duration_frames": 120,
                }
            if "width" in params:
                cached_doc["width"] = params["width"]
            if "height" in params:
                cached_doc["height"] = params["height"]
            if "fps" in params:
                cached_doc["fps"] = params["fps"]
            if "name" in params:
                cached_doc["name"] = params["name"]
            self._fake_docs[doc_id] = cached_doc
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": cached_doc,
            }

        if method == "doc.save":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"file_path": params.get("file_path", "doc_0.sifz")},
            }

        if method == "doc.close":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"closed": True},
            }

        if method == "canvas.list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"canvases": ["/"]},
            }

        if method == "scene.tree":
            # Layers created through scene.build are reported after the canned
            # layer, so tools that read back what they built see their layers.
            built = [
                {
                    "id": lyr["id"],
                    "desc": lyr["id"],
                    "description": lyr["id"],
                    "type": lyr.get("type", "circle"),
                    "active": True,
                    "depth": index + 1,
                    "params": {
                        k: v for k, v in (lyr.get("params") or {}).items() if isinstance(v, dict)
                    },
                    "children": [],
                }
                for index, lyr in enumerate(
                    self._fake_docs.get(params.get("doc_id", "doc_0"), {}).get("layers", [])
                )
            ]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "canvas_path": params.get("canvas_path", "/"),
                    "name": "Synfig Animation 1",
                    "width": 1920,
                    "height": 1080,
                    "fps": 24.0,
                    "duration_frames": 120,
                    "layers": [
                        {
                            "id": "Circle001",
                            "desc": "Circle001",
                            "description": "Circle001",
                            "type": "circle",
                            "active": True,
                            "depth": 0,
                            "params": {
                                "radius": {"type": "real", "value": 1.5},
                                "color": {
                                    "type": "color",
                                    "r": 0.2,
                                    "g": 0.6,
                                    "b": 1.0,
                                    "a": 1.0,
                                },
                            },
                            "children": [],
                        },
                        *built,
                    ],
                },
            }

        if method == "layer.add":
            layer_type = params.get("layer_type", "circle")
            if layer_type not in KNOWN_LAYER_TYPES:
                # The real bridge refuses unknown layer types; the fake has to
                # behave the same so the contract tests stay meaningful.
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": f"Failed to create layer of type: {layer_type}",
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": "circle_001",
                    "layer_type": layer_type,
                    "description": params.get("description", "Circle001"),
                    "depth": params.get("depth", 0),
                    "diff": {
                        "action": "layer.add",
                        "created": ["circle_001"],
                        "modified": [],
                        "deleted": [],
                    },
                },
            }

        if method == "layer.remove":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "removed": True,
                    "diff": {
                        "action": "layer.remove",
                        "created": [],
                        "modified": [],
                        "deleted": [params.get("layer_id", "")],
                    },
                },
            }

        if method in ("layer.duplicate", "layer.reorder", "layer.raise", "layer.lower"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "depth": params.get("new_depth", 0),
                    "reordered": True,
                    "raised": True,
                    "lowered": True,
                    "diff": {"action": method, "created": [], "modified": [], "deleted": []},
                },
            }

        if method == "layer.group":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "group_id": params.get("group_name", "Group"),
                    "grouped_layers": params.get("layer_ids", []),
                },
            }

        if method == "layer.ungroup":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "ungrouped_layers": ["Circle001"],
                },
            }

        if method == "param.get":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "value": {"type": "real", "value": 1.5},
                },
            }

        if method == "param.set":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "radius"),
                    "before": {"type": "real", "value": 1.0},
                    "after": params.get("value", {"type": "real", "value": 1.5}),
                },
            }

        if method == "anim.time_get":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"time": {"seconds": self._fake_time}},
            }

        if method == "anim.time_set":
            t = params.get("time", 0.0)
            self._fake_time = float(t) if isinstance(t, (int, float)) else 0.0
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"time": {"seconds": self._fake_time}},
            }

        if method == "anim.keyframe_add":
            t = float(params.get("time", 0.0))
            kf = {"time": t, "description": params.get("description", ""), "active": True}
            self._fake_keyframes.append(kf)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "time": t,
                    "description": kf["description"],
                    "active": True,
                    "diff": {
                        "action": "anim.keyframe_add",
                        "created": [f"kf_{t}"],
                        "modified": [],
                        "deleted": [],
                    },
                },
            }

        if method == "anim.keyframe_list":
            if not self._fake_keyframes:
                self._fake_keyframes = [{"time": 0.0, "description": "Start", "active": True}]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "keyframes": self._fake_keyframes,
                },
            }

        if method == "anim.keyframe_remove":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"removed": True},
            }

        if method == "selection.get":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"selected_layers": ["Circle001"]},
            }

        if method == "selection.set":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"selected_layers": params.get("layer_ids", [])},
            }

        if method in ("history.undo", "history.redo"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": True},
            }

        if method == "history.list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"undo_count": 1, "redo_count": 0},
            }

        if method == "render.frame":
            out_path_str = params.get("output_path")
            if out_path_str:
                out_p = Path(out_path_str)
                out_p.parent.mkdir(parents=True, exist_ok=True)
                if not out_p.exists():
                    try:
                        from PIL import Image

                        img = Image.new("RGBA", (16, 16), (100, 150, 200, 255))
                        img.save(out_p)
                    except Exception:
                        out_p.write_bytes(
                            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                        )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": True},
            }

        if method == "doc.set_time_range":
            doc_id = params.get("doc_id", "doc_0")
            cached_doc = self._fake_docs.get(doc_id, {})
            if "start_time" in params:
                cached_doc["start_time"] = float(params["start_time"])
            elif "begin_time" in params:
                cached_doc["start_time"] = float(params["begin_time"])
            if "end_time" in params:
                cached_doc["end_time"] = float(params["end_time"])
            if "fps" in params:
                cached_doc["fps"] = float(params["fps"])
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": doc_id,
                    "start_time": cached_doc.get("start_time", 0.0),
                    "end_time": cached_doc.get("end_time", 5.0),
                    "fps": cached_doc.get("fps", 24.0),
                },
            }

        if method == "param.convert":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "radius"),
                    "type": params.get("type", "scale"),
                },
            }

        if method == "param.export":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "radius"),
                    "name": params.get("name", "ExportedVal"),
                },
            }

        if method == "param.unexport":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "name": params.get("name", "ExportedVal"),
                },
            }

        if method in ("anim.waypoint_set", "waypoint.set"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "origin"),
                    "time": params.get("time", 0.0),
                    "value": params.get("value", {}),
                    "interpolation_in": params.get("interpolation_in", "linear"),
                    "interpolation_out": params.get("interpolation_out", "linear"),
                },
            }

        if method in ("anim.waypoint_remove", "waypoint.remove", "waypoint.delete"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "origin"),
                    "time": params.get("time", 0.0),
                },
            }

        if method == "anim.animate_param":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "origin"),
                    "waypoint_count": len(params.get("waypoints", [])),
                },
            }

        if method == "anim.interpolation_set":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "interpolation": params.get("interpolation", "tcb"),
                },
            }

        if method == "scene.build":
            doc_id = params.get("doc_id", "doc_0")
            layers_spec = params.get("layers", [])
            groups_spec = params.get("groups", [])
            created: list[str] = []
            doc_layers = self._fake_docs.setdefault(doc_id, {}).setdefault("layers", [])
            for lyr in layers_spec:
                l_id = lyr.get("id", "Layer")
                created.append(l_id)
                doc_layers.append(
                    {
                        "id": l_id,
                        "name": l_id,
                        "type": lyr.get("type", "circle"),
                        "depth": lyr.get("depth", 0),
                        "params": lyr.get("params", {}),
                        "waypoints": lyr.get("waypoints", []),
                    }
                )
            for g in groups_spec:
                g_id = g.get("id", "Group")
                created.append(g_id)
                doc_layers.append(
                    {
                        "id": g_id,
                        "name": g_id,
                        "type": "group",
                        "depth": 0,
                        "params": {},
                        "waypoints": [],
                        "children": g.get("layer_ids", []),
                    }
                )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": doc_id,
                    "diff": {
                        "action": "scene.build",
                        "created": created,
                        "modified": [],
                        "deleted": [],
                    },
                },
            }

        if method == "schema.list_layers":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "count": 6,
                    "layers": [
                        {
                            "name": "circle",
                            "local_name": "Circle",
                            "category": "Geometry",
                            "version": "0.1",
                            "params": {
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "radius": {
                                    "type": "real",
                                    "local_name": "Radius",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "origin": {
                                    "type": "vector",
                                    "local_name": "Origin",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "rectangle",
                            "local_name": "Rectangle",
                            "category": "Geometry",
                            "version": "0.1",
                            "params": {
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "point1": {
                                    "type": "vector",
                                    "local_name": "Point 1",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "point2": {
                                    "type": "vector",
                                    "local_name": "Point 2",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "star",
                            "local_name": "Star",
                            "category": "Geometry",
                            "version": "0.1",
                            "params": {
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "radius1": {
                                    "type": "real",
                                    "local_name": "Radius 1",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "radius2": {
                                    "type": "real",
                                    "local_name": "Radius 2",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "points": {
                                    "type": "integer",
                                    "local_name": "Points",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "text",
                            "local_name": "Text",
                            "category": "Typography",
                            "version": "0.1",
                            "params": {
                                "text": {
                                    "type": "string",
                                    "local_name": "Text",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "solid_color",
                            "local_name": "Solid Color",
                            "category": "Geometry",
                            "version": "0.1",
                            "params": {
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "outline",
                            "local_name": "Outline",
                            "category": "Geometry",
                            "version": "0.1",
                            "params": {
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "width": {
                                    "type": "real",
                                    "local_name": "Width",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "bline": {
                                    "type": "bline_point_list",
                                    "local_name": "Spline",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "region",
                            "local_name": "Region",
                            "category": "Geometry",
                            "version": "0.1",
                            "params": {
                                "color": {
                                    "type": "color",
                                    "local_name": "Color",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "bline": {
                                    "type": "bline_point_list",
                                    "local_name": "Spline",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "blur",
                            "local_name": "Blur",
                            "category": "Blurs",
                            "version": "0.1",
                            "params": {
                                "size": {
                                    "type": "vector",
                                    "local_name": "Size",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "type": {
                                    "type": "integer",
                                    "local_name": "Type",
                                    "writable": True,
                                    "animatable": True,
                                },
                            },
                        },
                        {
                            "name": "PasteCanvas",
                            "local_name": "Group",
                            "category": "Composite",
                            "version": "0.1",
                            "params": {
                                "origin": {
                                    "type": "vector",
                                    "local_name": "Origin",
                                    "writable": True,
                                    "animatable": True,
                                },
                                "canvas": {
                                    "type": "canvas",
                                    "local_name": "Canvas",
                                    "writable": True,
                                    "animatable": False,
                                },
                            },
                        },
                    ],
                },
            }

        if method == "param.list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", ""),
                    "params": [
                        {"name": "radius", "value": {"type": "real", "value": 1.5}},
                        {
                            "name": "color",
                            "value": {"type": "color", "r": 0.2, "g": 0.6, "b": 1.0, "a": 1.0},
                        },
                    ],
                },
            }

        if method == "anim.waypoint_list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", ""),
                    "param_name": params.get("param_name", ""),
                    "waypoints": [
                        {
                            "time": 0.0,
                            "value": {"type": "real", "value": 1.0},
                            "interpolation_in": "linear",
                            "interpolation_out": "linear",
                        },
                        {
                            "time": 1.0,
                            "value": {"type": "real", "value": 3.0},
                            "interpolation_in": "linear",
                            "interpolation_out": "linear",
                        },
                    ],
                },
            }

        if method in ("canvas.create", "canvas.rename", "canvas.delete", "canvas.set_properties"):
            canvas_id = params.get("canvas_id", params.get("id", "canvas1"))
            action = method.split(".")[1]
            result: dict[str, Any] = {
                "doc_id": params.get("doc_id", "doc_0"),
                "canvas_id": canvas_id,
                "diff": {
                    "action": f"canvas.{action}",
                    "created": [canvas_id] if action == "create" else [],
                    "modified": [canvas_id] if action in ("rename", "set_properties") else [],
                    "deleted": [canvas_id] if action == "delete" else [],
                },
            }
            if action == "rename":
                result["name"] = params.get("name", "")
                result["previous_name"] = canvas_id
            if action == "set_properties":
                result["name"] = canvas_id
                result["width"] = params.get("width", 1920)
                result["height"] = params.get("height", 1080)
                result["fps"] = params.get("fps", 24.0)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        if method == "param.link":
            link_id = params.get("link_id", params.get("name", ""))
            if not link_id:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing value node id"},
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", ""),
                    "param_name": params.get("param_name", ""),
                    "link_id": link_id,
                    "diff": {
                        "action": "param.link",
                        "created": [],
                        "modified": [params.get("layer_id", "")],
                        "deleted": [],
                    },
                },
            }

        if method == "param.export":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", ""),
                    "param_name": params.get("param_name", ""),
                    "name": params.get("name", ""),
                    "diff": {
                        "action": "param.export",
                        "created": [params.get("name", "")],
                        "modified": [params.get("layer_id", "")],
                        "deleted": [],
                    },
                },
            }

        if method == "param.unexport":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "name": params.get("name", ""),
                    "diff": {
                        "action": "param.unexport",
                        "created": [],
                        "modified": [],
                        "deleted": [params.get("name", "")],
                    },
                },
            }

        # Default fallback
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"status": "ok", "method": method},
        }
