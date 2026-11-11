"""
Guards that the published tool reference stays in sync with the server.

The docs are generated from the live tool registry; if a tool is added, renamed
or removed without regenerating ``docs/tools.md`` this test fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_TOOLS = REPO_ROOT / "docs" / "tools.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from synfig_mcp.tools.register import TOOL_PROFILES  # noqa: E402


async def _registered_tool_names() -> set[str]:
    from mcp.client import Client

    from synfig_mcp.backend.headless import HeadlessBackend
    from synfig_mcp.server import create_server

    app = create_server(backend=HeadlessBackend(), profile="all")
    async with Client(app) as client:
        tools = (await client.list_tools()).tools
    return {t.name for t in tools}


@pytest.mark.asyncio
async def test_tool_docs_are_up_to_date() -> None:
    """docs/tools.md must document exactly the registered tools."""
    assert DOCS_TOOLS.is_file(), "docs/tools.md is missing"
    content = DOCS_TOOLS.read_text(encoding="utf-8")

    documented = set(re.findall(r"^### `([a-z0-9_]+)`$", content, re.MULTILINE))
    registered = await _registered_tool_names()

    assert registered, "no tools are registered"
    missing = registered - documented
    extra = documented - registered
    assert not missing, f"Tools missing from docs/tools.md: {sorted(missing)}"
    assert not extra, f"Documented tools that no longer exist: {sorted(extra)}"


@pytest.mark.asyncio
async def test_tool_docs_state_the_correct_total() -> None:
    """The header of docs/tools.md must state the real number of tools."""
    content = DOCS_TOOLS.read_text(encoding="utf-8")
    registered = await _registered_tool_names()
    assert f"all {len(registered)} Model Context Protocol" in content


@pytest.mark.asyncio
async def test_every_registered_tool_has_a_profile() -> None:
    """Every tool must be assigned to at least one profile."""
    registered = await _registered_tool_names()
    missing = [name for name in registered if name not in TOOL_PROFILES]
    assert not missing, f"Tools without a profile entry: {missing}"


def test_tool_profiles_reference_known_profiles() -> None:
    """Profile names used by the tool map must be valid."""
    valid = {"core", "anim", "fx", "rig", "assets", "review", "all"}
    for name, profiles in TOOL_PROFILES.items():
        unknown = profiles - valid
        assert not unknown, f"Tool '{name}' references unknown profiles: {sorted(unknown)}"
