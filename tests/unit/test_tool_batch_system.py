# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for batch operations, undo/redo, templates and system tools."""

from __future__ import annotations

import json

import pytest
from tests.conftest import ToolBox

from synfig_mcp.tools.common import AppContext


def payload(raw: str) -> dict:
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


class TestBatch:
    async def test_run_operations(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.batch_operations(
                project_id=project,
                operations=[
                    {"tool": "add_circle", "arguments": {"name": "a", "radius": 0.2}},
                    {"tool": "add_rectangle", "arguments": {"name": "b"}},
                    {"tool": "add_solid_color", "arguments": {"name": "bg", "index": 0}},
                ],
            )
        )
        assert result["operations_run"] == 3
        assert result["rolled_back"] is False
        assert [item["index"] for item in result["results"]] == [0, 1, 2]
        layers = payload(await tools.list_layers(project_id=project))["layers"]
        assert [item["name"] for item in layers] == ["bg", "a", "b"]

    async def test_project_id_inferred(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.batch_operations(
                operations=[
                    {"tool": "add_circle", "arguments": {"project_id": project, "name": "a"}}
                ]
            )
        )
        assert result["project_id"] == project

    async def test_rollback_on_failure(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.batch_operations(
                project_id=project,
                operations=[
                    {"tool": "add_circle", "arguments": {"name": "a"}},
                    {"tool": "add_polygon", "arguments": {"vertices": [[0, 0], [1, 1]]}},
                ],
            )
        data = error(excinfo.value)
        assert data["error"] == "batch_operation_error"
        assert payload(await tools.list_layers(project_id=project))["count"] == 0

    async def test_partial_without_rollback(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError):
            await tools.batch_operations(
                project_id=project,
                rollback_on_error=False,
                operations=[
                    {"tool": "add_circle", "arguments": {"name": "a"}},
                    {"tool": "add_polygon", "arguments": {"vertices": [[0, 0]]}},
                ],
            )
        assert payload(await tools.list_layers(project_id=project))["count"] == 1

    async def test_validation_errors(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError):
            await tools.batch_operations(project_id=project, operations=[])
        with pytest.raises(RuntimeError):
            await tools.batch_operations(
                project_id=project, operations=[{"tool": "", "arguments": {}}]
            )
        with pytest.raises(RuntimeError):
            await tools.batch_operations(
                project_id=project,
                operations=[{"tool": "add_circle", "arguments": "not-an-object"}],
            )
        with pytest.raises(RuntimeError):
            await tools.batch_operations(
                project_id=project, operations=[{"tool": "batch_operations", "arguments": {}}]
            )
        with pytest.raises(RuntimeError):
            await tools.batch_operations(operations=[{"tool": "add_circle"}])

    async def test_undo_redo(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        undone = payload(await tools.undo(project_id=project))
        assert undone["undone"] is True
        assert payload(await tools.list_layers(project_id=project))["count"] == 0
        redone = payload(await tools.redo(project_id=project))
        assert redone["redone"] is True
        assert payload(await tools.list_layers(project_id=project))["count"] == 1

    async def test_undo_batch_as_one_step(self, tools: ToolBox, project: str) -> None:
        await tools.batch_operations(
            project_id=project,
            operations=[
                {"tool": "add_circle", "arguments": {"name": "a"}},
                {"tool": "add_rectangle", "arguments": {"name": "b"}},
            ],
        )
        assert payload(await tools.list_layers(project_id=project))["count"] == 2
        await tools.undo(project_id=project)
        assert payload(await tools.list_layers(project_id=project))["count"] == 0


class TestTemplates:
    @pytest.mark.parametrize("template", ["bouncing-ball", "title-card", "logo-reveal"])
    async def test_templates(self, tools: ToolBox, project: str, template: str) -> None:
        result = payload(
            await tools.apply_template(project_id=project, template=template, name="Demo")
        )
        assert result["template"] == template
        assert result["created_layers"]
        layers = payload(await tools.list_layers(project_id=project))["layers"]
        assert len(layers) == len(result["created_layers"])
        assert all(item["name"] for item in layers)

    async def test_unknown_template(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.apply_template(project_id=project, template="bogus")
        assert error(excinfo.value)["error"] == "parameter_error"


class TestSystem:
    async def test_doctor_without_binary(self, tools: ToolBox, context: AppContext) -> None:
        context._probed = {
            "found": False,
            "version": None,
            "targets": [],
            "renderers": [],
            "layers": [],
            "problems": ["synfig binary not found"],
        }
        report = payload(await tools.synfig_doctor())
        assert report["found"] is False
        assert report["healthy"] is False
        assert report["workspace_writable"] is True
        assert any("binary" in problem for problem in report["problems"])
        assert report["config"]["history_depth"] == 20
        assert report["resolved_via"]

    async def test_doctor_with_probe(self, tools: ToolBox, context: AppContext) -> None:
        context._probed = {
            "found": True,
            "version": "synfig 1.5.5",
            "targets": ["png"],
            "renderers": ["cairo"],
            "layers": ["circle"],
            "problems": [],
        }
        report = payload(await tools.synfig_doctor())
        assert report["healthy"] is True
        assert report["version"] == "synfig 1.5.5"

    async def test_version_and_targets_without_binary(
        self, tools: ToolBox, context: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(context, "binary_path", lambda: None)
        with pytest.raises(RuntimeError) as excinfo:
            await tools.synfig_version()
        assert error(excinfo.value)["error"] == "synfig_binary_not_found"
        context._probed = {"found": False, "targets": [], "renderers": [], "problems": ["missing"]}
        targets = payload(await tools.list_render_targets())
        assert targets["targets"] == []
        assert targets["problems"] == ["missing"]

    async def test_version_and_targets_with_probe(
        self, tools: ToolBox, context: AppContext
    ) -> None:
        context._probed = {
            "found": True,
            "version": "synfig 1.5.5",
            "targets": ["png", "gif"],
            "renderers": ["cairo"],
            "layers": [],
            "problems": [],
        }
        version = payload(await tools.synfig_version())
        assert version["version"] == "synfig 1.5.5"
        targets = payload(await tools.list_render_targets())
        assert targets["targets"] == ["png", "gif"]

    async def test_layer_types(self, tools: ToolBox, context: AppContext) -> None:
        context._probed = {"found": False, "layers": ["my_custom_layer"], "problems": []}
        result = payload(await tools.list_layer_types())
        assert "circle" in result["layer_types"]
        assert "my_custom_layer" in result["layer_types"]
        assert result["count"] == len(result["layer_types"])
