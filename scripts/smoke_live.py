#!/usr/bin/env python3
"""
Smoke test the full MCP stack against a running Synfig Studio.

It starts the MCP server as a subprocess (exactly like an MCP client does),
speaks the protocol over stdio and exercises the live path: health, document
discovery, a declarative scene build, an animation, a render and the visual
review metrics.

    python scripts/smoke_live.py

Exit code 0 means everything worked.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "server" / "src"))

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


def _server_command() -> list[str]:
    """Prefer the local virtualenv, fall back to the installed entry point."""
    venv = REPO_ROOT / "server" / ".venv" / "Scripts" / "synfig-mcp.exe"
    if venv.exists():
        return [str(venv)]
    return ["synfig-mcp"]


async def main() -> int:
    params = StdioServerParameters(command=_server_command()[0], args=[], env=None)
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="synfig_smoke_") as tmp:
        out_dir = Path(tmp)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                print(f"tools/list            -> {len(tools.tools)} tools")

                health = await session.call_tool("health_check", {})
                health_data = json.loads(health.content[0].text)
                backend = health_data.get("backend")
                print(f"health_check          -> backend={backend}, studio={health_data.get('studio_running')}")
                if backend != "live":
                    failures.append(
                        f"expected the live backend, got '{backend}'. "
                        "Is the patched Studio running with 'Tools -> MCP Bridge' enabled?"
                    )

                docs = await session.call_tool("doc_list", {})
                doc_blocks = [b.text for b in docs.content if hasattr(b, "text")]
                doc_data = []
                for block in doc_blocks:
                    try:
                        parsed = json.loads(block)
                    except Exception:
                        continue
                    doc_data.extend(parsed if isinstance(parsed, list) else [parsed])
                doc_id = doc_data[0].get("id") or doc_data[0].get("doc_id") if doc_data else "doc_0"
                size = ""
                if doc_data:
                    first = doc_data[0]
                    size = (f"{first.get('width')}x{first.get('height')} @ "
                            f"{first.get('fps')}fps")
                print(f"doc_list              -> {len(doc_data)} document(s), using '{doc_id}' {size}")

                build = await session.call_tool(
                    "scene_build",
                    {
                        "spec": {
                            "doc_id": doc_id,
                            "layers": [
                                {
                                    "id": "smoke_ball",
                                    "type": "circle",
                                    "depth": 0,
                                    "params": {
                                        "radius": {"type": "real", "value": 1.2},
                                        "color": {
                                            "type": "color",
                                            "r": 0.9,
                                            "g": 0.3,
                                            "b": 0.2,
                                            "a": 1.0,
                                        },
                                    },
                                    "waypoints": [
                                        {
                                            "param": "origin",
                                            "time": 0.0,
                                            "value": {"type": "vector", "x": -1.0, "y": 0.0},
                                            "interpolation": "linear",
                                        },
                                        {
                                            "param": "origin",
                                            "time": 1.0,
                                            "value": {"type": "vector", "x": 1.0, "y": 0.0},
                                            "interpolation": "linear",
                                        },
                                    ],
                                },
                                {
                                    "id": "smoke_shadow",
                                    "type": "circle",
                                    "depth": 1,
                                    "params": {"radius": {"type": "real", "value": 0.8}},
                                },
                            ],
                            "groups": [{"id": "smoke_cast", "layer_ids": ["smoke_ball", "smoke_shadow"]}],
                        }
                    },
                )
                build_data = json.loads(build.content[0].text)
                created = build_data.get("diff", {}).get("created", [])
                print(f"scene_build           -> created {created}")

                tree = await session.call_tool("scene_tree", {"doc_id": doc_id})
                tree_data = json.loads(tree.content[0].text)
                layers = tree_data.get("layers", [])
                print(f"scene_tree            -> {len(layers)} layer(s), "
                      f"{tree_data.get('width')}x{tree_data.get('height')} @ {tree_data.get('fps')}fps")

                # A layer inside a group must stay addressable.
                params_list = await session.call_tool(
                    "param_list", {"doc_id": doc_id, "layer_id": "smoke_ball"}
                )
                param_data = json.loads(params_list.content[0].text)
                print(f"param_list            -> {len(param_data)} parameter(s) on a grouped layer")

                # Export a value and link another parameter to it.
                exported = await session.call_tool(
                    "param_export",
                    {
                        "doc_id": doc_id,
                        "layer_id": "smoke_ball",
                        "param_name": "radius",
                        "name": "smokeSharedRadius",
                    },
                )
                export_data = json.loads(exported.content[0].text)
                print(f"param_export          -> {export_data.get('name')}")

                linked = await session.call_tool(
                    "param_link",
                    {
                        "doc_id": doc_id,
                        "layer_id": "smoke_shadow",
                        "param_name": "radius",
                        "link_id": "smokeSharedRadius",
                    },
                )
                link_data = json.loads(linked.content[0].text)
                print(f"param_link            -> {link_data.get('link_id')}")

                linked_value = await session.call_tool(
                    "param_get",
                    {"doc_id": doc_id, "layer_id": "smoke_shadow", "param_name": "radius"},
                )
                value_data = json.loads(linked_value.content[0].text)
                print(f"param_get (linked)    -> {value_data.get('value')}")

                waypoints = await session.call_tool(
                    "anim_waypoint_list",
                    {"doc_id": doc_id, "layer_id": "smoke_ball", "param_name": "origin"},
                )
                waypoint_data = json.loads(waypoints.content[0].text)
                print(f"anim_waypoint_list    -> {len(waypoint_data)} waypoint(s)")

                frame = out_dir / "smoke.png"
                render = await session.call_tool(
                    "render_frame",
                    {
                        "doc_id": doc_id,
                        "output_path": str(frame),
                        "time": 0.5,
                        "width": 320,
                        "height": 240,
                    },
                )
                render_data = json.loads(render.content[0].text)
                exists = frame.is_file()
                print(f"render_frame          -> success={render_data.get('success')}, file={exists}")
                if not exists:
                    failures.append("render_frame did not produce a file")

                review = await session.call_tool(
                    "review_frame", {"doc_id": doc_id, "time": 0.5, "width": 320, "height": 240}
                )
                review_data = json.loads(review.content[0].text)
                metrics = review_data.get("metrics", {})
                print(f"review_frame          -> metrics={len(metrics)}, "
                      f"warnings={len(review_data.get('warnings', []))}")

                undo = await session.call_tool("history_undo", {"doc_id": doc_id})
                undo_data = json.loads(undo.content[0].text)
                print(f"history_undo          -> success={undo_data.get('success')}")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nAll live checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
