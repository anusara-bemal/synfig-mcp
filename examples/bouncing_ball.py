# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Example: Build a complete bouncing ball animation using synfig-mcp."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from synfig_mcp.config import Settings
from synfig_mcp.server import create_server


async def main() -> None:
    workspace = Path("./workspace_example").resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    settings = Settings(workspace=workspace)
    server = create_server(settings)

    tools = {t.name: t.fn for t in server._tool_manager.list_tools()}

    print("[1] Creating new 24fps project: 'Bouncing Ball'...")
    proj_res = json.loads(
        await tools["create_project"](
            name="bouncing_ball",
            width=640,
            height=480,
            fps=24.0,
            begin_time="0f",
            end_time="2s 0f",
            path="bouncing_ball.sif",
            save=True,
        )
    )
    project_id = proj_res["project_id"]
    print(f"    Project ID: {project_id}")

    print("[2] Adding background solid color layer...")
    await tools["add_solid_color"](
        project_id=project_id,
        color="#1a1a2e",
        name="NightSkyBackground",
    )

    print("[3] Adding ground rectangle...")
    await tools["add_rectangle"](
        project_id=project_id,
        point1=[-5.5, -2.5],
        point2=[5.5, -4.0],
        color="#16213e",
        name="Ground",
    )

    print("[4] Adding bouncing ball circle layer...")
    ball_res = json.loads(
        await tools["add_circle"](
            project_id=project_id,
            center=[0.0, 2.0],
            radius=0.75,
            color="#e94560",
            name="Ball",
        )
    )
    ball_index = ball_res["index"]
    print(f"    Ball Layer Index: {ball_index}")

    print("[5] Animating ball bounce using waypoints...")
    waypoints = [
        {"time": "0f", "value": [0.0, 2.0], "interpolation": "clamped"},
        {"time": "12f", "value": [0.0, -1.75], "interpolation": "linear"},
        {"time": "24f", "value": [0.0, 1.5], "interpolation": "clamped"},
        {"time": "36f", "value": [0.0, -1.75], "interpolation": "linear"},
        {"time": "48f", "value": [0.0, 2.0], "interpolation": "clamped"},
    ]
    await tools["animate_param"](
        project_id=project_id,
        layer=ball_index,
        param="origin",
        waypoints=waypoints,
    )

    print("[6] Saving animation file...")
    save_res = json.loads(
        await tools["save_project"](
            project_id=project_id,
            path="bouncing_ball.sif",
        )
    )
    print(f"    Saved to: {save_res.get('saved') or save_res.get('path')}")
    print("Animation successfully generated!")


if __name__ == "__main__":
    asyncio.run(main())
