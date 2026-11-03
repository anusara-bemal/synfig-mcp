# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for project lifecycle tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.conftest import ToolBox


def payload(raw: str) -> dict:
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


@pytest.fixture
def box(tools: ToolBox) -> ToolBox:
    return tools


class TestCreate:
    async def test_default_save(self, box: ToolBox, tmp_path: Path) -> None:
        result = payload(await box.create_project(name="My Project", width=640, height=360))
        assert result["saved"].endswith("My Project.sif")
        assert Path(result["saved"]).is_file()
        assert result["info"]["width"] == 640
        assert result["info"]["height"] == 360

    async def test_unsaved(self, box: ToolBox) -> None:
        result = payload(await box.create_project(name="unsaved", save=False))
        assert result["saved"] is None
        assert result["info"]["layer_count"] == 0

    async def test_custom_path_and_options(self, box: ToolBox) -> None:
        result = payload(
            await box.create_project(
                name="opts",
                width=100,
                height=50,
                fps=30,
                begin_time="1s",
                end_time="2s",
                background="#102030",
                x_res=1000,
                y_res=1000,
                view_box=[-2, 2, 2, -2],
                gamma=[1.1, 1.0, 0.9],
                antialias=4,
                path="nested/opts.sifz",
            )
        )
        assert result["saved"].endswith("opts.sifz")
        assert result["info"]["fps"] == 30.0
        assert result["info"]["antialias"] == 4

    @pytest.mark.parametrize("name", ["", "   "])
    async def test_empty_name(self, box: ToolBox, name: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await box.create_project(name=name)
        assert error(excinfo.value)["error"] == "parameter_error"

    async def test_bad_time_range(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await box.create_project(name="bad", begin_time="2s", end_time="1s")
        assert "end_time" in error(excinfo.value)["message"]

    async def test_bad_view_box(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError):
            await box.create_project(name="bad", view_box=[1, 2, 3])

    async def test_bad_gamma(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError):
            await box.create_project(name="bad", gamma=[1, 2])

    async def test_resolution_limit(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await box.create_project(name="huge", width=99999, height=99999)
        assert error(excinfo.value)["error"] == "limit_exceeded"

    async def test_bad_path_escape(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await box.create_project(name="bad", path="../escape.sif")
        assert error(excinfo.value)["error"] == "workspace_error"


class TestOpenSave:
    async def test_open_existing(self, box: ToolBox, project: str) -> None:
        path = payload(await box.get_project_info(project))["path"]
        assert path
        opened = payload(await box.open_project(path=Path(path).name))
        assert opened["info"]["project_id"] == project or opened.get("already_open") is True

    async def test_open_missing(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await box.open_project(path="missing.sif")
        assert error(excinfo.value)["error"] == "workspace_error"

    async def test_save_default_and_as(self, box: ToolBox, project: str) -> None:
        await box.add_circle(project_id=project, name="dot")
        saved = payload(await box.save_project(project_id=project, backup=False))
        assert saved["format"] == "sif"
        other = payload(await box.save_project_as(project_id=project, path="copy.sifz"))
        assert other["saved"].endswith("copy.sifz")
        assert Path(other["saved"]).is_file()

    async def test_close_discard(self, box: ToolBox, project: str) -> None:
        await box.add_circle(project_id=project, name="dot")
        result = payload(await box.close_project(project_id=project, save=False))
        assert result["discarded_unsaved_changes"] is True
        with pytest.raises(RuntimeError):
            await box.get_project_info(project)

    async def test_close_save(self, box: ToolBox, project: str) -> None:
        await box.add_circle(project_id=project, name="dot")
        result = payload(await box.close_project(project_id=project, save=True))
        assert result["saved"] is True

    async def test_list_projects(self, box: ToolBox, project: str) -> None:
        projects = payload(await box.list_open_projects())["projects"]
        assert any(item["project_id"] == project for item in projects)

    async def test_info(self, box: ToolBox, project: str) -> None:
        info = payload(await box.get_project_info(project))
        assert info["project_id"] == project
        assert info["width"] == 256

    async def test_duplicate(self, box: ToolBox, project: str) -> None:
        result = payload(await box.duplicate_project(project_id=project, new_name="copy"))
        assert result["source_project_id"] == project
        assert Path(result["path"]).is_file()
        assert result["info"]["name"] == "copy"


class TestProperties:
    async def test_set_canvas(self, box: ToolBox, project: str) -> None:
        result = payload(
            await box.set_canvas_properties(
                project_id=project,
                width=320,
                height=200,
                x_res=2000,
                y_res=2000,
                view_box=[-1, 1, 1, -1],
                antialias=2,
                background="#000000",
                gamma=1.2,
            )
        )
        assert result["canvas"]["width"] == 320
        assert result["canvas"]["height"] == 200

    async def test_bad_canvas(self, box: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError):
            await box.set_canvas_properties(project_id=project, view_box=[1, 2, 3])
        with pytest.raises(RuntimeError):
            await box.set_canvas_properties(project_id=project, width=0)

    async def test_time_range(self, box: ToolBox, project: str) -> None:
        result = payload(
            await box.set_time_range(project_id=project, begin_time="1s", end_time="3s")
        )
        assert result["end_time"] == "3s"
        with pytest.raises(RuntimeError):
            await box.set_time_range(project_id=project, begin_time="3s", end_time="1s")

    async def test_fps(self, box: ToolBox, project: str) -> None:
        assert payload(await box.set_fps(project_id=project, fps=30))["fps"] == 30
        with pytest.raises(RuntimeError):
            await box.set_fps(project_id=project, fps=0)
        with pytest.raises(RuntimeError):
            await box.set_fps(project_id=project, fps="x")

    async def test_image_span(self, box: ToolBox, project: str) -> None:
        assert payload(await box.set_image_span(project_id=project, span=2.0))["image_span"] == 2.0
        assert payload(await box.set_image_span(project_id=project, span=3.0))["image_span"] == 3.0
        with pytest.raises(RuntimeError):
            await box.set_image_span(project_id=project, span=0)
        with pytest.raises(RuntimeError):
            await box.set_image_span(project_id=project, span="x")


class TestValidate:
    async def test_open_project(self, box: ToolBox, project: str) -> None:
        report = payload(await box.validate_project(project_id=project))
        assert report["valid"] is True

    async def test_file(self, box: ToolBox, project: str) -> None:
        path = Path(payload(await box.get_project_info(project))["path"])
        report = payload(await box.validate_project(path=path.name))
        assert report["valid"] is True
        assert report["path"].endswith(".sif")

    async def test_missing_arguments(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError):
            await box.validate_project()

    async def test_missing_file(self, box: ToolBox) -> None:
        with pytest.raises(RuntimeError):
            await box.validate_project(path="missing.sif")
