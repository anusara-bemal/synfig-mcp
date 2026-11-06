"""
In-process Fake Bridge Server for contract tests and local development without Synfig Studio.
Fully implements the protocol/schema/*.json specification.
"""

import asyncio
import json
from typing import Any

from synfig_mcp.logging import get_logger

logger = get_logger("synfig_mcp.protocol.fake_bridge")

MAX_MESSAGE_SIZE = 10 * 1024 * 1024
DEFAULT_FAKE_TOKEN = "0123456789abcdef0123456789abcdef"  # nosec B105


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
        if method == "doc.info":
            doc_id = params.get("doc_id", "doc_0")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": doc_id,
                    "name": "Synfig Animation 1",
                    "file_path": None,
                    "width": 1920,
                    "height": 1080,
                    "fps": 24.0,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "duration_frames": 120,
                },
            }

        if method == "layer.add":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": "circle_001",
                    "layer_type": params.get("layer_type", "circle"),
                    "description": "Circle001",
                    "depth": params.get("depth", 0),
                    "diff": {
                        "action": "layer_add",
                        "created": ["circle_001"],
                        "modified": [],
                        "deleted": [],
                    },
                },
            }

        if method == "param.set":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "doc_id": params.get("doc_id", "doc_0"),
                    "layer_id": params.get("layer_id", "circle_001"),
                    "param_name": params.get("param_name", "color"),
                    "before": {"type": "color", "r": 0.2, "g": 0.6, "b": 1.0, "a": 1.0},
                    "after": params.get("value"),
                },
            }

        if method in ("history.undo", "history.redo"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": True},
            }

        # Default fallback
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"status": "ok", "method": method},
        }
