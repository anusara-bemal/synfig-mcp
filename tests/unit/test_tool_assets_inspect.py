# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for asset and inspection tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree
from tests.conftest import ToolBox

from synfig_mcp.tools.common import AppContext


def payload(raw: str) -> dict:
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


class TestAssets:
    async def test_import_asset_copy(self, tools: ToolBox, settings, tmp_path: Path) -> None:
        source = settings.workspace / "logo.png"
        source.write_bytes(b"image-data")
        result = payload(await tools.import_asset(path="logo.png"))
        assert result["copied"] is True
        assert result["size_bytes"] == len(b"image-data")
        assert Path(result["path"]).parent.name == "assets"
        # Importing again from within assets is a no-op.
        again = payload(
            await tools.import_asset(
                path=Path(result["path"]).relative_to(settings.workspace).as_posix()
            )
        )
        assert again["copied"] is False

    async def test_import_asset_renames_on_collision(self, tools: ToolBox, settings) -> None:
        first = settings.workspace / "a.png"
        first.write_bytes(b"a")
        one = payload(await tools.import_asset(path="a.png", name="same.png"))
        second = settings.workspace / "b.png"
        second.write_bytes(b"b")
        two = payload(await tools.import_asset(path="b.png", name="same.png"))
        assert one["path"] != two["path"]
        assert Path(two["path"]).name == "same-2.png"

    async def test_import_asset_errors(self, tools: ToolBox, settings) -> None:
        with pytest.raises(RuntimeError):
            await tools.import_asset(path="missing.png")
        bad = settings.workspace / "thing.txt"
        bad.write_text("x", encoding="utf-8")
        with pytest.raises(RuntimeError) as excinfo:
            await tools.import_asset(path="thing.txt")
        assert error(excinfo.value)["error"] == "workspace_error"

    async def test_list_assets(self, tools: ToolBox, settings) -> None:
        (settings.workspace / "one.png").write_bytes(b"1")
        await tools.import_asset(path="one.png")
        listed = payload(await tools.list_assets())
        assert listed["count"] == 1
        assert listed["assets"][0]["suffix"] == ".png"

    async def test_embed_image_without_copy(self, tools: ToolBox, project: str, settings) -> None:
        image = settings.workspace / "keep.png"
        image.write_bytes(b"x")
        result = payload(
            await tools.embed_image(
                project_id=project,
                image_path="keep.png",
                copy_to_assets=False,
                name="kept",
            )
        )
        assert result["embedded"] == str(image)
        assert result["layer"]["name"] == "kept"

    async def test_import_svg(self, tools: ToolBox, project: str, settings) -> None:
        svg = settings.workspace / "shape.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', encoding="utf-8"
        )
        result = payload(await tools.import_svg(project_id=project, svg_path="shape.svg"))
        assert result["layer"]["type"] == "import"
        assert result["svg"] == str(svg)
        with pytest.raises(RuntimeError):
            await tools.import_svg(project_id=project, svg_path="missing.svg")

    async def test_set_canvas_inline(
        self, tools: ToolBox, project: str, context: AppContext
    ) -> None:
        session = await context.registry.get(project)
        root = session.root
        defs = session.defs(create=True)
        assert defs is not None
        canvas = etree.SubElement(defs, "canvas", attrib={"id": "inner"})
        etree.SubElement(canvas, "layer", attrib={"type": "circle", "active": "true"})
        layer = etree.SubElement(root, "layer", attrib={"type": "group", "active": "true"})
        param = etree.SubElement(layer, "param", attrib={"name": "canvas", "use": "inner"})

        result = payload(await tools.set_canvas_inline(project_id=project, canvas_id="inner"))
        assert result["inlined"] == 1
        assert param.get("use") is None
        assert param.find("canvas") is not None

        with pytest.raises(RuntimeError):
            await tools.set_canvas_inline(project_id=project, canvas_id="missing")


class TestSnapshots:
    async def test_roundtrip(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="dot", radius=0.3)
        snapshot = payload(await tools.export_json_snapshot(project_id=project))
        assert snapshot["snapshot"]["format"] == "synfig-mcp-snapshot/1"
        assert snapshot["snapshot"]["layers"][0]["name"] == "dot"

        restored = payload(
            await tools.import_json_snapshot(
                snapshot=json.dumps(snapshot), new_name="restored", path="restored.sif"
            )
        )
        assert restored["saved"].endswith("restored.sif")
        assert restored["info"]["name"] == "restored"
        assert Path(restored["saved"]).is_file()
        new_id = restored["project_id"]
        await tools.add_circle(project_id=new_id, name="second")
        layers = payload(await tools.list_layers(project_id=new_id))["layers"]
        assert len(layers) == 2

    async def test_import_object_and_errors(self, tools: ToolBox, project: str) -> None:
        snapshot = payload(await tools.export_json_snapshot(project_id=project))
        result = payload(await tools.import_json_snapshot(snapshot=snapshot["snapshot"]))
        assert result["project_id"]
        with pytest.raises(RuntimeError):
            await tools.import_json_snapshot(snapshot="not-json")
        with pytest.raises(RuntimeError):
            await tools.import_json_snapshot(snapshot={"project_id": "x"})
        with pytest.raises(RuntimeError):
            await tools.import_json_snapshot(snapshot={"xml_base64": "!!!"})


class TestDiff:
    async def test_same_project(self, tools: ToolBox, project: str) -> None:
        report = payload(await tools.diff_projects(a=project, b=project))
        assert report["summary"] == {
            "added": 0,
            "removed": 0,
            "changed": 0,
            "props_changed": 0,
        }

    async def test_added_removed_changed(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="stay", radius=0.2)
        copy = payload(await tools.duplicate_project(project_id=project, new_name="copy"))
        other = copy["project_id"]
        await tools.add_circle(project_id=other, name="extra")
        await tools.set_layer_param(project_id=other, layer=0, param="radius", value=0.9)
        report = payload(await tools.diff_projects(a=project, b=other))
        assert report["summary"]["added"] == 1
        assert report["summary"]["changed"] == 1

    async def test_file_paths(self, tools: ToolBox, project: str) -> None:
        info = payload(await tools.get_project_info(project))
        name = Path(info["path"]).name
        report = payload(await tools.diff_projects(a_path=name, b_path=name))
        assert report["summary"]["added"] == 0

    async def test_missing_arguments(self, tools: ToolBox) -> None:
        with pytest.raises(RuntimeError):
            await tools.diff_projects(a="only-one")
