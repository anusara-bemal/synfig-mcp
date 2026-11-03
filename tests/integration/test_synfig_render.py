# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Integration tests against a real Synfig installation.

Run with::

    SYNFIG_BIN=/path/to/synfig pytest -m synfig

They are skipped automatically when no binary is available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.conftest import ToolBox

from synfig_mcp.cli.binary import find_synfig_binary
from synfig_mcp.config import Settings
from synfig_mcp.document import io
from synfig_mcp.server import create_server

pytestmark = pytest.mark.synfig


def _binary() -> str:
    binary = find_synfig_binary(os.environ.get("SYNFIG_BIN"))
    if not binary or not Path(binary).is_file():
        pytest.skip("synfig binary not available (set SYNFIG_BIN or install Synfig)")
    return binary


def payload(raw):  # type: ignore[no-untyped-def]
    if isinstance(raw, list):
        return json.loads(raw[0].text)
    return json.loads(raw)


@pytest.fixture
def real_tools(tmp_path: Path) -> ToolBox:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = Settings(
        workspace=workspace,
        synfig_bin=_binary(),
        render_timeout=180.0,
        render_workers=1,
    )
    return ToolBox(create_server(settings))


class TestRealSynfig:
    async def test_doctor(self, real_tools: ToolBox) -> None:
        report = payload(await real_tools.synfig_doctor())
        assert report["found"] is True
        assert report["version"]
        assert "png" in report["targets"]

    async def test_create_validate_render(self, real_tools: ToolBox) -> None:
        created = payload(
            await real_tools.create_project(name="integration", width=64, height=64, end_time="12f")
        )
        project = created["project_id"]
        await real_tools.add_circle(project_id=project, center=[0, 0], radius=0.8, color="#ff5522")
        assert payload(await real_tools.validate_project(project_id=project))["valid"] is True

        rendered = payload(
            await real_tools.render_frame(
                project_id=project, time="0f", output="frame.png", return_image=False
            )
        )
        png = Path(rendered["output"])
        assert png.is_file()
        assert png.stat().st_size > 100
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    async def test_animation_gif(self, real_tools: ToolBox) -> None:
        created = payload(
            await real_tools.create_project(name="anim", width=64, height=64, end_time="12f")
        )
        project = created["project_id"]
        await real_tools.add_circle(project_id=project, name="ball", radius=0.5)
        await real_tools.animate_param(
            project_id=project,
            layer=0,
            param="origin",
            waypoints=[{"time": "0f", "value": [0, 0]}, {"time": "12f", "value": [1, 0]}],
            interpolation="linear",
        )
        result = payload(
            await real_tools.render_animation(project_id=project, target="gif", output="anim.gif")
        )
        gif = Path(result["output"])
        assert gif.is_file()
        assert gif.stat().st_size > 0

    async def test_save_open_roundtrip(self, real_tools: ToolBox) -> None:
        created = payload(await real_tools.create_project(name="roundtrip", width=32, height=32))
        project = created["project_id"]
        await real_tools.add_circle(project_id=project, name="dot", radius=0.25)
        saved = payload(await real_tools.save_project(project_id=project, backup=False))
        first = io.read_project(Path(saved["saved"])).getroot()
        assert first.find("layer/param[@name='radius']") is not None
