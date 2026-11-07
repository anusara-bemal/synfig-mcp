"""
MCP Server entrypoint for synfig-mcp.
Configures logging to stderr to maintain clean stdio transport, registers all typed tools,
and executes the MCP protocol loop.
"""

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


def main() -> None:
    """Run the MCP server over clean stdio transport."""
    logger.info("Starting synfig-mcp server over stdio transport")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
