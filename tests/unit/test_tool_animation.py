# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for animation, waypoints, keyframes, bones and exports."""

from __future__ import annotations

import json

import pytest
from tests.conftest import ToolBox


def payload(raw: str) -> dict:
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


async def circle(tools: ToolBox, project: str, name: str, radius: float = 0.5) -> None:
    await tools.add_circle(project_id=project, name=name, radius=radius)


class TestWaypoints:
    async def test_animate_param(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        result = payload(
            await tools.animate_param(
                project_id=project,
                layer=0,
                param="radius",
                waypoints=[
                    {"time": "0f", "value": 0.2},
                    {"time": "24f", "value": 0.8},
                ],
                interpolation="linear",
            )
        )
        assert result["waypoints_set"] == 2
        param = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))[
            "param"
        ]
        assert param["type"] == "animated"
        assert len(param["value"]["waypoints"]) == 2

    async def test_add_remove_waypoint(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        await tools.animate_param(
            project_id=project,
            layer=0,
            param="radius",
            waypoints=[{"time": "0f", "value": 0.2}],
        )
        await tools.add_waypoint(
            project_id=project,
            layer=0,
            param="radius",
            time="12f",
            value=0.6,
            interpolation="clamped",
        )
        param = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))[
            "param"
        ]
        assert len(param["value"]["waypoints"]) == 2
        assert any(wp["before"] == "clamped" for wp in param["value"]["waypoints"])

        removed = payload(
            await tools.remove_waypoint(project_id=project, layer=0, param="radius", time="12f")
        )
        assert removed["removed"] is True
        with pytest.raises(RuntimeError) as excinfo:
            await tools.remove_waypoint(project_id=project, layer=0, param="radius", time="12f")
        assert error(excinfo.value)["error"] == "waypoint_error"

    async def test_set_interpolation(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        await tools.animate_param(
            project_id=project,
            layer=0,
            param="radius",
            waypoints=[{"time": "0f", "value": 0.2}, {"time": "24f", "value": 0.8}],
        )
        all_wps = payload(
            await tools.set_interpolation(
                project_id=project, layer=0, param="radius", interpolation="tcb"
            )
        )
        assert all_wps["waypoints_updated"] == 2
        one = payload(
            await tools.set_interpolation(
                project_id=project,
                layer=0,
                param="radius",
                interpolation="constant",
                time="1s",
            )
        )
        assert one["waypoints_updated"] == 1

    async def test_animate_bad_param(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        with pytest.raises(RuntimeError):
            await tools.animate_param(
                project_id=project,
                layer=0,
                param="ghost",
                waypoints=[{"time": "0f", "value": 1}],
            )


class TestKeyframes:
    async def test_add_list_move_remove(self, tools: ToolBox, project: str) -> None:
        first = payload(await tools.add_keyframe(project_id=project, time="12f", label="intro"))
        assert first["time"] == "12f"
        assert first["updated"] is False
        again = payload(await tools.add_keyframe(project_id=project, time="12f", label="later"))
        assert again["updated"] is True

        listed = payload(await tools.list_keyframes(project_id=project))["keyframes"]
        assert len(listed) == 1
        assert listed[0]["label"] == "later"

        moved = payload(
            await tools.move_keyframe(project_id=project, from_time="12f", to_time="1s")
        )
        assert moved["to"] == "1s"
        payload(await tools.remove_keyframe(project_id=project, time="1s"))
        assert payload(await tools.list_keyframes(project_id=project))["keyframes"] == []
        with pytest.raises(RuntimeError):
            await tools.remove_keyframe(project_id=project, time="1s")
        with pytest.raises(RuntimeError):
            await tools.move_keyframe(project_id=project, from_time="1s", to_time="2s")


class TestTimeLoopAndOffset:
    async def test_time_loop(self, tools: ToolBox, project: str) -> None:
        result = payload(
            await tools.set_time_loop(
                project_id=project, duration="1s", link_time="0f", symmetrical=True
            )
        )
        assert result["timeloop"]["type"] == "timeloop"

    async def test_time_offset(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        await tools.group_layers(project_id=project, layers=[0], name="grp")
        result = payload(
            await tools.add_time_offset(project_id=project, layer=0, time_offset="12f")
        )
        assert result["time_offset"] == "12f"
        with pytest.raises(RuntimeError):
            await tools.add_time_offset(project_id=project, layer=1, time_offset="0f")


class TestConvert:
    async def test_static_and_animated(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        animated = payload(
            await tools.convert_param(project_id=project, layer=0, param="radius", to="animated")
        )
        assert animated["converted_to"] == "animated"
        param = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))[
            "param"
        ]
        assert param["type"] == "animated"

        await tools.add_waypoint(project_id=project, layer=0, param="radius", time="12f", value=0.9)
        static = payload(
            await tools.convert_param(project_id=project, layer=0, param="radius", to="static")
        )
        assert static["converted_to"] == "static"
        param = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))[
            "param"
        ]
        assert param["type"] == "real"

    async def test_linked_and_unlinked(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "a", radius=0.3)
        await circle(tools, project, "b", radius=0.9)
        linked = payload(
            await tools.convert_param(
                project_id=project,
                layer=1,
                param="radius",
                to="linked",
                source_layer=0,
                source_param="radius",
                export_name="shared",
            )
        )
        assert linked["converted_to"] == "linked"
        unlinked = payload(await tools.unlink_params(project_id=project, layer=1, param="radius"))
        assert unlinked["param"] == "radius"

    async def test_exported(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "a")
        result = payload(
            await tools.export_value(
                project_id=project, layer=0, param="radius", export_name="radius_value"
            )
        )
        assert result["export_name"] == "radius_value"
        exported = payload(await tools.list_exported_values(project_id=project))["exported"]
        assert any(
            entry.get("id") == "radius_value" or entry.get("name") == "radius_value"
            for entry in exported
        )
        with pytest.raises(RuntimeError):
            await tools.export_value(
                project_id=project, layer=0, param="radius", export_name="radius_value"
            )

    async def test_bad_target(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "a")
        with pytest.raises(RuntimeError):
            await tools.convert_param(project_id=project, layer=0, param="radius", to="bogus")
        with pytest.raises(RuntimeError):
            await tools.convert_param(project_id=project, layer=0, param="radius", to="linked")


