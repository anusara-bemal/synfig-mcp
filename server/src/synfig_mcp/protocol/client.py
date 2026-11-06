"""
Async client communicating over TCP JSON-RPC with the Synfig Studio bridge.
"""

import asyncio
import json
from typing import Any

from synfig_mcp.errors import BridgeConnectionError
from synfig_mcp.protocol.models import JsonRpcRequest, JsonRpcResponse


class BridgeClient:
    """Async TCP JSON-RPC client."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._request_id = 0

    async def connect(self, timeout: float = 3.0) -> None:
        """Establish connection to bridge socket."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout,
            )
        except Exception as e:
            raise BridgeConnectionError(f"Could not connect to {self.host}:{self.port}") from e

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a request and wait for the response."""
        if not self._writer or not self._reader:
            raise BridgeConnectionError("Client is not connected to bridge")

        self._request_id += 1
        req = JsonRpcRequest(id=self._request_id, method=method, params=params or {})
        payload = json.dumps(req.model_dump()) + "\n"

        self._writer.write(payload.encode("utf-8"))
        await self._writer.drain()

        line = await self._reader.readline()
        if not line:
            raise BridgeConnectionError("Bridge closed connection prematurely")

        resp_dict = json.loads(line.decode("utf-8"))
        resp = JsonRpcResponse.model_validate(resp_dict)
        if resp.error:
            raise RuntimeError(f"Bridge error {resp.error.code}: {resp.error.message}")
        return resp.result

    async def close(self) -> None:
        """Close connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
