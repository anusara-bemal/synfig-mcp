"""
Generate the website's tool catalog and counts from the live tool registry.

The marketing site at ``website/`` hard-codes its tool list and its "N tools"
numbers. This script regenerates both from the same registry the server exposes,
so the site can never advertise a tool that does not exist (or miss one that
does). ``server/tests/unit/test_website_catalog.py`` runs it in ``--check`` mode
and fails when the committed files are out of date.
"""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from mcp.client import Client

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server
from synfig_mcp.tools.register import TOOL_PROFILES

PROFILE_ORDER = ["core", "anim", "fx", "rig", "assets", "review"]

CATALOG_START = "const TOOLS_CATALOG = ["
CATALOG_END = "// END GENERATED CATALOG"
STATS_START = "const MCP_STATS = {"
STATS_END = "// END GENERATED STATS"


def _first_sentence(description: str | None) -> str:
    """Condense a tool description to a single website-friendly line."""
    text = (description or "").strip()
    # Descriptions are "Summary. Returns: ... Gotcha: ..." - keep only the summary.
    text = re.split(r"\bReturns:", text, maxsplit=1)[0]
    text = " ".join(text.split())
    if len(text) > 200:
        text = text[:197].rstrip() + "..."
    return text


def _signature(schema: dict | None) -> str:
    """Render a compact ``(name?: type)`` signature from a JSON schema."""
    props = (schema or {}).get("properties", {})
    required = set((schema or {}).get("required", []))
    parts = []
    for name, info in props.items():
        typ = info.get("type", "any")
        if isinstance(typ, list):
            typ = next((t for t in typ if t != "null"), typ[0])
        parts.append(f"{name}{'' if name in required else '?'}: {typ}")
    return "(" + ", ".join(parts) + ")"


async def _collect() -> tuple[list[dict], dict[str, int]]:
    app = create_server(backend=HeadlessBackend(), profile="all")
    async with Client(app) as client:
        tools = (await client.list_tools()).tools

    entries = []
    for tool in sorted(tools, key=lambda t: t.name):
        profiles = sorted(
            TOOL_PROFILES.get(tool.name, {"all"}),
            key=lambda p: PROFILE_ORDER.index(p) if p in PROFILE_ORDER else len(PROFILE_ORDER),
        )
        entries.append(
            {
                "name": tool.name,
                "profiles": profiles,
                "desc": _first_sentence(tool.description),
                "params": _signature(tool.input_schema),
            }
        )

    counts = {"all": len(tools)}
    for profile in PROFILE_ORDER:
        counts[profile] = sum(1 for t in tools if profile in TOOL_PROFILES.get(t.name, {"all"}))
    return entries, counts


def render_catalog(entries: list[dict]) -> str:
    lines = [
        CATALOG_START,
        "  // Generated from the live server registry by scripts/generate_website_catalog.py.",
    ]
    for entry in entries:
        profiles = ", ".join(f'"{p}"' for p in entry["profiles"])
        lines.append(
            f"  {{ name: {_js_string(entry['name'])}, "
            f"profiles: [{profiles}], "
            f"desc: {_js_string(entry['desc'])}, "
            f"params: {_js_string(entry['params'])} }},"
        )
    lines.append("];")
    lines.append(CATALOG_END)
    return "\n".join(lines)


def render_stats(counts: dict[str, int]) -> str:
    profile_pairs = ", ".join(f"{p}: {counts[p]}" for p in PROFILE_ORDER)
    return "\n".join(
        [
            STATS_START,
            f"  total: {counts['all']},",
            f"  profiles: {{ {profile_pairs} }},",
            "};",
            STATS_END,
        ]
    )


def _js_string(value: str) -> str:
    import json

    return json.dumps(value)


def _replace_block(text: str, start: str, end: str, block: str) -> str:
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"markers not found for {start!r} .. {end!r}")
    return pattern.sub(lambda _m: block, text, count=1)


def _replace_patterns(text: str, replacements: dict[str, str]) -> str:
    """Substitute count placeholders regardless of the value they currently hold.

    The site carries the tool count in prose ("Tools (89)"), in a hero stat, and
    in profile-filter buttons. Matching the *shape* rather than a fixed literal
    (e.g. "81") keeps the generator correct as the count changes; a literal
    match silently no-ops once the committed number drifts.
    """
    for pattern, new in replacements.items():
        text = re.sub(pattern, new, text)
    return text


def build(repo_root: Path) -> dict[Path, str]:
    entries, counts = asyncio.run(_collect())
    total = counts["all"]

    script_path = repo_root / "website" / "script.js"
    script = script_path.read_text(encoding="utf-8")
    script = _replace_block(script, CATALOG_START, CATALOG_END, render_catalog(entries))
    script = _replace_block(script, STATS_START, STATS_END, render_stats(counts))

    html_path = repo_root / "website" / "index.html"
    html = html_path.read_text(encoding="utf-8")
    html = _replace_patterns(
        html,
        {
            r"Tools \(\d+\)": f"Tools ({total})",
            r"Tools API \(\d+\)": f"Tools API ({total})",
            r"\d+ typed tools": f"{total} typed tools",
            r">\d+ Typed MCP Tools<": f">{total} Typed MCP Tools<",
            r">\d+ Tools<": f">{total} Tools<",
            r'<span class="stat-number">\d+</span>(\s*<span class="stat-label">MCP Tools</span>)': (
                f'<span class="stat-number">{total}</span>' + r"\1"
            ),
            r"All \(\d+\)": f"All ({total})",
            r"core \(\d+\)": f"core ({counts['core']})",
            r"anim \(\d+\)": f"anim ({counts['anim']})",
            r"fx \(\d+\)": f"fx ({counts['fx']})",
            r"rig \(\d+\)": f"rig ({counts['rig']})",
            r"assets \(\d+\)": f"assets ({counts['assets']})",
            r"review \(\d+\)": f"review ({counts['review']})",
        },
    )

    return {script_path: script, html_path: html}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed files differ from generated output",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    generated = build(repo_root)

    stale = []
    for path, content in generated.items():
        current = path.read_text(encoding="utf-8")
        if current != content:
            stale.append(path)
            if not args.check:
                path.write_text(content, encoding="utf-8")

    if args.check:
        if stale:
            names = ", ".join(str(p.relative_to(repo_root)) for p in stale)
            raise SystemExit(
                f"Website is out of date: {names}. "
                "Run: uv run python scripts/generate_website_catalog.py"
            )
        print("Website catalog and counts are up to date.")
        return

    if stale:
        for path in stale:
            print(f"Updated {path.relative_to(repo_root)}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
