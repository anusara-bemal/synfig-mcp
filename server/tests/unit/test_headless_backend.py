"""
Comprehensive unit tests for HeadlessBackend pure-Python engine.
"""

import tempfile
from pathlib import Path

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.protocol.models import ColorValue, RealValue, VectorValue


@pytest.fixture
def backend() -> HeadlessBackend:
    return HeadlessBackend()


@pytest.mark.asyncio
async def test_headless_health_check(
    backend: HeadlessBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("synfig_mcp.backend.headless.is_studio_running", lambda *_, **__: False)
    health = await backend.health_check()
    assert health.backend == "headless"
    assert health.connected is True
    assert health.studio_running is False
    assert health.details["engine"] == "lxml_sif_dom"
    assert health.details["studio_process_detected"] is False
    assert "warning" not in health.details


@pytest.mark.asyncio
async def test_headless_health_warns_when_studio_is_open(
    backend: HeadlessBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("synfig_mcp.backend.headless.is_studio_running", lambda *_, **__: True)
    health = await backend.health_check()
    assert health.backend == "headless"
    assert health.studio_running is True
    assert health.details["studio_process_detected"] is True
    assert "off-screen" in health.details["warning"]
    assert "MCP Bridge" in health.details["warning"]


@pytest.mark.asyncio
async def test_headless_doc_lifecycle(backend: HeadlessBackend) -> None:
    # 1. doc_new
    doc = await backend.doc_new(width=1280, height=720, fps=30.0)
    assert doc.width == 1280
    assert doc.height == 720
    assert doc.fps == 30.0

    # 2. doc_list
    docs = await backend.doc_list()
    assert len(docs) == 1
    assert docs[0].id == doc.id

    # 3. doc_set_properties
    updated = await backend.doc_set_properties(
        doc_id=doc.id,
        name="Renamed Canvas",
        width=1920,
        height=1080,
        fps=60.0,
        start_time=1.0,
        end_time=10.0,
    )
    assert updated.name == "Renamed Canvas"
    assert updated.width == 1920
    assert updated.height == 1080
    assert updated.fps == 60.0
    assert updated.start_time == 1.0
    assert updated.end_time == 10.0

    # 4. doc_save and doc_open
    with tempfile.TemporaryDirectory() as tmp_dir:
        save_path = Path(tmp_dir) / "saved_project.sifz"
        saved_file = await backend.doc_save(doc.id, str(save_path))
        assert Path(saved_file).is_file()

        opened_doc = await backend.doc_open(saved_file)
        assert opened_doc.name == "Renamed Canvas"
        assert opened_doc.width == 1920

    # 5. doc_close
    assert await backend.doc_close(doc.id) is True
    assert len(await backend.doc_list()) == 1  # only opened_doc remains
    assert await backend.doc_close(opened_doc.id) is True
    assert len(await backend.doc_list()) == 0


@pytest.mark.asyncio
async def test_headless_layer_crud_and_scene_tree(backend: HeadlessBackend) -> None:
    doc = await backend.doc_new(1920, 1080, 24.0)

    # 1. Add layers
    circle = await backend.layer_add(doc.id, "circle")
    assert circle["layer_type"] == "circle"
    circle_id = circle["layer_id"]

    rect = await backend.layer_add(doc.id, "rectangle")
    assert rect["layer_type"] == "rectangle"
    rect_id = rect["layer_id"]

    star = await backend.layer_add(doc.id, "star")
    assert star["layer_type"] == "star"
    star_id = star["layer_id"]

    # 2. Scene tree inspection
    tree = await backend.scene_tree(doc.id)
    assert len(tree["layers"]) == 3
    # Topmost is star (last added), bottom is circle
    assert tree["layers"][0]["id"] == star_id
    assert tree["layers"][2]["id"] == circle_id

    # 3. Duplicate layer
    dup = await backend.layer_duplicate(doc.id, circle_id)
    assert dup["layer_type"] == "circle"
    tree_after_dup = await backend.scene_tree(doc.id)
    assert len(tree_after_dup["layers"]) == 4

    # 4. Reorder layer
    assert await backend.layer_reorder(doc.id, circle_id, new_depth=0) is True
    tree_after_reorder = await backend.scene_tree(doc.id)
    assert tree_after_reorder["layers"][0]["id"] == circle_id

    # 5. Raise / Lower
    assert await backend.layer_lower(doc.id, circle_id) is True
    tree_after_lower = await backend.scene_tree(doc.id)
    assert tree_after_lower["layers"][1]["id"] == circle_id

    assert await backend.layer_raise(doc.id, circle_id) is True
    tree_after_raise = await backend.scene_tree(doc.id)
    assert tree_after_raise["layers"][0]["id"] == circle_id

    # 6. Group layers into PasteCanvas
    group = await backend.layer_group(doc.id, [rect_id, star_id], group_name="MyGroup")
    assert group["group_id"] == "MyGroup"
    tree_after_group = await backend.scene_tree(doc.id)
    group_node = next(node for node in tree_after_group["layers"] if node["id"] == "MyGroup")
    assert "children" in group_node
    assert len(group_node["children"]) == 2

    # 7. Ungroup layers
    released = await backend.layer_ungroup(doc.id, "MyGroup")
    assert rect_id in released or "Rectangle001" in released
    tree_after_ungroup = await backend.scene_tree(doc.id)
    assert not any(node["id"] == "MyGroup" for node in tree_after_ungroup["layers"])

    # 8. Remove layer
    assert await backend.layer_remove(doc.id, circle_id) is True
    tree_after_remove = await backend.scene_tree(doc.id)
    assert not any(node["id"] == circle_id for node in tree_after_remove["layers"])


@pytest.mark.asyncio
async def test_headless_parameter_get_and_set(backend: HeadlessBackend) -> None:
    doc = await backend.doc_new()
    layer = await backend.layer_add(doc.id, "circle")
    layer_id = layer["layer_id"]

    # 1. Get default radius
    radius_val = await backend.param_get(doc.id, layer_id, "radius")
    assert radius_val is not None
    assert isinstance(radius_val, RealValue)
    assert abs(radius_val.value - 1.0) < 1e-4

    # 2. Set radius
    new_radius = RealValue(value=3.75)
    res = await backend.param_set(doc.id, layer_id, "radius", new_radius)
    assert res["after"]["value"] == 3.75

    updated_val = await backend.param_get(doc.id, layer_id, "radius")
    assert updated_val is not None
    assert isinstance(updated_val, RealValue)
    assert abs(updated_val.value - 3.75) < 1e-4

    # 3. Set color parameter
    new_color = ColorValue(r=1.0, g=0.5, b=0.2, a=0.8)
    await backend.param_set(doc.id, layer_id, "color", new_color)
    color_val = await backend.param_get(doc.id, layer_id, "color")
    assert color_val is not None
    assert isinstance(color_val, ColorValue)
    assert abs(color_val.r - 1.0) < 1e-4
    assert abs(color_val.g - 0.5) < 1e-4

    # 4. Set origin vector parameter
    new_origin = VectorValue(x=2.5, y=-1.5)
    await backend.param_set(doc.id, layer_id, "origin", new_origin)
    origin_val = await backend.param_get(doc.id, layer_id, "origin")
    assert origin_val is not None
    assert isinstance(origin_val, VectorValue)
    assert abs(origin_val.x - 2.5) < 1e-4
    assert abs(origin_val.y - -1.5) < 1e-4


@pytest.mark.asyncio
async def test_headless_animation_and_keyframes(backend: HeadlessBackend) -> None:
    doc = await backend.doc_new()

    # Timeline cursor
    assert await backend.anim_time_get(doc.id) == 0.0
    await backend.anim_time_set(doc.id, 2.5)
    assert await backend.anim_time_get(doc.id) == 2.5

    # Keyframes
    assert len(await backend.anim_keyframe_list(doc.id)) == 0

    kf1 = await backend.anim_keyframe_add(doc.id, time=0.0, description="Start")
    assert kf1["time"] == 0.0
    assert kf1["description"] == "Start"

    kf2 = await backend.anim_keyframe_add(doc.id, time=1.5, description="Middle")
    assert kf2["time"] == 1.5

    keyframes = await backend.anim_keyframe_list(doc.id)
    assert len(keyframes) == 2
    assert keyframes[0]["description"] == "Start"
    assert keyframes[1]["description"] == "Middle"

    # Remove keyframe
    assert await backend.anim_keyframe_remove(doc.id, time=0.0) is True
    keyframes_after = await backend.anim_keyframe_list(doc.id)
    assert len(keyframes_after) == 1
    assert keyframes_after[0]["description"] == "Middle"


@pytest.mark.asyncio
async def test_headless_undo_redo(backend: HeadlessBackend) -> None:
    doc = await backend.doc_new()

    # Initial state: 0 layers
    tree0 = await backend.scene_tree(doc.id)
    assert len(tree0["layers"]) == 0

    # Action 1: Add circle
    await backend.layer_add(doc.id, "circle")
    tree1 = await backend.scene_tree(doc.id)
    assert len(tree1["layers"]) == 1

    # Action 2: Add rectangle
    await backend.layer_add(doc.id, "rectangle")
    tree2 = await backend.scene_tree(doc.id)
    assert len(tree2["layers"]) == 2

    # Undo Action 2
    assert await backend.undo(doc.id) is True
    tree_undone = await backend.scene_tree(doc.id)
    assert len(tree_undone["layers"]) == 1

    # Undo Action 1
    assert await backend.undo(doc.id) is True
    tree_undone2 = await backend.scene_tree(doc.id)
    assert len(tree_undone2["layers"]) == 0

    # No more undos
    assert await backend.undo(doc.id) is False

    # Redo Action 1
    assert await backend.redo(doc.id) is True
    tree_redone = await backend.scene_tree(doc.id)
    assert len(tree_redone["layers"]) == 1

    # Redo Action 2
    assert await backend.redo(doc.id) is True
    tree_redone2 = await backend.scene_tree(doc.id)
    assert len(tree_redone2["layers"]) == 2

    # No more redos
    assert await backend.redo(doc.id) is False

    # History summary
    history = await backend.history_list(doc.id)
    assert history["undo_count"] >= 2
    assert history["redo_count"] == 0


@pytest.mark.asyncio
async def test_headless_render_frame(backend: HeadlessBackend) -> None:
    if not backend.runner.is_available:
        pytest.skip("synfig binary not available on this system")

    doc = await backend.doc_new(width=100, height=100)
    await backend.layer_add(doc.id, "circle")

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_png = Path(tmp_dir) / "render.png"
        success = await backend.render_frame(doc.id, str(out_png), time=0.0, width=100, height=100)
        assert success is True
        assert out_png.is_file()
        assert out_png.stat().st_size > 0
