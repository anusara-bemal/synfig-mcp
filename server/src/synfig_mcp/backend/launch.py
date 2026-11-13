"""
Launch Synfig Studio with the MCP bridge enabled and wait for readiness.

The direct-GUI workflow needs a real Studio window.  When none is running,
the server can start the patched build itself (bridge opt-in via
``SYNFIG_MCP_ENABLE=1``), then wait until the bridge socket accepts
connections before reporting success.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from synfig_mcp.backend.select import probe_live_bridge
from synfig_mcp.config import settings
from synfig_mcp.errors import SynfigError
from synfig_mcp.logging import get_logger

logger = get_logger("synfig_mcp.backend.launch")

_REPO_ROOT = Path(__file__).resolve().parents[4]


def find_studio_executable() -> Path | None:
    """Locate a Synfig Studio executable, preferring the patched repo build."""
    env_path = os.environ.get("SYNFIG_MCP_STUDIO_PATH")
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(
        [
            _REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe",
            _REPO_ROOT
            / "build_synfig"
            / "build_ucrt64"
            / "output"
            / "Release"
            / "bin"
            / "synfigstudio.exe",
        ]
    )
    if sys.platform == "win32":
        for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates.append(Path(base) / "Synfig" / "bin" / "synfigstudio.exe")
                candidates.append(Path(base) / "Synfig Studio" / "bin" / "synfigstudio.exe")
    else:
        candidates.extend(
            [Path("/usr/bin/synfigstudio"), Path("/usr/local/bin/synfigstudio")]
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    found = shutil.which("synfigstudio")
    if found:
        return Path(found).resolve()
    return None


async def launch_studio(wait_seconds: float = 45.0) -> dict[str, Any]:
    """Start Synfig Studio with the bridge enabled and wait for the socket.

    Returns immediately when a bridge is already reachable.  Raises
    ``SynfigError`` when no executable is found or the bridge does not come
    up in time; it never reports a launch that did not happen.
    """
    if probe_live_bridge(settings.bridge_host, settings.bridge_port):
        return {
            "launched": False,
            "already_running": True,
            "host": settings.bridge_host,
            "port": settings.bridge_port,
        }

    exe = find_studio_executable()
    if exe is None:
        raise SynfigError(
            "No Synfig Studio executable found. Install the patched synfig-mcp "
            "Studio build, or set SYNFIG_MCP_STUDIO_PATH to synfigstudio.exe."
        )

    env = dict(os.environ)
    env["SYNFIG_MCP_ENABLE"] = "1"
    env["SYNFIG_MCP_PORT"] = str(settings.bridge_port)
    env.pop("SYNFIG_MCP_DISABLE", None)
    # The crash-recovery confirmation is a modal dialog shown before
    # mcp_bridge::start(); left unanswered it blocks the bridge forever.
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"

    kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "env": env,
        "cwd": str(exe.parent),
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True

    process = subprocess.Popen([str(exe)], **kwargs)
    logger.info("Launched Synfig Studio", pid=process.pid, executable=str(exe))

    deadline = asyncio.get_event_loop().time() + wait_seconds
    while asyncio.get_event_loop().time() < deadline:
        if process.poll() is not None:
            if process.returncode == 0:
                raise SynfigError(
                    "Synfig Studio is already running: the launched process forwarded to "
                    "the existing instance and exited (Gtk single-instance), and that "
                    f"instance has no MCP bridge on {settings.bridge_host}:{settings.bridge_port}. "
                    "Enable Tools -> MCP Bridge in the open Studio window, or close it and retry."
                )
            raise SynfigError(
                f"Synfig Studio exited immediately (code {process.returncode}). "
                "The build may be missing runtime DLLs; run it manually to see the error."
            )
        if probe_live_bridge(settings.bridge_host, settings.bridge_port, timeout=0.5):
            return {
                "launched": True,
                "already_running": False,
                "pid": process.pid,
                "executable": str(exe),
                "host": settings.bridge_host,
                "port": settings.bridge_port,
                "bridge_ready": True,
            }
        await asyncio.sleep(0.5)

    raise SynfigError(
        f"Synfig Studio started (pid {process.pid}) but its MCP bridge did not "
        f"become reachable on {settings.bridge_host}:{settings.bridge_port} within "
        f"{wait_seconds:.0f}s. Enable Tools -> MCP Bridge in the Studio window."
    )