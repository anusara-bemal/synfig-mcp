"""
Backend selection and auto-detection logic.
"""

import socket

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.config import settings
from synfig_mcp.logging import get_logger

logger = get_logger("synfig_mcp.backend.select")


def probe_live_bridge(host: str, port: int, timeout: float = 0.5) -> bool:
    """Quickly check if the live bridge TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def get_backend(mode: str | None = None) -> BackendBase:
    """
    Select active backend based on mode and availability.
    - 'live': forces LiveBackend
    - 'headless': forces HeadlessBackend
    - 'auto': probes the live bridge; uses headless only when no Studio process is running

    In auto mode an open Studio window is never silently replaced by an
    invisible headless document. If Studio is detected but its bridge is
    unreachable, the live backend is kept so operations fail with guidance
    instead of reporting success on a document the user cannot see.

    In auto mode the returned backend re-evaluates the choice on every call,
    so a Studio that starts (or closes) after the MCP server is picked up
    without a restart.
    """
    target_mode = mode or settings.backend_mode

    if target_mode == "live":
        logger.info("Using forced LiveBackend")
        return LiveBackend()

    if target_mode == "headless":
        logger.info("Using forced HeadlessBackend")
        return HeadlessBackend()

    from synfig_mcp.backend.auto import AutoBackend

    logger.info(
        "Using auto backend (live bridge is used as soon as it is reachable)",
        host=settings.bridge_host,
        port=settings.bridge_port,
    )
    return AutoBackend()
