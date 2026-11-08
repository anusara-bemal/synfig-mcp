"""
Streamable HTTP transport for synfig-mcp using the official MCP Python SDK
streamable_http transport, mounted with constant-time bearer token authentication
and Host allow-list verification.
"""

from __future__ import annotations

import os
import secrets

from mcp.server.mcpserver import MCPServer
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from synfig_mcp.errors import SecurityError

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class SecurityMiddleware:
    """
    ASGI middleware enforcing:
    1. Host header allow-list (defaulting to 127.0.0.1, localhost)
    2. Constant-time Bearer token authentication (via Authorization: Bearer <token>)
    3. Stripping any sensitive error details from error responses
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: list[str] | None = None,
        token: str | None = None,
    ) -> None:
        self.app = app
        raw_hosts = allowed_hosts or ["127.0.0.1", "localhost"]
        self.allowed_hosts = [h.lower() for h in raw_hosts]
        self.token = token or os.environ.get("SYNFIG_MCP_HTTP_TOKEN")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))

        # 1. Host allow-list check
        host_header = headers.get(b"host", b"").decode("latin-1").split(":")[0].strip().lower()
        if self.allowed_hosts and host_header not in self.allowed_hosts:
            # Clean, non-sensitive error body
            resp = PlainTextResponse("Forbidden", status_code=403)
            await resp(scope, receive, send)
            return

        # 2. Bearer token auth check (constant-time comparison)
        if self.token:
            auth_header = headers.get(b"authorization", b"").decode("latin-1").strip()
            expected = f"Bearer {self.token}"
            if not secrets.compare_digest(auth_header, expected):
                # Clean, non-sensitive error body
                resp = PlainTextResponse(
                    "Unauthorized",
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await resp(scope, receive, send)
                return

        await self.app(scope, receive, send)


def create_http_app(
    mcp_server: MCPServer,
    host: str = "127.0.0.1",
    token: str | None = None,
    allowed_hosts: list[str] | None = None,
    streamable_http_path: str = "/mcp",
) -> ASGIApp:
    """
    Create a secured Starlette ASGI app using official SDK Streamable HTTP transport.

    Why official SDK Streamable HTTP:
    Using mcp_server.streamable_http_app guarantees full MCP protocol compatibility
    (session lifecycle, SSE events, and JSON-RPC compliance) while our outer ASGI
    SecurityMiddleware handles constant-time auth and host perimeter defense.
    """
    inner_app = mcp_server.streamable_http_app(
        host=host,
        streamable_http_path=streamable_http_path,
    )
    effective_hosts = allowed_hosts or [host, "localhost", "127.0.0.1"]
    return SecurityMiddleware(
        app=inner_app,
        allowed_hosts=effective_hosts,
        token=token,
    )


def validate_network_bind(host: str, token: str | None, allow_remote: bool) -> None:
    """Validate loopback binding and security requirements for remote listening."""
    is_loopback = host.strip().lower() in LOOPBACK_HOSTS
    if not is_loopback:
        if not allow_remote:
            raise SecurityError(
                f"Refusing to bind on non-loopback host '{host}' without explicit allow_remote=True (--allow-remote)."
            )
        if not token:
            raise SecurityError(
                f"Refusing to bind on non-loopback host '{host}' without a secure authentication token."
            )


def run_http_server(
    mcp_server: MCPServer,
    host: str = "127.0.0.1",
    port: int = 8000,
    token: str | None = None,
    allow_remote: bool = False,
    allowed_hosts: list[str] | None = None,
) -> None:
    """Run uvicorn server with streamable HTTP transport after security validation."""
    validate_network_bind(host=host, token=token, allow_remote=allow_remote)

    import uvicorn

    app = create_http_app(
        mcp_server=mcp_server,
        host=host,
        token=token,
        allowed_hosts=allowed_hosts,
    )
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    import anyio

    anyio.run(server.serve)
