# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Shared pytest fixtures for the synfig-mcp test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from synfig_mcp.config import Settings
from synfig_mcp.server import create_server


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at an isolated workspace and a deliberately absent binary.

    Tools that need a real synfig binary are exercised by the integration
    suite (marked ``synfig``); unit tests must stay hermetic.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return Settings(
        workspace=workspace,
        synfig_bin=str(tmp_path / "missing-synfig"),
        history_depth=20,
        render_workers=2,
    )


@pytest.fixture
def server(settings: Settings):  # type: ignore[no-untyped-def]
    return create_server(settings)


class ToolBox:
    """Call registered MCP tools directly, without a client transport."""

    def __init__(self, server) -> None:  # type: ignore[no-untyped-def]
        self._server = server

    def get(self, name: str):  # type: ignore[no-untyped-def]
        tool = self._server._tool_manager.get_tool(name)
        assert tool is not None, f"tool {name!r} is not registered"
        return tool.fn

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return self.get(name)


@pytest.fixture
def tools(server) -> ToolBox:  # type: ignore[no-untyped-def]
    return ToolBox(server)


@pytest.fixture
def context(server) -> Any:  # type: ignore[no-untyped-def]
    """The AppContext captured by the tool closures (for direct inspection)."""
    from synfig_mcp.tools.common import AppContext

    seen: set[int] = set()

    def search(obj: Any) -> AppContext | None:
        if isinstance(obj, AppContext):
            return obj
        if id(obj) in seen or not callable(obj):
            return None
        seen.add(id(obj))
        for cell in getattr(obj, "__closure__", None) or ():
            try:
                found = search(cell.cell_contents)
            except ValueError:  # empty cell
                continue
            if found is not None:
                return found
        return None

    found = search(server._tool_manager.get_tool("create_project").fn)
    if found is None:
        raise AssertionError("AppContext not found in tool closure")
    return found


def parse(payload: Any) -> Any:
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


@pytest.fixture
async def project(tools: ToolBox) -> str:  # type: ignore[no-untyped-def]
    raw = await tools.create_project(
        name="demo",
        width=256,
        height=256,
        fps=24.0,
        begin_time="0f",
        end_time="2s 0f",
        path="demo.sif",
    )
    return parse(raw)["project_id"]
