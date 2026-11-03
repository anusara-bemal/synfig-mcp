# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for shape, content and filter tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.conftest import ToolBox


def payload(raw: str) -> dict:
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


class TestPrimitives:
    async def test_circle(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_circle(
                project_id=project,
                center=[0.2, 0.3],
                radius=0.4,
                color="#ff8800",
                feather=0.01,
                name="ball",
            )
        )
        assert result["layer"]["type"] == "circle"
        assert result["layer"]["name"] == "ball"
        radius = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))
        assert radius["param"]["value"] == 0.4

    async def test_rectangle(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_rectangle(project_id=project, point1=[-1, 1], point2=[1, -1], bevel=0.1)
        )
        assert result["layer"]["type"] == "rectangle"

    async def test_polygon(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_polygon(
                project_id=project, vertices=[[0, 1], [1, -1], [-1, -1]], color="#00ff00"
            )
        )
        assert result["layer"]["type"] == "polygon"
        listed = payload(await tools.list_layers(project_id=project))["layers"]
        assert listed[0]["param_count"] > 0

    async def test_polygon_too_small(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.add_polygon(project_id=project, vertices=[[0, 0], [1, 1]])
        assert error(excinfo.value)["error"] == "parameter_error"

    async def test_star(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_star(project_id=project, points=6, radius1=1.0, regular_polygon=True)
        )
        assert result["layer"]["type"] == "star"
        with pytest.raises(RuntimeError):
            await tools.add_star(project_id=project, points=2)

    async def test_index_insertion(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="first")
        result = payload(
            await tools.add_solid_color(project_id=project, name="background", index=0)
        )
        assert result["index"] == 0
        names = [
            item["name"] for item in payload(await tools.list_layers(project_id=project))["layers"]
        ]
        assert names == ["background", "first"]


class TestBlineShapes:
    async def test_inline_region(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_region(
                project_id=project,
                vertices=[[-1, 0], [0, 1], [1, 0], [0, -1]],
                loop=True,
                color="#3366cc",
            )
        )
        assert result["layer"]["type"] == "region"

    async def test_outline_and_advanced(self, tools: ToolBox, project: str) -> None:
        out = payload(
            await tools.add_outline(project_id=project, vertices=[[0, 0], [1, 1]], width=0.1)
        )
        assert out["layer"]["type"] == "outline"
        adv = payload(
            await tools.add_advanced_outline(
                project_id=project, vertices=[[0, 0], [1, 0], [1, 1]], start_tip=1, end_tip=2
            )
        )
        assert adv["layer"]["type"] == "advanced_outline"

    async def test_bline_reference(self, tools: ToolBox, project: str) -> None:
        created = payload(
            await tools.add_bline(project_id=project, id="path1", vertices=[[0, 0], [1, 0], [1, 1]])
        )
        assert created["bline_id"] == "path1"
        region = payload(await tools.add_region(project_id=project, bline_id="path1"))
        assert region["layer"]["type"] == "region"
        info = payload(await tools.list_exported_values(project_id=project))
        assert any(entry["id"] == "path1" or entry["name"] == "path1" for entry in info["exported"])

    async def test_bline_errors(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError):
            await tools.add_bline(project_id=project, id="x", vertices=[[0, 0]])
        with pytest.raises(RuntimeError):
            await tools.add_bline(project_id=project, id="1bad", vertices=[[0, 0], [1, 1]])
        with pytest.raises(RuntimeError):
            await tools.add_region(project_id=project)
        with pytest.raises(RuntimeError):
            await tools.add_region(project_id=project, vertices=[[0, 0], [1, 1]], bline_id="also")


class TestContent:
    async def test_text(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_text(project_id=project, text="Hello\nWorld", origin=[0, 1], size=0.8)
        )
        assert result["layer"]["type"] == "text"
        text = payload(await tools.get_layer_param(project_id=project, layer=0, param="text"))
        assert "Hello" in text["param"]["value"]
        with pytest.raises(RuntimeError):
            await tools.add_text(project_id=project, text="   ")

    async def test_solid_and_checker(self, tools: ToolBox, project: str) -> None:
        solid = payload(await tools.add_solid_color(project_id=project, color="#102030"))
        assert solid["layer"]["type"] == "solid_color"
        checker = payload(await tools.add_checkerboard(project_id=project, size=[1, 1], pos=[0, 0]))
        assert checker["layer"]["type"] == "checker_board"

    async def test_gradients(self, tools: ToolBox, project: str) -> None:
        stops = [{"pos": 0.0, "color": "#000000"}, {"pos": 1.0, "color": "#ffffff"}]
        for kind in ("linear", "radial", "conical", "spiral"):
            result = payload(await tools.add_gradient(project_id=project, kind=kind, stops=stops))
            assert result["layer"]["type"].endswith("gradient")
            assert result["gradient_kind"] == kind

    async def test_gradient_errors(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError):
            await tools.add_gradient(project_id=project, kind="bogus", stops=[])
        with pytest.raises(RuntimeError):
            await tools.add_gradient(project_id=project)
        with pytest.raises(RuntimeError):
            await tools.add_gradient(
                project_id=project,
                stops=[{"pos": 0, "color": "#000000"}],
                gradient_id="both",
            )

    async def test_noise_gradient(self, tools: ToolBox, project: str) -> None:
        result = payload(await tools.add_noise_gradient(project_id=project, seed=7))
        assert result["layer"]["type"] == "noise"

    async def test_image_layers(self, tools: ToolBox, project: str, settings) -> None:
        image = settings.workspace / "pixel.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        added = payload(await tools.add_image(project_id=project, filename="pixel.png"))
        assert added["layer"]["type"] == "import"
        embedded = payload(
            await tools.embed_image(
                project_id=project, image_path="pixel.png", tl=[0, 1], br=[1, 0]
            )
        )
        assert embedded["layer"]["type"] == "import"
        assert Path(embedded["embedded"]).is_file()

    async def test_add_image_escape(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.add_image(project_id=project, filename="../nope.png")
        assert error(excinfo.value)["error"] == "workspace_error"


class TestFilters:
    @pytest.mark.parametrize(
        ("tool", "kwargs", "layer_type"),
        [
            ("add_blur", {"size": [0.2, 0.2]}, "blur"),
            ("add_motion_blur", {"aperture": 2.0}, "motion_blur"),
            ("add_color_correct", {"contrast": 0.2}, "colorcorrect"),
            ("add_halftone", {"kind": "halftone3"}, "halftone3"),
            ("add_clamp", {"floor": 0.1}, "clamp"),
            ("add_stretch", {"amount": [2, 2]}, "stretch"),
            ("add_rotate", {"angle": 45}, "rotate"),
            ("add_translate", {"offset": [1, 0]}, "translate"),
            ("add_zoom", {"amount": 2}, "zoom"),
            ("add_twirl", {"rotations": 10}, "twirl"),
            ("add_bevel", {"depth": 0.2}, "bevel"),
            ("add_shade", {"size": [0.2, 0.2]}, "shade"),
            ("add_radial_blur", {"fade_out": True}, "radial_blur"),
            ("add_distortions", {"seed": 1}, "noise_distort"),
            ("add_duplicate", {"index_source": 0}, "duplicate"),
        ],
    )
    async def test_filters(
        self, tools: ToolBox, project: str, tool: str, kwargs: dict, layer_type: str
    ) -> None:
        result = payload(await getattr(tools, tool)(project_id=project, **kwargs))
        assert result["layer"]["type"] == layer_type

    async def test_bad_halftone(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError):
            await tools.add_halftone(project_id=project, kind="bogus")
