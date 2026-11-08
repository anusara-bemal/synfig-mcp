"""
MCP Server entrypoint for synfig-mcp.
Configures logging to stderr to maintain clean stdio transport, registers all typed tools,
and executes the MCP protocol loop.
"""

from __future__ import annotations

import argparse
import sys

from mcp.server.mcpserver import MCPServer

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.backend.select import get_backend
from synfig_mcp.logging import configure_logging, get_logger
from synfig_mcp.tools import register_all_tools

configure_logging()
logger = get_logger("synfig_mcp.server")


def create_server(backend: BackendBase | None = None) -> MCPServer:
    """Create and configure the MCPServer instance with all tools registered."""
    active_backend = backend or get_backend()
    mcp_app = MCPServer("synfig-mcp")
    register_all_tools(mcp_app, active_backend)
    return mcp_app


mcp = create_server()


def main(args: list[str] | None = None) -> None:
    """Run the MCP server over stdio or streamable HTTP transport, or run diagnostics."""
    raw_args = args if args is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="synfig-mcp",
        description="Live MCP control of Synfig Studio (native bridge + headless fallback)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # synfig-mcp doctor
    subparsers.add_parser("doctor", help="Run system diagnostics and verify dependencies")

    # server options
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Bearer token for HTTP authentication",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        default=False,
        help="Allow binding to non-loopback network interfaces (requires --token)",
    )
    parser.add_argument(
        "--allowed-hosts",
        nargs="*",
        default=["127.0.0.1", "localhost"],
        help="Allowed Host headers for HTTP transport",
    )

    parsed = parser.parse_args(raw_args)

    if parsed.command == "doctor":
        from synfig_mcp.doctor import run_doctor

        sys.exit(run_doctor())

    if parsed.transport == "streamable-http":
        from synfig_mcp.http_transport import run_http_server

        logger.info(
            "Starting synfig-mcp server over streamable HTTP",
            host=parsed.host,
            port=parsed.port,
            auth_enabled=bool(parsed.token),
        )
        run_http_server(
            mcp_server=mcp,
            host=parsed.host,
            port=parsed.port,
            token=parsed.token,
            allow_remote=parsed.allow_remote,
            allowed_hosts=parsed.allowed_hosts,
        )
    else:
        logger.info("Starting synfig-mcp server over stdio transport")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
