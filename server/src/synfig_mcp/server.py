"""
MCP Server entrypoint for synfig-mcp.
"""

from typing import Any

from mcp.server import MCPServer

from synfig_mcp.backend.select import get_backend
from synfig_mcp.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("synfig_mcp.server")

mcp = MCPServer("synfig-mcp")
backend = get_backend()


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """
    Check server status, active backend (Live vs Headless), and bridge connection.
    Use this to determine whether Synfig Studio is currently connected.
    """
    status = await backend.health_check()
    return status.model_dump()


def main() -> None:
    """Run the MCP server over stdio."""
    logger.info("Starting synfig-mcp server", backend=backend.name)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
