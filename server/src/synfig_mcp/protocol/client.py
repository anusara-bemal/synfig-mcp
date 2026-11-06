"""
Async TCP JSON-RPC 2.0 client for Synfig Studio mcp_bridge.
Implements request correlation, reconnect with backoff, cancellation, and event streaming.
"""

import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from typing import Any

from synfig_mcp.errors import (
    BridgeAuthError,
    BridgeConnectionError,
    ProtocolVersionMismatchError,
    SynfigError,
)
from synfig_mcp.logging import get_logger
from synfig_mcp.protocol.models import (
    HelloParams,
    HelloResult,
    JsonRpcNotification,
    JsonRpcRequest,
)

logger = get_logger("synfig_mcp.protocol.client")

MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB limit


class BridgeClient:
    """Production-grade async JSON-RPC 2.0 client for Synfig Studio bridge."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 19998,
        token: str | None = None,
        protocol_version: str = "1.0",
        default_timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.protocol_version = protocol_version
        self.default_timeout = default_timeout

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._request_id = 0
        self._pending_requests: dict[int | str, asyncio.Future[Any]] = {}
        self._event_queue: asyncio.Queue[JsonRpcNotification] = asyncio.Queue()
        self._listen_task: asyncio.Task[None] | None = None
        self._closed = False
        self._capabilities: list[str] = []

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._closed

    @property
    def capabilities(self) -> list[str]:
        return self._capabilities

    async def connect_with_retry(
        self,
        max_attempts: int = 3,
        initial_backoff: float = 0.2,
        max_backoff: float = 2.0,
    ) -> None:
        """Attempt connection with exponential backoff and jitter."""
        attempt = 0
        backoff = initial_backoff
        last_error: Exception | None = None

        while attempt < max_attempts:
            attempt += 1
            try:
                logger.debug(
                    "Connecting to bridge", attempt=attempt, host=self.host, port=self.port
                )
                await self.connect()
                return
            except (BridgeConnectionError, TimeoutError, OSError) as e:
                last_error = e
                if attempt >= max_attempts:
                    break
                jitter = secrets.SystemRandom().uniform(0.8, 1.2)
                sleep_time = min(backoff * jitter, max_backoff)
                await asyncio.sleep(sleep_time)
                backoff *= 2.0

        raise BridgeConnectionError(
            f"Failed to connect to bridge at {self.host}:{self.port} after {max_attempts} attempts"
        ) from last_error

    async def connect(self, timeout: float = 3.0) -> None:
        """Establish TCP connection, start listener, and perform handshake."""
        self._closed = False
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout,
            )
        except Exception as e:
            raise BridgeConnectionError(f"Could not connect to {self.host}:{self.port}") from e

        # Start background message dispatcher
        self._listen_task = asyncio.create_task(self._read_loop())

        # If token is provided, perform handshake
        if self.token:
            await self._handshake()

    async def _handshake(self) -> None:
        """Send hello handshake to bridge and verify compatibility."""
        params = HelloParams(
            protocol_version=self.protocol_version,
            token=self.token or "",
        )
        res = await self.call("hello", params.model_dump())
        hello_result = HelloResult.model_validate(res)

        server_major = hello_result.protocol_version.split(".")[0]
        client_major = self.protocol_version.split(".")[0]
        if server_major != client_major:
            await self.close()
            raise ProtocolVersionMismatchError(
                f"Bridge protocol version {hello_result.protocol_version} is incompatible with client {self.protocol_version}"
            )

        self._capabilities = hello_result.capabilities
        logger.info(
            "Bridge handshake successful",
            studio_version=hello_result.studio_version,
            capabilities=self._capabilities,
        )

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Send correlated JSON-RPC 2.0 call and wait for response."""
        if not self._writer or self._closed:
            raise BridgeConnectionError("Bridge client is not connected")

        self._request_id += 1
        req_id = self._request_id
        req = JsonRpcRequest(id=req_id, method=method, params=params or {})

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending_requests[req_id] = future

        payload = json.dumps(req.model_dump()) + "\n"
        if len(payload) > MAX_MESSAGE_SIZE:
            self._pending_requests.pop(req_id, None)
            raise SynfigError(f"Message exceeds maximum allowed size ({MAX_MESSAGE_SIZE} bytes)")

        effective_timeout = timeout if timeout is not None else self.default_timeout
        try:
            self._writer.write(payload.encode("utf-8"))
            await self._writer.drain()

            return await asyncio.wait_for(future, timeout=effective_timeout)
        except TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise SynfigError(
                f"Request {method} (id={req_id}) timed out after {effective_timeout}s"
            ) from None
        except Exception:
            self._pending_requests.pop(req_id, None)
            raise

    async def events(self) -> AsyncIterator[JsonRpcNotification]:
        """Stream server-to-client notifications."""
        while not self._closed:
            event = await self._event_queue.get()
            yield event

    async def _read_loop(self) -> None:
        """Background loop reading newline-delimited JSON-RPC messages."""
        if self._reader is None:
            return

        while not self._closed:
            try:
                line = await self._reader.readline()
                if not line:
                    logger.debug("Bridge closed socket connection")
                    break

                if len(line) > MAX_MESSAGE_SIZE:
                    logger.error("Received message exceeding maximum allowed size")
                    break

                text = line.decode("utf-8").strip()
                if not text:
                    continue

                msg = json.loads(text)
                if "id" in msg and msg["id"] is not None:
                    # Response to a pending request
                    req_id = msg["id"]
                    future = self._pending_requests.pop(req_id, None)
                    if future and not future.done():
                        if "error" in msg and msg["error"]:
                            err = msg["error"]
                            code = err.get("code", 1000)
                            message = err.get("message", "Unknown bridge error")
                            if code == 1002:
                                future.set_exception(BridgeAuthError(message))
                            elif code == 1003:
                                future.set_exception(ProtocolVersionMismatchError(message))
                            else:
                                future.set_exception(SynfigError(f"Bridge error {code}: {message}"))
                        else:
                            future.set_result(msg.get("result"))
                elif "method" in msg:
                    # Notification event
                    notification = JsonRpcNotification.model_validate(msg)
                    await self._event_queue.put(notification)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in bridge read loop", error=str(e))
                break

        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up pending requests and transport on disconnect."""
        self._closed = True
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.set_exception(BridgeConnectionError("Connection lost to bridge"))
        self._pending_requests.clear()

    async def close(self) -> None:
        """Gracefully close client."""
        self._closed = True
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.debug("Error closing writer", error=str(e))
            self._writer = None
            self._reader = None
        await self._cleanup()
