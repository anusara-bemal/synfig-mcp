# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""System tools: doctor, version, render targets, layer types."""

from __future__ import annotations

from pathlib import Path

from ..cli.binary import default_candidates, find_synfig_binary, find_synfig_studio_binary
from .common import AppContext, json_dumps, tool


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def synfig_doctor() -> str:
        """Diagnose the synfig installation.

        Returns JSON with the detected binary path, version, available render
        targets/renderers/layers, workspace settings and problems.
        """
        probed = await ctx.probe()
        payload = dict(probed)
        studio_bin = find_synfig_studio_binary()
        home = Path.home()
        plugin_cand = [
            home / "synfig" / "plugins" / "synfig_mcp_sync" / "plugin.xml",
            home / ".synfig" / "plugins" / "synfig_mcp_sync" / "plugin.xml",
        ]
        plugin_installed = any(p.is_file() for p in plugin_cand)
        plugin_file = next((str(p) for p in plugin_cand if p.is_file()), None)

        payload.update(
            {
                "workspace": str(ctx.settings.workspace),
                "workspace_writable": ctx.settings.workspace.is_dir(),
                "synfig_bin_env": ctx.settings.synfig_bin,
                "path_candidates": [c for c in default_candidates()],
                "resolved_via": _resolution_origin(ctx.settings.synfig_bin),
                "studio_binary": studio_bin,
                "studio_reachable": studio_bin is not None,
                "plugin_installed": plugin_installed,
                "plugin_reachable": plugin_installed,
                "plugin_path": plugin_file,
                "config": {
                    "render_timeout": ctx.settings.render_timeout,
                    "max_frames": ctx.settings.max_frames,
                    "max_resolution": ctx.settings.max_resolution,
                    "max_layers": ctx.settings.max_layers,
                    "max_file_mb": ctx.settings.max_file_mb,
                    "unit_px": ctx.settings.unit_px,
                    "unit_system": ctx.settings.unit_system,
                    "history_depth": ctx.settings.history_depth,
                    "render_workers": ctx.settings.render_workers,
                    "autosave": ctx.settings.autosave,
                },
            }
        )
        problems = list(payload.get("problems", []))
        if not ctx.settings.workspace.is_dir():
            problems.append(
                f"workspace {ctx.settings.workspace} does not exist; create it or set SYNFIG_MCP_WORKSPACE"
            )
        elif not os_access_writable(ctx.settings.workspace):
            problems.append(f"workspace {ctx.settings.workspace} is not writable")
        payload["problems"] = problems
        payload["healthy"] = not problems and payload.get("found", False)
        return json_dumps(payload)

    @tool(server)
    async def synfig_version() -> str:
        """Print the synfig version (requires the binary)."""
        binary = ctx.require_binary()
        probed = await ctx.probe()
        return json_dumps({"binary": binary, "version": probed.get("version")})

    @tool(server)
    async def list_render_targets() -> str:
        """List render targets supported by this synfig build."""
        probed = await ctx.probe()
        return json_dumps(
            {
                "targets": probed.get("targets", []),
                "renderers": probed.get("renderers", []),
                "problems": probed.get("problems", []),
            }
        )

    @tool(server)
    async def list_layer_types() -> str:
        """List layer types supported by this synfig build."""
        layer_types = await ctx.known_layer_types()
        return json_dumps({"count": len(layer_types), "layer_types": layer_types})

    @tool(server)
    async def install_synfig_plugin() -> str:
        """Install the Synfig MCP Sync plugin into Synfig Studio's user plugins folder.

        Adds a 'Synfig MCP: Reload Canvas' menu item under Synfig Studio's Plugins menu
        so you can instantly refresh the open window whenever the AI modifies files.
        """
        home = Path.home()
        candidates = [
            home / "synfig" / "plugins" / "synfig_mcp_sync",
            home / ".synfig" / "plugins" / "synfig_mcp_sync",
        ]
        target_dir = candidates[0] if (home / "synfig").exists() else candidates[1]
        target_dir.mkdir(parents=True, exist_ok=True)

        plugin_xml = """<?xml version="1.0" encoding="UTF-8"?>
<plugin>
   <name>Synfig MCP: Reload Canvas</name>
   <desc>Instantly reload current canvas modified by synfig-mcp</desc>
   <exec>reload.py</exec>
</plugin>
"""
        reload_py = """#!/usr/bin/env python
import sys

# Synfig Studio plugin runner: passing cleanly triggers canvas reload
if __name__ == "__main__":
    sys.exit(0)
"""
        (target_dir / "plugin.xml").write_text(plugin_xml, encoding="utf-8")
        (target_dir / "reload.py").write_text(reload_py, encoding="utf-8")

        return json_dumps(
            {
                "installed": True,
                "plugin_path": str(target_dir),
                "name": "Synfig MCP: Reload Canvas",
                "message": (
                    "Plugin installed! In Synfig Studio, restart the app or check "
                    "Plugins -> Synfig MCP: Reload Canvas to refresh open files instantly."
                ),
            }
        )


def _resolution_origin(env_bin: str | None) -> str:
    if env_bin:
        return "SYNFIG_BIN environment variable"
    detected = find_synfig_binary(None)
    return f"auto-detected: {detected}" if detected else "not found"


def os_access_writable(path) -> bool:  # type: ignore[no-untyped-def]
    import os

    return os.access(path, os.W_OK)
