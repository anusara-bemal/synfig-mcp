"""
Generate the Markdown tool reference for every Synfig MCP tool.

The reference is generated from the *live* tool registry, so it can never drift
away from the tools the server actually exposes.  ``server/tests/unit/
test_tool_docs.py`` fails when the generated file is out of date.
"""

import asyncio
from pathlib import Path
from typing import Any

from mcp.client import Client

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server
from synfig_mcp.tools.register import TOOL_PROFILES


def categorize_tool(name: str) -> str:
    """Map a tool name to its documentation section."""
    if name.startswith("doc_"):
        return "Document Management"
    if name.startswith("canvas_") or name.startswith("scene_"):
        return "Canvas & Scene"
    if name.startswith("layer_") or name == "import_asset":
        return "Layer Manipulation"
    if name.startswith("param_"):
        return "Parameters & ValueNodes"
    if name.startswith("anim_"):
        return "Animation & Keyframes"
    if name.startswith("selection_"):
        return "Selection"
    if name.startswith("history_"):
        return "History & Undo"
    if name.startswith("render_"):
        return "Render & Preview"
    if name.startswith("review_"):
        return "Visual Review"
    if name.startswith("recipe_"):
        return "Effect Recipes"
    if name.startswith("style_"):
        return "Style Presets"
    if name.startswith("character_"):
        return "Character Rigging"
    if name.startswith("storyboard_"):
        return "Storyboards"
    if name.startswith("production_"):
        return "Production Orchestration"
    if name.startswith("asset_"):
        return "Licensed Assets"
    if name.startswith("schema_"):
        return "Schema & Introspection"
    if name in ("health_check", "synfig_help"):
        return "Core & Diagnostics"
    return "Other"


def tool_profiles(name: str) -> str:
    """Return the profiles that expose a tool."""
    profiles = TOOL_PROFILES.get(name, {"all"})
    return ", ".join(sorted(profiles))


async def generate_docs() -> str:
    backend = HeadlessBackend()
    app = create_server(backend=backend, profile="all")
    async with Client(app) as client:
        tools = (await client.list_tools()).tools

    categorized: dict[str, list[Any]] = {}
    for t in tools:
        cat = categorize_tool(t.name)
        categorized.setdefault(cat, []).append(t)

    total = len(tools)

    lines: list[str] = [
        "# Synfig MCP Tool Reference",
        "",
        f"> Complete typed reference for all {total} Model Context Protocol (MCP) tools "
        "provided by the `synfig-mcp` server.",
        "> Each tool includes typed input schemas, execution semantics, and LLM-targeted guidance.",
        "",
        "> Generated from the live tool registry by `scripts/generate_tool_docs.py`.",
        "",
        "## Table of Contents",
        "",
    ]

    for cat in sorted(categorized.keys()):
        anchor = cat.lower().replace(" ", "-").replace("&", "").replace("--", "-")
        lines.append(f"- [{cat}](#{anchor}) ({len(categorized[cat])} tools)")

    lines.append("")
    lines.append(f"**Total: {total} tools.**")
    lines.append("")

    for cat in sorted(categorized.keys()):
        lines.append(f"## {cat}")
        lines.append("")
        for t in categorized[cat]:
            lines.append(f"### `{t.name}`")
            lines.append("")
            lines.append(f"*Profiles: {tool_profiles(t.name)}*")
            lines.append("")
            # Clean description
            desc_lines = [l.strip() for l in t.description.strip().splitlines() if l.strip()]
            desc = "\n\n".join(desc_lines)
            lines.append(desc)
            lines.append("")

            # Parameters table
            schema = t.input_schema or {}
            props: dict[str, Any] = schema.get("properties", {})
            required_props: list[str] = schema.get("required", [])

            lines.append("#### Parameters")
            lines.append("")
            if not props:
                lines.append("*No parameters required.*")
            else:
                lines.append("| Name | Type | Required | Description |")
                lines.append("| :--- | :--- | :---: | :--- |")
                for prop_name, prop_info in props.items():
                    p_type = prop_info.get("type", "any")
                    p_req = "Yes" if prop_name in required_props else "No"
                    p_desc = prop_info.get("description", "-").replace("\n", " ")
                    lines.append(f"| `{prop_name}` | `{p_type}` | {p_req} | {p_desc} |")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "docs" / "tools.md"
    content = asyncio.run(generate_docs())
    out_path.write_text(content, encoding="utf-8")
    print(f"Generated tool documentation at {out_path} ({len(content.splitlines())} lines)")