class TestBake:
    async def test_bake(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        await tools.animate_param(
            project_id=project,
            layer=0,
            param="radius",
            waypoints=[{"time": "0f", "value": 0.2}, {"time": "1s", "value": 0.8}],
            interpolation="linear",
        )
        result = payload(
            await tools.bake_animation(
                project_id=project,
                layer=0,
                param="radius",
                begin_time="0f",
                end_time="1s",
                step_frames=12,
            )
        )
        assert result["waypoints_created"] == 3
        param = payload(await tools.get_layer_param(project_id=project, layer=0, param="radius"))[
            "param"
        ]
        assert len(param["value"]["waypoints"]) == 3

    async def test_bake_errors(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        with pytest.raises(RuntimeError):
            await tools.bake_animation(
                project_id=project,
                layer=0,
                param="radius",
                begin_time="1s",
                end_time="0f",
            )
        with pytest.raises(RuntimeError):
            await tools.bake_animation(project_id=project, layer=0, param="radius", step_frames=0)


class TestBones:
    async def test_create_list_set(self, tools: ToolBox, project: str) -> None:
        first = payload(
            await tools.create_bone(
                project_id=project, name="spine", origin=[0, 0], angle=90, length=2
            )
        )
        assert first["name"] == "spine"
        assert len(first["guid"]) == 32
        second = payload(await tools.create_bone(project_id=project, name="arm", parent="spine"))
        assert second["parent_guid"] == first["guid"]

        bones = payload(await tools.list_bones_tool(project_id=project))["bones"]
        assert [bone["name"] for bone in bones] == ["spine", "arm"]
        assert bones[0]["origin"]["x"] == 0.0

        updated = payload(
            await tools.set_bone_param(project_id=project, bone="arm", param="length", value=1.5)
        )
        assert updated["value"] == 1.5
        renamed = payload(
            await tools.set_bone_param(
                project_id=project, bone="arm", param="name", value="forearm"
            )
        )
        assert renamed["param"] == "name"
        bones = payload(await tools.list_bones_tool(project_id=project))["bones"]
        assert bones[1]["name"] == "forearm"

    async def test_bone_errors(self, tools: ToolBox, project: str) -> None:
        await tools.create_bone(project_id=project, name="a")
        with pytest.raises(RuntimeError):
            await tools.create_bone(project_id=project, name="a")
        with pytest.raises(RuntimeError):
            await tools.create_bone(project_id=project, name="1 bad")
        with pytest.raises(RuntimeError):
            await tools.create_bone(project_id=project, name="b", parent="ghost")
        with pytest.raises(RuntimeError):
            await tools.set_bone_param(project_id=project, bone="ghost", param="length", value=1)
        with pytest.raises(RuntimeError):
            await tools.set_bone_param(project_id=project, bone="a", param="bogus", value=1)
        with pytest.raises(RuntimeError):
            await tools.set_bone_param(project_id=project, bone="a", param="parent", value="ghost")

    async def test_bind_skeleton(self, tools: ToolBox, project: str) -> None:
        await circle(tools, project, "ball")
        await tools.create_bone(project_id=project, name="root", angle=0)
        result = payload(
            await tools.bind_skeleton(
                project_id=project, layer=0, param="origin", bones=["root"], weights=[1.0]
            )
        )
        assert result["type"] == "vector"
        assert result["bones"][0]["ref"] == "root"
        with pytest.raises(RuntimeError):
            await tools.bind_skeleton(project_id=project, layer=0, param="origin", bones=[])
        with pytest.raises(RuntimeError):
            await tools.bind_skeleton(
                project_id=project, layer=0, param="origin", bones=["root", "ghost"]
            )
        with pytest.raises(RuntimeError):
            await tools.bind_skeleton(project_id=project, layer=0, param="radius", bones=["root"])
