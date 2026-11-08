"""
Generate comprehensive Markdown documentation for all 47 Synfig MCP tools.
"""

import asyncio
from pathlib import Path
from typing import Any

from mcp.client import Client

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server


def categorize_tool(name: str) -> str:
    if name.startswith("doc_"):
        return "Document Management"
    if name.startswith("canvas_") or name.startswith("scene_"):
        return "Canvas & Hierarchy"
    if name.startswith("layer_"):
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
    if name.startswith("schema_"):
        return "Schema & Introspection"
    return "Core & Diagnostic"


async def generate_docs() -> str:
    backend = HeadlessBackend()
    app = create_server(backend=backend)
    async with Client(app) as client:
        tools = (await client.list_tools()).tools

    categorized: dict[str, list[Any]] = {}
    for t in tools:
        cat = categorize_tool(t.name)
        categorized.setdefault(cat, []).append(t)

    lines: list[str] = [
        "# Synfig MCP Tool Reference",
        "",
        "> Complete typed reference for all 47 Model Context Protocol (MCP) tools provided by the `synfig-mcp` server.",
        "> Each tool includes typed input schemas, execution semantics, and LLM-targeted guidance.",
        "",
        "## Table of Contents",
        "",
    ]

    for cat in sorted(categorized.keys()):
        anchor = cat.lower().replace(" ", "-").replace("&", "").replace("--", "-")
        lines.append(f"- [{cat}](#{anchor}) ({len(categorized[cat])} tools)")

    lines.append("")

    for cat in sorted(categorized.keys()):
        lines.append(f"## {cat}")
        lines.append("")
        for t in categorized[cat]:
            lines.append(f"### `{t.name}`")
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
    out_path = Path("docs/tools.md")
    content = asyncio.run(generate_docs())
    out_path.write_text(content, encoding="utf-8")
    print(f"Generated tool documentation at {out_path} ({len(content.splitlines())} lines)")
