# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""FastMCP server factory for synfig-mcp."""

from __future__ import annotations

from typing import Literal, cast

from mcp.server.fastmcp import FastMCP

from .cli.render import RenderManager
from .config import Settings, load_settings
from .document.registry import ProjectRegistry
from .logging import configure_logging, get_logger
from .tools import (
    animation_tools,
    asset_tools,
    batch_tools,
    inspect_tools,
    layer_tools,
    project_tools,
    render_tools,
    shape_tools,
    system_tools,
)
from .tools import common as tools_common

logger = get_logger(__name__)

INSTRUCTIONS = """synfig-mcp exposes Synfig Studio (2D vector animation) to MCP clients.

Workflow:
1. synfig_doctor to verify the installation and workspace.
2. create_project or open_project to get a project_id.
3. Build layers with shape/filter tools; animate with animate_param/add_waypoint.
4. save_project often; render_frame to check, render_animation for final output.
5. validate_project before saving or rendering.

Rules:
- All file paths must stay inside SYNFIG_MCP_WORKSPACE.
- Layer paint order == document order: index 0 is painted first (background).
- Render targets depend on the local synfig build; check list_render_targets.
- Undo is in-memory only; it does not write to disk.
"""


def create_server(
    settings: Settings | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    registry = ProjectRegistry(settings)
    render_manager = RenderManager(settings)
    ctx = tools_common.AppContext(
        settings=settings, registry=registry, render_manager=render_manager
    )

    server = FastMCP(
        "synfig-mcp",
        instructions=INSTRUCTIONS,
        log_level=_log_level_literal(settings.log_level),
        host=host,
        port=port,
    )

    system_tools.register(server, ctx)
    project_tools.register(server, ctx)
    layer_tools.register(server, ctx)
    shape_tools.register(server, ctx)
    shape_tools.register_filters(server, ctx)
    animation_tools.register(server, ctx)
    render_tools.register(server, ctx)
    asset_tools.register(server, ctx)
    inspect_tools.register(server, ctx)
    batch_tools.register(server, ctx)

    from .prompts import workflow_prompts
    from .resources import project_resources

    project_resources.register(server, ctx)
    workflow_prompts.register(server, ctx)

    logger.info(
        "synfig-mcp server created workspace=%s synfig_bin=%s",
        settings.workspace,
        settings.synfig_bin or "auto-detect",
    )
    return server


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _log_level_literal(level: str) -> LogLevel:
    normalized = (level or "INFO").upper()
    if normalized in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return cast(LogLevel, normalized)
    return "INFO"
