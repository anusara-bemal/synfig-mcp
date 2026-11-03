# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for generic layer tools."""

from __future__ import annotations

import json

import pytest
from tests.conftest import ToolBox


def payload(raw: str) -> dict:
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


class TestAddLayer:
    async def test_add_circle(self, tools: ToolBox, project: str) -> None:
        result = payload(await tools.add_layer(project_id=project, layer_type="circle", name="dot"))
        assert result["index"] == 0
        assert result["layer"]["type"] == "circle"
        assert result["layer"]["name"] == "dot"

    async def test_add_with_params(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_layer(
                project_id=project,
                layer_type="circle",
                params={"radius": 0.25, "color": "#ff8800", "origin": [0.1, 0.2]},
                amount=0.5,
                blend_method="multiply",
            )
        )
        assert result["layer"]["amount"] == 0.5
        assert result["layer"]["blend_method"] == 6

    async def test_add_inactive(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.add_layer(project_id=project, layer_type="circle", active=False)
        )
        assert result["layer"]["active"] is False

    async def test_unknown_type(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.add_layer(project_id=project, layer_type="not-a-layer")
        assert error(excinfo.value)["error"] == "unknown_layer_type"

    async def test_missing_project(self, tools: ToolBox) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.add_layer(project_id="nope", layer_type="circle")
        assert error(excinfo.value)["error"] == "project_not_found"

    async def test_bad_param(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        with pytest.raises(RuntimeError):
            await tools.set_layer_param(
                project_id=project, layer=0, param="radius", value="not-a-number", type="real"
            )


class TestModify:
    async def test_delete(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        result = payload(await tools.delete_layer(project_id=project, layer=0))
        assert result["deleted_index"] == 0
        assert payload(await tools.list_layers(project_id=project))["count"] == 0

    async def test_delete_missing(self, tools: ToolBox, project: str) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.delete_layer(project_id=project, layer="ghost")
        assert error(excinfo.value)["error"] == "layer_not_found"

    async def test_duplicate(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        result = payload(await tools.duplicate_layer(project_id=project, layer=0, new_name="copy"))
        assert result["index"] == 1
        assert result["layer"]["name"] == "copy"
        assert payload(await tools.list_layers(project_id=project))["count"] == 2

    async def test_move_and_z(self, tools: ToolBox, project: str) -> None:
        for name in ("a", "b", "c"):
            await tools.add_circle(project_id=project, name=name)
        result = payload(await tools.move_layer(project_id=project, layer=0, index=2, z_depth=1.5))
        assert result["index"] == 2
        assert result["layer"]["z_depth"] == 1.5
        names = [
            item["name"] for item in payload(await tools.list_layers(project_id=project))["layers"]
        ]
        assert names == ["b", "c", "a"]

    async def test_move_offset(self, tools: ToolBox, project: str) -> None:
        for name in ("a", "b", "c"):
            await tools.add_circle(project_id=project, name=name)
        result = payload(await tools.move_layer(project_id=project, layer=0, offset=1))
        assert result["index"] == 1

    async def test_rename_and_errors(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        renamed = payload(await tools.rename_layer(project_id=project, layer=0, name="renamed"))
        assert renamed["layer"]["name"] == "renamed"
        with pytest.raises(RuntimeError):
            await tools.rename_layer(project_id=project, layer=0, name="   ")

    async def test_params(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        result = payload(
            await tools.set_layer_param(project_id=project, layer=0, param="color", value="#ff8800")
        )
        assert result["param"]["type"] == "color"
        assert result["param"]["value"]["hex"].upper().startswith("#FF8800")
        read = payload(await tools.get_layer_param(project_id=project, layer=0, param="color"))
        assert read["param"]["type"] == "color"
        missing = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))
        assert missing["param"]["type"] == "real"

    async def test_get_layer(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        data = payload(await tools.get_layer(project_id=project, layer=0))["layer"]
        assert data["index"] == 0
        assert any(param["name"] == "radius" for param in data["params"])
        no_params = payload(
            await tools.get_layer(project_id=project, layer=0, include_params=False)
        )["layer"]
        assert "params" not in no_params

    async def test_list_with_params(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        listed = payload(await tools.list_layers(project_id=project, include_params=True))
        assert listed["layers"][0]["params"]

    async def test_enable_disable(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        assert payload(await tools.disable_layer(project_id=project, layer=0))["active"] is False
        assert payload(await tools.enable_layer(project_id=project, layer=0))["active"] is True

    async def test_blend_amount_z(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        blend = payload(
            await tools.set_blend_method(project_id=project, layer=0, blend_method="add")
        )
        assert blend["blend_method_name"].lower() == "add"
        assert (
            payload(await tools.set_amount(project_id=project, layer=0, amount=0.25))["amount"]
            == 0.25
        )
        assert (
            payload(await tools.set_z_depth(project_id=project, layer=0, z_depth=-2.0))["z_depth"]
            == -2.0
        )

    async def test_bad_amounts(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        with pytest.raises(RuntimeError):
            await tools.set_amount(project_id=project, layer=0, amount=2.0)
        with pytest.raises(RuntimeError):
            await tools.set_amount(project_id=project, layer=0, amount="x")
        with pytest.raises(RuntimeError):
            await tools.set_z_depth(project_id=project, layer=0, z_depth="x")
        with pytest.raises(RuntimeError):
            await tools.set_blend_method(project_id=project, layer=0, blend_method="bogus")

    async def test_lock_and_exclude(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        assert payload(await tools.lock_layer(project_id=project, layer=0))["locked"] is True
        assert (
            payload(await tools.exclude_from_rendering(project_id=project, layer=0))["excluded"]
            is True
        )
        listed = payload(await tools.list_layers(project_id=project))["layers"][0]
        assert listed["hit_locked"] is True
        assert listed["exclude_from_rendering"] is True
        assert (
            payload(await tools.lock_layer(project_id=project, layer=0, locked=False))["locked"]
            is False
        )


class TestGroups:
    async def test_group_ungroup(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        await tools.add_circle(project_id=project, name="b")
        grouped = payload(await tools.group_layers(project_id=project, layers=[0, 1], name="grp"))
        assert grouped["group_index"] == 0
        assert grouped["group"]["type"] == "group"
        tree = payload(await tools.list_layers(project_id=project))["layers"]
        assert tree[0]["name"] == "grp"
        assert tree[1]["depth"] == 1

        ungrouped = payload(await tools.ungroup_layers(project_id=project, layer=0))
        assert ungrouped["ungrouped"] == 2
        assert payload(await tools.list_layers(project_id=project))["count"] == 2

    async def test_group_errors(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        with pytest.raises(RuntimeError):
            await tools.group_layers(project_id=project, layers=[])
        with pytest.raises(RuntimeError) as excinfo:
            await tools.group_layers(project_id=project, layers=[9])
        assert error(excinfo.value)["error"] == "parameter_error"

    async def test_ungroup_non_group(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        with pytest.raises(RuntimeError) as excinfo:
            await tools.ungroup_layers(project_id=project, layer=0)
        assert "not a group" in error(excinfo.value)["message"]


class TestHistory:
    async def test_undo_redo_layer(self, tools: ToolBox, project: str) -> None:
        await tools.add_circle(project_id=project, name="a")
        await tools.undo(project_id=project)
        assert payload(await tools.list_layers(project_id=project))["count"] == 0
        await tools.redo(project_id=project)
        assert payload(await tools.list_layers(project_id=project))["count"] == 1
