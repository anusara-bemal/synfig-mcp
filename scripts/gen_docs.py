# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Generate docs/tools-reference.md from registered FastMCP tool schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from synfig_mcp.server import create_server


def _format_type(prop: dict[str, Any]) -> str:
    if "type" in prop:
        t = prop["type"]
        if t == "array":
            item_t = prop.get("items", {}).get("type", "any")
            return f"array[{item_t}]"
        return str(t)
    if "anyOf" in prop:
        subtypes = [p.get("type", "object") for p in prop["anyOf"] if p.get("type") != "null"]
        if not subtypes:
            subtypes = ["any"]
        base = " | ".join(subtypes)
        if any(p.get("type") == "null" for p in prop["anyOf"]):
            return f"{base} | null"
        return base
    return "any"


def generate_tools_reference() -> str:
    server = create_server()
    tools = server._tool_manager.list_tools()
    tools_sorted = sorted(tools, key=lambda t: t.name)

    lines: list[str] = [
        "# Synfig MCP Tools Reference",
        "",
        "> Auto-generated reference for all 100+ MCP tools provided by `synfig-mcp`.",
        "",
        "## Table of Contents",
        "",
    ]

    for tool in tools_sorted:
        lines.append(f"- [`{tool.name}`](#{tool.name.replace('_', '-')})")
    lines.append("")
    lines.append("---")
    lines.append("")

    for tool in tools_sorted:
        lines.append(f"## `{tool.name}`")
        lines.append("")
        doc = (tool.description or "No description provided.").strip()
        lines.append(doc)
        lines.append("")

        schema = tool.parameters or {}
        properties: dict[str, Any] = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        lines.append("### Parameters")
        lines.append("")
        if properties:
            lines.append("| Name | Type | Required | Default | Description |")
            lines.append("| --- | --- | --- | --- | --- |")
            for prop_name, prop_data in properties.items():
                ptype = _format_type(prop_data)
                is_req = "Yes" if prop_name in required else "No"
                default_val = prop_data.get("default", "—")
                if default_val is None:
                    default_str = "`null`"
                elif default_val != "—":
                    default_str = f"`{json.dumps(default_val)}`"
                else:
                    default_str = "—"
                pdesc = prop_data.get("description", "").replace("\n", " ").strip() or "—"
                lines.append(f"| `{prop_name}` | `{ptype}` | {is_req} | {default_str} | {pdesc} |")
        else:
            lines.append("_None_")
        lines.append("")

        lines.append("### Return Value")
        lines.append("")
        lines.append("Structured JSON string (or MCP `Image` content for frame renders).")
        lines.append("")

        lines.append("### Example Call")
        lines.append("")
        example_args: dict[str, Any] = {}
        for prop_name, prop_data in properties.items():
            if prop_name in required:
                t = prop_data.get("type")
                if t == "string":
                    example_args[prop_name] = f"sample_{prop_name}"
                elif t == "integer":
                    example_args[prop_name] = 100
                elif t == "number":
                    example_args[prop_name] = 1.0
                elif t == "boolean":
                    example_args[prop_name] = True
                elif t == "array":
                    example_args[prop_name] = []
                else:
                    example_args[prop_name] = "value"
        if not example_args and properties:
            first_k = next(iter(properties.keys()))
            example_args[first_k] = properties[first_k].get("default", "value")

        lines.append("```json")
        lines.append(json.dumps({"tool": tool.name, "arguments": example_args}, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    output_path = Path(__file__).resolve().parent.parent / "docs" / "tools-reference.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_tools_reference()
    output_path.write_text(content, encoding="utf-8")
    print(f"Generated tools reference at {output_path}")


if __name__ == "__main__":
    main()
