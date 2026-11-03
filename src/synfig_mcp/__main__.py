# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Console entry point: ``synfig-mcp`` / ``python -m synfig_mcp``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import load_settings
from .logging import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="synfig-mcp", description="Synfig Studio MCP server")
    parser.add_argument("--version", action="version", version=f"synfig-mcp {__version__}")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport (default: stdio). 'http' maps to streamable-http.",
    )
    parser.add_argument(
        "--host", default=None, help="Bind host for HTTP transport (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Bind port for HTTP transport (default: 8000)"
    )
    parser.add_argument(
        "--workspace", default=None, help="Workspace directory (overrides SYNFIG_MCP_WORKSPACE)"
    )
    parser.add_argument(
        "--log-level", default=None, help="DEBUG, INFO, WARNING, ERROR (default: INFO)"
    )
    args = parser.parse_args(argv)

    env_overrides: dict[str, str] = {}
    if args.workspace:
        env_overrides["SYNFIG_MCP_WORKSPACE"] = args.workspace
    if args.log_level:
        env_overrides["SYNFIG_MCP_LOG_LEVEL"] = args.log_level

    import os

    environ = dict(os.environ)
    environ.update(env_overrides)
    settings = load_settings(environ)
    configure_logging(settings.log_level)

    from .server import create_server

    server = create_server(settings, host=args.host or "127.0.0.1", port=args.port or 8000)

    transport = args.transport
    if transport == "http":
        transport = "streamable-http"
    server.run(transport=transport)
    return 0


if __name__ == "__main__":
    sys.exit(main())
