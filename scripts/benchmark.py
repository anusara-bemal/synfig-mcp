# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Comprehensive feature capability benchmark and scoring suite for synfig-mcp.

Tests all MCP tools against real Synfig Studio documents and CLI execution,
computing category-specific scores and an overall production grade rank.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from synfig_mcp.config import Settings
from synfig_mcp.server import create_server


def parse_payload(res: Any) -> dict[str, Any]:
    if isinstance(res, list):
        for item in res:
            if hasattr(item, "text"):
                return json.loads(item.text)
        return {}
    if isinstance(res, str):
        try:
            return json.loads(res)
        except Exception:
            return {"raw": res}
    if isinstance(res, dict):
        return res
    return {}


@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    duration_ms: float
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    def __init__(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="synfig_mcp_bench_"))
        self.settings = Settings(
            workspace=self.tmp_dir,
            history_depth=50,
            render_timeout=120.0,
        )
        self.server = create_server(self.settings)
        self.tools: dict[str, Any] = {
            t.name: t.fn for t in self.server._tool_manager.list_tools()
        }
        self.results: list[TestResult] = []

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    async def run_test(
        self,
        name: str,
        category: str,
        test_fn: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        start = time.perf_counter()
        try:
            await test_fn()
            duration = (time.perf_counter() - start) * 1000.0
            self.results.append(
                TestResult(name=name, category=category, passed=True, duration_ms=duration)
            )
            print(f"  [PASS] {name:<35} ({duration:6.1f}ms)")
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000.0
            self.results.append(
                TestResult(
                    name=name,
                    category=category,
                    passed=False,
                    duration_ms=duration,
                    message=str(exc),
                )
            )
            print(f"  [FAIL] {name:<35}: {exc}")

    async def execute_all(self) -> None:
        print("\n=======================================================")
        print("   SYNFIG MCP PRODUCTION FEATURE CAPABILITY BENCHMARK   ")
        print("=======================================================\n")

        # ---------------------------------------------------------
        # 1. System & Doctor Diagnostics
        # ---------------------------------------------------------
        print("[1/10] Testing System & Diagnostics...")
        await self.run_test("synfig_doctor", "System", self._test_doctor)
        await self.run_test("synfig_version", "System", self._test_version)
        await self.run_test("list_render_targets", "System", self._test_render_targets)
        await self.run_test("list_layer_types", "System", self._test_layer_types)

        # ---------------------------------------------------------
        # 2. Project Lifecycle & Multi-Format Documents
        # ---------------------------------------------------------
        print("\n[2/10] Testing Project Lifecycle & Formats (.sif, .sifz, .sfg)...")
        await self.run_test("create_project", "Project", self._test_create_project)
        await self.run_test("canvas_properties", "Project", self._test_canvas_props)
        await self.run_test("set_fps_and_time_range", "Project", self._test_fps_time_range)
        await self.run_test("save_and_reopen_sif", "Project", self._test_sif_roundtrip)
        await self.run_test("save_and_reopen_sifz", "Project", self._test_sifz_roundtrip)
        await self.run_test("save_and_reopen_sfg", "Project", self._test_sfg_roundtrip)
        await self.run_test("duplicate_project", "Project", self._test_duplicate)
        await self.run_test("validate_project", "Project", self._test_validate)

        # ---------------------------------------------------------
        # 3. Layer Manipulation
        # ---------------------------------------------------------
        print("\n[3/10] Testing Layer Tree & Hierarchy Manipulation...")
        await self.run_test("add_and_list_layers", "Layers", self._test_layers_add_list)
        await self.run_test("layer_parameters", "Layers", self._test_layer_params)
        await self.run_test("layer_blending_and_opacity", "Layers", self._test_layer_blend_amount)
        await self.run_test("layer_reorder_and_zdepth", "Layers", self._test_layer_reorder)
        await self.run_test("layer_enable_disable", "Layers", self._test_layer_enable_disable)
        await self.run_test("layer_group_and_ungroup", "Layers", self._test_layer_grouping)

        # ---------------------------------------------------------
        # 4. Vector Shapes & Content
        # ---------------------------------------------------------
        print("\n[4/10] Testing Vector Shapes & Primitives...")
        await self.run_test("shape_circle_rect_polygon", "Shapes", self._test_primitives)
        await self.run_test("shape_star_and_text", "Shapes", self._test_star_and_text)
        await self.run_test("shape_bline_and_outlines", "Shapes", self._test_bline_and_outlines)
        await self.run_test("gradients_and_patterns", "Shapes", self._test_gradients_and_patterns)

        # ---------------------------------------------------------
        # 5. Visual Filters & Effects
        # ---------------------------------------------------------
        print("\n[5/10] Testing Visual Filters & Effects...")
        await self.run_test("filter_blur_motion_radial", "Filters", self._test_blurs)
        await self.run_test("filter_color_correct_halftone", "Filters", self._test_color_filters)
        await self.run_test("filter_transforms_and_twirl", "Filters", self._test_transforms)
        await self.run_test("filter_bevel_and_shade", "Filters", self._test_bevel_shade)

        # ---------------------------------------------------------
        # 6. Animation, Timeline & Keyframes
        # ---------------------------------------------------------
        print("\n[6/10] Testing Animation, Waypoints & Keyframes...")
        await self.run_test("animate_waypoints_and_interpolation", "Animation", self._test_waypoints)
        await self.run_test("keyframes_management", "Animation", self._test_keyframes)
        await self.run_test("timeloop_and_timeoffset", "Animation", self._test_time_loop_offset)
        await self.run_test("bake_animation", "Animation", self._test_bake)

        # ---------------------------------------------------------
        # 7. Rigging, Bones & Parameter Linking
        # ---------------------------------------------------------
        print("\n[7/10] Testing Rigging, Bones & Linking...")
        await self.run_test("create_and_link_bones", "Rigging", self._test_bones)
        await self.run_test("export_value_and_link_params", "Rigging", self._test_export_and_link)

        # ---------------------------------------------------------
        # 8. Asset Pipeline & Embedding
        # ---------------------------------------------------------
        print("\n[8/10] Testing Asset Pipeline...")
        await self.run_test("import_asset_and_embed_image", "Assets", self._test_asset_pipeline)

        # ---------------------------------------------------------
        # 9. Real Synfig CLI Rendering
        # ---------------------------------------------------------
        print("\n[9/10] Testing Real Synfig CLI Rendering Engine...")
        await self.run_test("render_single_png_frame", "Rendering", self._test_render_frame)
        await self.run_test("render_preview_and_thumbnail", "Rendering", self._test_render_preview_thumb)
        await self.run_test("render_animated_gif", "Rendering", self._test_render_gif)
        await self.run_test("get_render_status_and_jobs", "Rendering", self._test_render_status)

        # ---------------------------------------------------------
        # 10. Batch Operations & History Rollback
        # ---------------------------------------------------------
        print("\n[10/10] Testing Batch Operations & Undo/Redo History...")
        await self.run_test("batch_operations_atomic", "Batch", self._test_batch_operations)
        await self.run_test("undo_and_redo_history", "Batch", self._test_undo_redo)
        await self.run_test("project_diffing", "Batch", self._test_diffing)

    # --- Test Implementations ---

    async def _test_doctor(self) -> None:
        raw = await self.tools["synfig_doctor"]()
        data = parse_payload(raw)
        assert data.get("found") is True, f"Doctor did not find synfig: {data}"
        assert data.get("healthy") is True

    async def _test_version(self) -> None:
        raw = await self.tools["synfig_version"]()
        data = parse_payload(raw)
        assert "version" in data and "synfig" in data["version"].lower()

    async def _test_render_targets(self) -> None:
        raw = await self.tools["list_render_targets"]()
        data = parse_payload(raw)
        assert "targets" in data and len(data["targets"]) > 0

    async def _test_layer_types(self) -> None:
        raw = await self.tools["list_layer_types"]()
        data = parse_payload(raw)
        assert "layer_types" in data and len(data["layer_types"]) > 10

    async def _test_create_project(self) -> None:
        raw = await self.tools["create_project"](
            name="proj1", width=640, height=360, fps=24.0, begin_time="0f", end_time="2s"
        )
        data = parse_payload(raw)
        assert "project_id" in data
        self.p1_id = data["project_id"]

    async def _test_canvas_props(self) -> None:
        raw = await self.tools["set_canvas_properties"](
            project_id=self.p1_id,
            width=800,
            height=600,
            background="#112233",
        )
        data = parse_payload(raw)
        assert data["canvas"]["width"] == 800

    async def _test_fps_time_range(self) -> None:
        await self.tools["set_fps"](project_id=self.p1_id, fps=30.0)
        await self.tools["set_time_range"](project_id=self.p1_id, begin_time="0f", end_time="3s 0f")
        info = parse_payload(await self.tools["get_project_info"](project_id=self.p1_id))
        assert info["fps"] == 30.0

    async def _test_sif_roundtrip(self) -> None:
        save_raw = await self.tools["save_project_as"](
            project_id=self.p1_id, path="roundtrip.sif"
        )
        s_data = parse_payload(save_raw)
        assert s_data["format"] == "sif"
        open_raw = await self.tools["open_project"](path="roundtrip.sif")
        o_data = parse_payload(open_raw)
        assert o_data["info"]["name"] == "proj1"

    async def _test_sifz_roundtrip(self) -> None:
        save_raw = await self.tools["save_project_as"](
            project_id=self.p1_id, path="roundtrip.sifz"
        )
        s_data = parse_payload(save_raw)
        assert s_data["format"] == "sifz"
        open_raw = await self.tools["open_project"](path="roundtrip.sifz")
        o_data = parse_payload(open_raw)
        assert o_data["info"]["name"] == "proj1"

    async def _test_sfg_roundtrip(self) -> None:
        save_raw = await self.tools["save_project_as"](
            project_id=self.p1_id, path="roundtrip.sfg"
        )
        s_data = parse_payload(save_raw)
        assert s_data["format"] == "sfg"
        open_raw = await self.tools["open_project"](path="roundtrip.sfg")
        o_data = parse_payload(open_raw)
        assert o_data["info"]["name"] == "proj1"

    async def _test_duplicate(self) -> None:
        raw = await self.tools["duplicate_project"](
            project_id=self.p1_id, new_name="proj1_copy"
        )
        data = parse_payload(raw)
        assert data["info"]["name"] == "proj1_copy"

    async def _test_validate(self) -> None:
        raw = await self.tools["validate_project"](project_id=self.p1_id)
        data = parse_payload(raw)
        assert data["valid"] is True

    async def _test_layers_add_list(self) -> None:
        raw = await self.tools["add_layer"](
            project_id=self.p1_id, layer_type="circle", name="MyCircle"
        )
        parse_payload(raw)
        list_raw = await self.tools["list_layers"](project_id=self.p1_id)
        layers = parse_payload(list_raw)["layers"]
        assert any(
            item["name"] == "MyCircle" or item.get("desc") == "MyCircle" for item in layers
        )

    async def _test_layer_params(self) -> None:
        await self.tools["set_layer_param"](
            project_id=self.p1_id, layer=0, param="radius", value=1.5
        )
        get_raw = await self.tools["get_layer_param"](
            project_id=self.p1_id, layer=0, param="radius"
        )
        data = parse_payload(get_raw)
        val = data["param"]["value"]
        assert abs(float(val) - 1.5) < 1e-4

    async def _test_layer_blend_amount(self) -> None:
        await self.tools["set_amount"](project_id=self.p1_id, layer=0, amount=0.75)
        await self.tools["set_blend_method"](project_id=self.p1_id, layer=0, blend_method="multiply")
        info = parse_payload(await self.tools["get_layer"](project_id=self.p1_id, layer=0))["layer"]
        assert info["amount"] == 0.75

    async def _test_layer_reorder(self) -> None:
        await self.tools["add_layer"](project_id=self.p1_id, layer_type="rectangle", name="MyRect")
        await self.tools["set_z_depth"](project_id=self.p1_id, layer=1, z_depth=2.0)
        await self.tools["move_layer"](project_id=self.p1_id, layer=1, index=0)

    async def _test_layer_enable_disable(self) -> None:
        await self.tools["disable_layer"](project_id=self.p1_id, layer=0)
        info1 = parse_payload(await self.tools["get_layer"](project_id=self.p1_id, layer=0))["layer"]
        assert info1["active"] is False
        await self.tools["enable_layer"](project_id=self.p1_id, layer=0)
        info2 = parse_payload(await self.tools["get_layer"](project_id=self.p1_id, layer=0))["layer"]
        assert info2["active"] is True

    async def _test_layer_grouping(self) -> None:
        grp = parse_payload(
            await self.tools["group_layers"](
                project_id=self.p1_id, layers=[0], name="TestGroup"
            )
        )
        assert "group" in grp
        ungrp = parse_payload(
            await self.tools["ungroup_layers"](project_id=self.p1_id, layer="TestGroup")
        )
        assert ungrp.get("ungrouped", 0) >= 1

    async def _test_primitives(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="shapes_test"))["project_id"]
        self.shape_pid = p
        await self.tools["add_circle"](project_id=p, center=[0.0, 0.0], radius=1.0, color="#ff0000")
        await self.tools["add_rectangle"](project_id=p, point1=[-1, 1], point2=[1, -1], color="#00ff00")
        await self.tools["add_polygon"](
            project_id=p, vertices=[[0, 1], [1, -1], [-1, -1]], color="#0000ff"
        )

    async def _test_star_and_text(self) -> None:
        p = self.shape_pid
        await self.tools["add_star"](project_id=p, radius1=1.0, radius2=0.5, points=5, color="#ffff00")
        await self.tools["add_text"](project_id=p, text="Synfig MCP Test", origin=[0, 2], size=0.5)

    async def _test_bline_and_outlines(self) -> None:
        p = self.shape_pid
        vertices = [[-1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
        await self.tools["add_bline"](project_id=p, id="curve1", vertices=vertices, loop=False)
        await self.tools["add_outline"](project_id=p, bline_id="curve1", width=0.1, color="#333333")
        await self.tools["add_advanced_outline"](project_id=p, bline_id="curve1", width=0.15)
        await self.tools["add_region"](project_id=p, bline_id="curve1", color="#990099")

    async def _test_gradients_and_patterns(self) -> None:
        p = self.shape_pid
        await self.tools["add_solid_color"](project_id=p, color="#abcdef")
        await self.tools["add_checkerboard"](project_id=p, color="#ffffff")
        await self.tools["add_gradient"](
            project_id=p,
            kind="linear",
            stops=[{"pos": 0.0, "color": "#000000"}, {"pos": 1.0, "color": "#ffffff"}],
        )
        await self.tools["add_noise_gradient"](project_id=p)

    async def _test_blurs(self) -> None:
        p = self.shape_pid
        await self.tools["add_blur"](project_id=p, size=[0.2, 0.2])
        await self.tools["add_motion_blur"](project_id=p)
        await self.tools["add_radial_blur"](project_id=p)

    async def _test_color_filters(self) -> None:
        p = self.shape_pid
        await self.tools["add_color_correct"](project_id=p, brightness=0.1, contrast=1.2)
        await self.tools["add_halftone"](project_id=p, size=0.1)
        await self.tools["add_clamp"](project_id=p)

    async def _test_transforms(self) -> None:
        p = self.shape_pid
        await self.tools["add_translate"](project_id=p, offset=[0.5, 0.5])
        await self.tools["add_rotate"](project_id=p, angle=45.0)
        await self.tools["add_zoom"](project_id=p, amount=1.2)
        await self.tools["add_stretch"](project_id=p, amount=[1.1, 0.9])
        await self.tools["add_twirl"](project_id=p, radius=1.0)

    async def _test_bevel_shade(self) -> None:
        p = self.shape_pid
        await self.tools["add_bevel"](project_id=p)
        await self.tools["add_shade"](project_id=p)

    async def _test_waypoints(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="anim_test"))["project_id"]
        self.anim_pid = p
        await self.tools["add_circle"](project_id=p, center=[0, 0], radius=1.0)
        wps = [
            {"time": "0f", "value": [-2.0, 0.0], "interpolation": "clamped"},
            {"time": "12f", "value": [0.0, 2.0], "interpolation": "tcb"},
            {"time": "24f", "value": [2.0, 0.0], "interpolation": "linear"},
        ]
        await self.tools["animate_param"](project_id=p, layer=0, param="origin", waypoints=wps)
        await self.tools["add_waypoint"](
            project_id=p, layer=0, param="origin", time="36f", value=[0.0, -2.0]
        )
        await self.tools["set_interpolation"](
            project_id=p, layer=0, param="origin", time="36f", interpolation="ease"
        )
        await self.tools["remove_waypoint"](project_id=p, layer=0, param="origin", time="36f")

    async def _test_keyframes(self) -> None:
        p = self.anim_pid
        await self.tools["add_keyframe"](project_id=p, time="12f", label="Peak")
        kfs = parse_payload(await self.tools["list_keyframes"](project_id=p))["keyframes"]
        assert len(kfs) >= 1
        await self.tools["move_keyframe"](project_id=p, from_time="12f", to_time="14f")
        await self.tools["remove_keyframe"](project_id=p, time="14f")

    async def _test_time_loop_offset(self) -> None:
        p = self.anim_pid
        await self.tools["set_time_loop"](
            project_id=p, link_time="0f", duration="24f"
        )
        # Group circle layer and add time offset on the group layer
        await self.tools["group_layers"](project_id=p, layers=[0], name="TimeOffsetGroup")
        await self.tools["add_time_offset"](project_id=p, layer="TimeOffsetGroup", time_offset="5f")

    async def _test_bake(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="bake_test"))["project_id"]
        await self.tools["add_circle"](project_id=p, center=[0, 0], radius=1.0)
        await self.tools["animate_param"](
            project_id=p,
            layer=0,
            param="origin",
            waypoints=[{"time": "0f", "value": [0, 0]}, {"time": "24f", "value": [2, 2]}],
        )
        baked = parse_payload(
            await self.tools["bake_animation"](
                project_id=p, layer=0, param="origin", begin_time="0f", end_time="24f", step_frames=2
            )
        )
        assert baked.get("waypoints_created", 0) > 0

    async def _test_bones(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="bones_test"))["project_id"]
        await self.tools["add_circle"](project_id=p, center=[0, 0], radius=1.0)
        await self.tools["create_bone"](
            project_id=p, name="RootBone", origin=[0, 0], length=1.5, angle=90.0
        )
        await self.tools["create_bone"](
            project_id=p, name="ArmBone", parent="RootBone", length=1.0, angle=45.0
        )
        bones = parse_payload(await self.tools["list_bones"](project_id=p))["bones"]
        assert len(bones) == 2
        await self.tools["bind_skeleton"](project_id=p, layer=0, param="origin", bones=["RootBone"])

    async def _test_export_and_link(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="link_test"))["project_id"]
        await self.tools["add_circle"](project_id=p, center=[0, 0], radius=1.0)
        await self.tools["add_rectangle"](project_id=p, point1=[-1, 1], point2=[1, -1])
        await self.tools["export_value"](
            project_id=p, layer=0, param="radius", export_name="SharedRadius"
        )
        exported = parse_payload(await self.tools["list_exported_values"](project_id=p))
        assert "SharedRadius" in [e["id"] for e in exported.get("exported", [])]
        await self.tools["link_params"](
            project_id=p,
            target_layer=1,
            target_param="point1",
            source_layer=0,
            source_param="origin",
        )
        await self.tools["unlink_params"](project_id=p, layer=1, param="point1")

    async def _test_asset_pipeline(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="asset_test"))["project_id"]
        img_path = self.tmp_dir / "sample.png"
        tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff"
            b"?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        img_path.write_bytes(tiny_png)
        await self.tools["import_asset"](path="sample.png")
        assets = parse_payload(await self.tools["list_assets"]())["assets"]
        assert len(assets) >= 1
        await self.tools["embed_image"](project_id=p, image_path="sample.png")

    async def _test_render_frame(self) -> None:
        p = parse_payload(
            await self.tools["create_project"](name="render_test", width=320, height=240, end_time="1s")
        )["project_id"]
        self.render_pid = p
        await self.tools["add_circle"](project_id=p, center=[0, 0], radius=1.0, color="#e94560")
        res = await self.tools["render_frame"](
            project_id=p, output="frame_test.png", width=320, height=240, time="0f"
        )
        data = parse_payload(res)
        out_path = Path(data["output"])
        assert out_path.exists(), f"Rendered frame not found at {out_path}"
        assert out_path.stat().st_size > 50, f"File size too small: {out_path.stat().st_size}"

    async def _test_render_preview_thumb(self) -> None:
        p = self.render_pid
        prev_res = await self.tools["render_preview"](project_id=p, width=160)
        p_data = parse_payload(prev_res)
        assert Path(p_data["output"]).exists()
        thumb_res = await self.tools["render_thumbnail"](project_id=p, size=128)
        t_data = parse_payload(thumb_res)
        assert Path(t_data["output"]).exists()

    async def _test_render_gif(self) -> None:
        p = self.render_pid
        res = await self.tools["render_animation"](
            project_id=p,
            target="gif",
            output="anim_test.gif",
            width=160,
            height=120,
            begin_time="0f",
            end_time="12f",
            fps=12.0,
        )
        data = parse_payload(res)
        out_path = Path(data["output"])
        assert out_path.exists(), f"Rendered GIF not found at {out_path}"
        assert out_path.stat().st_size > 100

    async def _test_render_status(self) -> None:
        status_raw = await self.tools["get_render_status"]()
        status_data = parse_payload(status_raw)
        assert "jobs" in status_data
        assert len(status_data["jobs"]) >= 1

    async def _test_batch_operations(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="batch_test"))["project_id"]
        ops = [
            {"tool": "add_circle", "arguments": {"radius": 0.5}},
            {"tool": "add_rectangle", "arguments": {"point1": [-1, 1], "point2": [1, -1]}},
            {"tool": "set_amount", "arguments": {"layer": 0, "amount": 0.8}},
        ]
        res = parse_payload(await self.tools["batch_operations"](project_id=p, operations=ops))
        assert res.get("operations_run") == 3
        assert res.get("rolled_back") is False

    async def _test_undo_redo(self) -> None:
        p = parse_payload(await self.tools["create_project"](name="history_test"))["project_id"]
        await self.tools["add_circle"](project_id=p, radius=1.0)
        assert len(parse_payload(await self.tools["list_layers"](project_id=p))["layers"]) == 1
        await self.tools["undo"](project_id=p)
        assert len(parse_payload(await self.tools["list_layers"](project_id=p))["layers"]) == 0
        await self.tools["redo"](project_id=p)
        assert len(parse_payload(await self.tools["list_layers"](project_id=p))["layers"]) == 1

    async def _test_diffing(self) -> None:
        p1 = parse_payload(await self.tools["create_project"](name="diff1"))["project_id"]
        p2 = parse_payload(await self.tools["duplicate_project"](project_id=p1, new_name="diff2"))[
            "project_id"
        ]
        await self.tools["add_circle"](project_id=p2, radius=2.0)
        diff = parse_payload(await self.tools["diff_projects"](a=p1, b=p2))
        assert diff.get("summary", {}).get("added") == 1

    def compute_score_and_report(self) -> dict[str, Any]:
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        categories: dict[str, list[TestResult]] = {}
        for r in self.results:
            categories.setdefault(r.category, []).append(r)

        cat_scores: dict[str, dict[str, Any]] = {}
        for cat, items in categories.items():
            p = sum(1 for i in items if i.passed)
            total = len(items)
            pct = (p / total) * 100.0 if total else 0.0
            avg_ms = sum(i.duration_ms for i in items) / total if total else 0.0
            cat_scores[cat] = {
                "passed": p,
                "total": total,
                "score_pct": pct,
                "avg_ms": avg_ms,
            }

        overall_score = (passed_tests / total_tests) * 100.0 if total_tests else 0.0

        if overall_score >= 95.0:
            rank = "S+ (Production Grade - Full Compatibility)"
        elif overall_score >= 90.0:
            rank = "S (Enterprise Grade - Highly Capable)"
        elif overall_score >= 80.0:
            rank = "A (Feature-Rich - Production Ready)"
        elif overall_score >= 70.0:
            rank = "B (Functional - Minor Gaps)"
        else:
            rank = "C (Experimental - Needs Work)"

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "overall_score": overall_score,
            "rank": rank,
            "categories": cat_scores,
        }

    def print_summary(self, report: dict[str, Any]) -> None:
        print("\n" + "=" * 65)
        print("                 BENCHMARK SCORECARD REPORT              ")
        print("=" * 65)
        print(f" Total Features Tested : {report['total']}")
        print(f" Passed                : {report['passed']}")
        print(f" Failed                : {report['failed']}")
        print(f" Overall Score         : {report['overall_score']:.1f} / 100.0")
        print(f" Capability Rank       : {report['rank']}")
        print("-" * 65)
        print(f"{'Category':<16} | {'Passed':<8} | {'Total':<6} | {'Score %':<8} | {'Avg Latency'}")
        print("-" * 65)
        for cat, stats in report["categories"].items():
            print(
                f"{cat:<16} | {stats['passed']:<8} | {stats['total']:<6} | "
                f"{stats['score_pct']:>6.1f}%  | {stats['avg_ms']:.1f}ms"
            )
        print("=" * 65)

    def write_markdown_report(self, report: dict[str, Any], dest: Path) -> None:
        md = [
            "# Synfig MCP Feature Capability & Benchmark Report",
            "",
            f"> Evaluated against: **Synfig Studio 1.5.5** on `{sys.platform}`",
            "",
            "## Executive Summary",
            "",
            f"- **Overall Score**: `{report['overall_score']:.1f} / 100.0`",
            f"- **Rank**: **{report['rank']}**",
            f"- **Features Tested**: `{report['total']}`",
            f"- **Passing Rate**: `{report['passed']} / {report['total']}` ({report['overall_score']:.1f}%)",
            "",
            "## Capability Score Breakdown by Category",
            "",
            "| Category | Passed | Total | Score | Avg Latency |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]

        for cat, stats in report["categories"].items():
            md.append(
                f"| **{cat}** | {stats['passed']} | {stats['total']} | {stats['score_pct']:.1f}% | {stats['avg_ms']:.1f}ms |"
            )

        md.append("")
        md.append("## Detailed Feature Test Breakdown")
        md.append("")
        md.append("| Test Name | Category | Status | Latency | Message |")
        md.append("| :--- | :--- | :---: | :---: | :--- |")

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            msg = r.message if r.message else "OK"
            md.append(f"| `{r.name}` | {r.category} | **{status}** | {r.duration_ms:.1f}ms | {msg} |")

        md.append("")
        md.append("---")
        md.append("*Report generated automatically by `scripts/benchmark.py`.*")

        dest.write_text("\n".join(md), encoding="utf-8")
        print(f"\nSaved detailed Markdown report to: {dest}")


async def main() -> None:
    runner = BenchmarkRunner()
    try:
        await runner.execute_all()
        report = runner.compute_score_and_report()
        runner.print_summary(report)
        report_path = Path(__file__).resolve().parent.parent / "docs" / "benchmark_report.md"
        runner.write_markdown_report(report, report_path)
    finally:
        runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
