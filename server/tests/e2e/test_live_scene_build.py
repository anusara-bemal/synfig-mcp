"""
Live verification of the declarative ``scene.build`` path.

The bridge must honour *every* part of a scene specification: the layers, their
parameters, their waypoints and the requested groups.  Before the hardening pass
the C++ handler silently ignored waypoints and groups, so a live build produced
a different document than the same build in headless mode.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from synfig_mcp.errors import SynfigError
from synfig_mcp.protocol.client import BridgeClient


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_scene_build_applies_waypoints(live_studio: BridgeClient) -> None:
    """Waypoints in a scene spec must reach the Studio timeline."""
    spec = {
        "doc_id": "doc_0",
        "layers": [
            {
                "id": "hero",
                "type": "circle",
                "depth": 0,
                "params": {"radius": {"type": "real", "value": 2.0}},
                "waypoints": [
                    {
                        "param": "radius",
                        "time": 0.0,
                        "value": {"type": "real", "value": 1.0},
                        "interpolation": "linear",
                    },
                    {
                        "param": "radius",
                        "time": 1.0,
                        "value": {"type": "real", "value": 3.0},
                        "interpolation": "linear",
                    },
                ],
            }
        ],
    }

    result = await live_studio.call("scene.build", spec)
    assert "diff" in result
    assert "hero" in result["diff"]["created"]

    tree = await live_studio.call("scene.tree", {"doc_id": "doc_0"})
    layers = tree.get("layers", [])
    assert layers, "scene.build did not create a layer"

    hero = next((layer for layer in layers if layer.get("desc") == "hero"), None)
    assert hero is not None, f"layer 'hero' missing from the scene tree: {layers}"

    # The waypoints must be visible as an animated parameter: reading the
    # parameter at two different times has to yield the two waypoint values.
    await live_studio.call("anim.time.set", {"doc_id": "doc_0", "time": 0.0})
    at_start = await live_studio.call(
        "param.get",
        {"doc_id": "doc_0", "layer_id": hero["id"], "param_name": "radius"},
    )
    await live_studio.call("anim.time.set", {"doc_id": "doc_0", "time": 1.0})
    at_end = await live_studio.call(
        "param.get",
        {"doc_id": "doc_0", "layer_id": hero["id"], "param_name": "radius"},
    )

    start_value = at_start.get("value", {}) if isinstance(at_start, dict) else {}
    end_value = at_end.get("value", {}) if isinstance(at_end, dict) else {}
    assert abs(float(start_value.get("value", 0.0)) - 1.0) < 0.01, (
        f"the first waypoint was not applied: {at_start}"
    )
    assert abs(float(end_value.get("value", 0.0)) - 3.0) < 0.01, (
        f"the second waypoint was not applied: {at_end}"
    )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_scene_build_applies_groups(live_studio: BridgeClient) -> None:
    """Groups in a scene spec must encapsulate the referenced layers."""
    spec = {
        "doc_id": "doc_0",
        "layers": [
            {"id": "part_a", "type": "circle", "depth": 0, "params": {}},
            {"id": "part_b", "type": "rectangle", "depth": 1, "params": {}},
        ],
        "groups": [{"id": "bundle", "layer_ids": ["part_a", "part_b"]}],
    }

    result = await live_studio.call("scene.build", spec)
    assert "bundle" in result["diff"]["created"], (
        f"the group was not created by scene.build: {result['diff']}"
    )

    tree = await live_studio.call("scene.tree", {"doc_id": "doc_0"})
    layers = tree.get("layers", [])
    bundle = next((layer for layer in layers if layer.get("desc") == "bundle"), None)
    assert bundle is not None, f"group 'bundle' missing from the scene tree: {layers}"
    assert bundle.get("children"), "the group does not contain the grouped layers"


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_scene_build_is_a_single_undo_step(live_studio: BridgeClient) -> None:
    """A declarative build must be undoable with a single undo."""
    spec = {
        "doc_id": "doc_0",
        "layers": [
            {"id": "undo_me", "type": "circle", "depth": 0, "params": {}},
        ],
    }
    await live_studio.call("scene.build", spec)

    tree = await live_studio.call("scene.tree", {"doc_id": "doc_0"})
    assert any(layer.get("desc") == "undo_me" for layer in tree.get("layers", []))

    await live_studio.call("history.undo", {"doc_id": "doc_0"})

    tree = await live_studio.call("scene.tree", {"doc_id": "doc_0"})
    assert not any(layer.get("desc") == "undo_me" for layer in tree.get("layers", [])), (
        "a single undo did not remove the layer created by scene.build"
    )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_scene_tree_has_the_documented_shape(live_studio: BridgeClient) -> None:
    """The live scene tree must expose the same keys as the headless engine."""
    await live_studio.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "circle"}
    )
    tree = await live_studio.call("scene.tree", {"doc_id": "doc_0"})

    for key in ("doc_id", "canvas_path", "name", "width", "height", "fps", "duration_frames"):
        assert key in tree, f"the live scene tree has no '{key}': {sorted(tree)}"

    layers = tree.get("layers", [])
    assert layers, "the live scene tree has no layers"
    for key in ("id", "desc", "description", "type", "active", "depth", "params", "children"):
        assert key in layers[0], f"a live layer entry has no '{key}': {sorted(layers[0])}"


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_value_types_match_the_python_models(live_studio: BridgeClient) -> None:
    """Every value type the bridge reports must match the documented wire format.

    The bridge used to answer with ``bline_point`` and ``canvas`` while the
    documented format (and the Python models) use ``bline_point_list`` and
    ``canvas_ref``; such a value failed model validation for MCP clients.
    """
    group = await live_studio.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "group", "description": "group"}
    )

    canvas_value = await live_studio.call(
        "param.get",
        {"doc_id": "doc_0", "layer_id": group["layer_id"], "param_name": "canvas"},
    )
    value = canvas_value.get("value", {}) if isinstance(canvas_value, dict) else {}
    assert value.get("type") == "canvas_ref", (
        f"the canvas reference does not use the documented format: {canvas_value}"
    )
    assert "canvas_id" in value, f"the canvas reference has no id: {canvas_value}"


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_gradient_parameters_round_trip(live_studio: BridgeClient) -> None:
    """Gradient parameters must be readable and writable through the bridge.

    The bridge used to answer with ``{"type": "gradient", "value": [...]}`` while
    the documented wire format and the Python model use ``cpoints``, which made
    every gradient parameter unreadable for MCP clients.
    """
    layer = await live_studio.call(
        "layer.add",
        {"doc_id": "doc_0", "layer_type": "linear_gradient", "description": "gradient"},
    )
    layer_id = layer["layer_id"]

    value = await live_studio.call(
        "param.get",
        {"doc_id": "doc_0", "layer_id": layer_id, "param_name": "gradient"},
    )
    gradient = value.get("value", {}) if isinstance(value, dict) else {}
    assert "cpoints" in gradient, f"gradient does not use the documented format: {gradient}"
    assert gradient["cpoints"], "the gradient has no color stops"

    await live_studio.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": layer_id,
            "param_name": "gradient",
            "value": {
                "type": "gradient",
                "cpoints": [
                    {"pos": 0.0, "color": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}},
                    {"pos": 1.0, "color": {"r": 0.0, "g": 0.0, "b": 1.0, "a": 1.0}},
                ],
            },
        },
    )

    updated = await live_studio.call(
        "param.get",
        {"doc_id": "doc_0", "layer_id": layer_id, "param_name": "gradient"},
    )
    stops = updated.get("value", {}).get("cpoints", []) if isinstance(updated, dict) else []
    assert stops, "the gradient lost its color stops"
    first = stops[0].get("color", {})
    assert abs(float(first.get("r", 0.0)) - 1.0) < 0.01, f"the gradient was not written: {stops}"


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_param_link_connects_a_parameter_to_an_exported_value_node(
    live_studio: BridgeClient,
) -> None:
    """A parameter must be able to follow an exported value node in Studio."""
    source = await live_studio.call(
        "layer.add",
        {"doc_id": "doc_0", "layer_type": "circle", "description": "source"},
    )
    follower = await live_studio.call(
        "layer.add",
        {"doc_id": "doc_0", "layer_type": "circle", "description": "follower"},
    )
    source_id = source["layer_id"]
    follower_id = follower["layer_id"]

    await live_studio.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": source_id,
            "param_name": "radius",
            "value": {"type": "real", "value": 2.0},
        },
    )
    await live_studio.call(
        "param.export",
        {"doc_id": "doc_0", "layer_id": source_id, "param_name": "radius", "name": "sharedRadius"},
    )
    await live_studio.call(
        "param.link",
        {
            "doc_id": "doc_0",
            "layer_id": follower_id,
            "param_name": "radius",
            "link_id": "sharedRadius",
        },
    )

    value = await live_studio.call(
        "param.get",
        {"doc_id": "doc_0", "layer_id": follower_id, "param_name": "radius"},
    )
    linked = value.get("value", {}) if isinstance(value, dict) else {}
    assert abs(float(linked.get("value", 0.0)) - 2.0) < 0.01, (
        f"the linked parameter does not follow the exported value: {value}"
    )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_param_link_rejects_an_unknown_value_node(
    live_studio: BridgeClient,
) -> None:
    """Linking to a value node that does not exist must fail."""
    layer = await live_studio.call(
        "layer.add",
        {"doc_id": "doc_0", "layer_type": "circle", "description": "lonely"},
    )
    with pytest.raises(SynfigError):
        await live_studio.call(
            "param.link",
            {
                "doc_id": "doc_0",
                "layer_id": layer["layer_id"],
                "param_name": "radius",
                "link_id": "neverExported",
            },
        )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_layer_add_rejects_invalid_parameter_values(
    live_studio: BridgeClient,
) -> None:
    """Invalid parameter values must be reported instead of being skipped."""
    with pytest.raises(SynfigError):
        await live_studio.call(
            "layer.add",
            {
                "doc_id": "doc_0",
                "layer_type": "circle",
                "params": {"radius": {"type": "not_a_type", "value": 1}},
            },
        )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_documents_saved_by_the_bridge_load_in_synfig(
    live_studio: BridgeClient, tmp_path: Path
) -> None:
    """A document saved through the bridge must be loadable by the Synfig engine."""
    from synfig_mcp.validation import find_synfig_binary, validate_document

    binary = find_synfig_binary()
    if binary is None:
        pytest.skip("Synfig CLI binary not available for validation")

    await live_studio.call(
        "scene.build",
        {
            "doc_id": "doc_0",
            "layers": [
                {"id": "saved_circle", "type": "circle", "depth": 0, "params": {}},
            ],
        },
    )

    target = tmp_path / "live_document.sif"
    await live_studio.call("doc.save", {"doc_id": "doc_0", "file_path": str(target)})
    assert target.is_file(), "the bridge did not write the document"

    result = await validate_document(target, binary=binary)
    assert result.valid, "\n".join(result.errors)
