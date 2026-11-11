"""
Contract gate: every document produced by the MCP must be loadable by the
*real* Synfig engine.

These tests are the ground truth for the headless backend.  Each case performs
a mutation through the public backend API, saves the document, and then asks
the actual ``synfig`` binary to load and render it.  A Synfig error (for
example ``Unexpected element <valuenode>``) fails the test, which is exactly
the class of defect that silently corrupted documents before.

The whole module is skipped when no Synfig binary is available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.cli.runner import CliRunner
from synfig_mcp.errors import SynfigError
from synfig_mcp.validation import ValidationResult, find_synfig_binary, validate_document


def _binary() -> Path | None:
    return find_synfig_binary()


BINARY = _binary()

pytestmark = pytest.mark.skipif(
    BINARY is None, reason="Synfig CLI binary not available for document validation"
)


async def assert_loadable(backend: HeadlessBackend, doc_id: str, tmp_path: Path) -> Path:
    """Save the document and assert the real Synfig engine loads it cleanly."""
    sif = tmp_path / "validated.sif"
    await backend.doc_save(doc_id=doc_id, file_path=str(sif))
    result: ValidationResult = await validate_document(sif, binary=BINARY)
    assert result.valid, (
        "Synfig rejected the generated document:\n"
        f"exit={result.exit_code}\n" + "\n".join(result.errors)
    )
    return sif


async def _new_doc(backend: HeadlessBackend) -> str:
    doc = await backend.doc_new(width=320, height=240, fps=24.0)
    return doc.id


# ---------------------------------------------------------------------------
# Layer creation
# ---------------------------------------------------------------------------


async def test_every_synfig_layer_type_creates_a_loadable_document(
    tmp_path: Path,
) -> None:
    """All layer types advertised by the Synfig binary must be creatable and loadable."""
    runner = CliRunner(BINARY)
    layer_types = sorted(await runner.get_layers())
    assert layer_types, "Synfig binary reported no layer types"

    backend = HeadlessBackend(runner=runner)
    doc_id = await _new_doc(backend)

    for layer_type in layer_types:
        result = await backend.layer_add(doc_id=doc_id, layer_type=layer_type, params={})
        assert result["layer_type"], f"layer_add returned no layer type for {layer_type}"

    await assert_loadable(backend, doc_id, tmp_path)


async def test_unknown_layer_type_is_rejected() -> None:
    """An unknown layer type must fail loudly instead of producing a broken document."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)

    with pytest.raises(SynfigError) as exc_info:
        await backend.layer_add(doc_id=doc_id, layer_type="definitely_not_a_layer", params={})
    assert "definitely_not_a_layer" in str(exc_info.value).lower()


async def test_created_layers_use_the_introspected_layer_version(tmp_path: Path) -> None:
    """Layer ``version`` must match the version reported by ``synfig --layer-info``."""
    runner = CliRunner(BINARY)
    backend = HeadlessBackend(runner=runner)
    doc_id = await _new_doc(backend)

    for layer_type in ("circle", "text", "switch", "noise_distort"):
        info = await runner.get_layer_info(layer_type)
        assert info is not None
        await backend.layer_add(doc_id=doc_id, layer_type=layer_type, params={})

    sif = tmp_path / "versions.sif"
    await backend.doc_save(doc_id=doc_id, file_path=str(sif))
    content = sif.read_text(encoding="utf-8")
    assert 'version="0.1"' not in content, (
        "layers are written with a hardcoded version=0.1 instead of the real version"
    )

    result = await validate_document(sif, binary=BINARY)
    assert result.valid, "\n".join(result.errors)
    assert not [w for w in result.warnings if "version" in w.lower()], (
        f"unexpected layer version warnings: {result.warnings}"
    )


# ---------------------------------------------------------------------------
# Parameter values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("param_name", "value"),
    [
        ("radius", {"type": "real", "value": 3.5}),
        ("color", {"type": "color", "r": 0.1, "g": 0.2, "b": 0.3, "a": 1.0}),
        ("origin", {"type": "vector", "x": 1.0, "y": 2.0}),
        ("feather", {"type": "real", "value": 0.5}),
        ("invert", {"type": "bool", "value": True}),
    ],
)
async def test_parameter_values_produce_loadable_documents(
    tmp_path: Path, param_name: str, value: dict[str, Any]
) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})

    await backend.param_set(
        doc_id=doc_id, layer_id=layer["layer_id"], param_name=param_name, value=value
    )

    await assert_loadable(backend, doc_id, tmp_path)


async def test_param_set_rejects_unsupported_value_types() -> None:
    """Values the engine cannot represent must fail loudly, not be stringified."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="outline", params={})

    with pytest.raises(SynfigError):
        await backend.param_set(
            doc_id=doc_id,
            layer_id=layer["layer_id"],
            param_name="bline",
            value={"type": "not_a_real_type", "value": 1},
        )


@pytest.mark.parametrize(
    ("value", "expected_x", "expected_y"),
    [
        ({"type": "vector", "x": 1.5, "y": -2.5}, 1.5, -2.5),
        ({"type": "vector", "value": {"x": 1.5, "y": -2.5}}, 1.5, -2.5),
        ([1.5, -2.5], 1.5, -2.5),
    ],
)
async def test_param_set_accepts_every_documented_vector_spelling(
    tmp_path: Path, value: Any, expected_x: float, expected_y: float
) -> None:
    """The vector spellings used in the guides must all reach the document."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})

    await backend.param_set(
        doc_id=doc_id, layer_id=layer["layer_id"], param_name="origin", value=value
    )

    read_back = await backend.param_get(
        doc_id=doc_id, layer_id=layer["layer_id"], param_name="origin"
    )
    assert read_back is not None
    assert read_back.type == "vector"
    assert abs(read_back.x - expected_x) < 1e-6
    assert abs(read_back.y - expected_y) < 1e-6

    await assert_loadable(backend, doc_id, tmp_path)


async def test_param_set_writes_a_valid_spline(tmp_path: Path) -> None:
    """Writing spline points must produce a document the engine accepts."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="outline", params={})

    await backend.param_set(
        doc_id=doc_id,
        layer_id=layer["layer_id"],
        param_name="bline",
        value={
            "type": "bline_point_list",
            "points": [
                {
                    "vertex": (-1.0, 0.0),
                    "t1": (0.0, 0.0),
                    "t2": (0.0, 0.0),
                    "width": 1.0,
                    "origin": 0.5,
                },
                {
                    "vertex": (1.0, 0.0),
                    "t1": (0.0, 0.0),
                    "t2": (0.0, 0.0),
                    "width": 1.0,
                    "origin": 0.5,
                },
            ],
        },
    )

    await assert_loadable(backend, doc_id, tmp_path)


async def test_param_export_produces_loadable_document(tmp_path: Path) -> None:
    """Exporting a parameter must yield a document Synfig can load and resolve."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(
        doc_id=doc_id, layer_type="circle", params={"radius": {"type": "real", "value": 2.0}}
    )

    await backend.param_export(
        doc_id=doc_id, layer_id=layer["layer_id"], param_name="radius", name="myRadius"
    )

    await assert_loadable(backend, doc_id, tmp_path)


async def test_param_unexport_produces_loadable_document(tmp_path: Path) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(
        doc_id=doc_id, layer_type="circle", params={"radius": {"type": "real", "value": 2.0}}
    )

    await backend.param_export(
        doc_id=doc_id, layer_id=layer["layer_id"], param_name="radius", name="myRadius"
    )
    await backend.param_unexport(doc_id=doc_id, name="myRadius")

    await assert_loadable(backend, doc_id, tmp_path)


@pytest.mark.parametrize(
    ("param_name", "value", "valuenode_type"),
    [
        ("radius", {"type": "real", "value": 2.0}, "linear"),
        ("radius", {"type": "real", "value": 2.0}, "add"),
        ("radius", {"type": "real", "value": 2.0}, "subtract"),
        ("radius", {"type": "real", "value": 2.0}, "scale"),
        ("radius", {"type": "real", "value": 2.0}, "absolute"),
        ("radius", {"type": "real", "value": 2.0}, "duplicate"),
        ("radius", {"type": "real", "value": 2.0}, "range"),
        ("radius", {"type": "real", "value": 2.0}, "step"),
        ("origin", {"type": "vector", "x": 1.0, "y": 2.0}, "composite"),
    ],
)
async def test_param_convert_produces_loadable_document(
    tmp_path: Path, param_name: str, value: dict[str, Any], valuenode_type: str
) -> None:
    """Converting a parameter to a ValueNode must produce Synfig-valid XML."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={"radius": value})

    await backend.param_convert(
        doc_id=doc_id, layer_id=layer["layer_id"], param_name=param_name, type=valuenode_type
    )

    await assert_loadable(backend, doc_id, tmp_path)


async def test_param_convert_rejects_unsupported_valuenode() -> None:
    """An unknown ValueNode type must be refused instead of writing broken XML."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})

    with pytest.raises(SynfigError):
        await backend.param_convert(
            doc_id=doc_id,
            layer_id=layer["layer_id"],
            param_name="radius",
            type="not_a_valuenode",
        )


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "interpolation", ["linear", "constant", "halt", "clamped", "auto", "manual"]
)
async def test_waypoint_interpolations_produce_loadable_documents(
    tmp_path: Path, interpolation: str
) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})

    await backend.anim_waypoint_set(
        doc_id=doc_id,
        layer_id=layer["layer_id"],
        param_name="radius",
        time=0.0,
        value={"type": "real", "value": 1.0},
        interpolation_in=interpolation,
        interpolation_out=interpolation,
    )

    await assert_loadable(backend, doc_id, tmp_path)


async def test_invalid_interpolation_is_rejected() -> None:
    """Unknown interpolation modes must be refused, not written into the document."""
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    layer = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})

    with pytest.raises(SynfigError):
        await backend.anim_waypoint_set(
            doc_id=doc_id,
            layer_id=layer["layer_id"],
            param_name="radius",
            time=0.0,
            value={"type": "real", "value": 1.0},
            interpolation_in="definitely_not_an_interpolation",
            interpolation_out="definitely_not_an_interpolation",
        )


async def test_keyframe_lifecycle_produces_loadable_document(tmp_path: Path) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})

    await backend.anim_keyframe_add(doc_id=doc_id, time=0.5, description="pose")
    await assert_loadable(backend, doc_id, tmp_path)

    await backend.anim_keyframe_remove(doc_id=doc_id, time=0.5)
    await assert_loadable(backend, doc_id, tmp_path)


async def test_group_and_ungroup_produce_loadable_documents(tmp_path: Path) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)
    first = await backend.layer_add(doc_id=doc_id, layer_type="circle", params={})
    second = await backend.layer_add(doc_id=doc_id, layer_type="rectangle", params={})

    group = await backend.layer_group(
        doc_id=doc_id, layer_ids=[first["layer_id"], second["layer_id"]], group_name="G1"
    )
    await assert_loadable(backend, doc_id, tmp_path)

    await backend.layer_ungroup(doc_id=doc_id, layer_id=group["group_id"])
    await assert_loadable(backend, doc_id, tmp_path)


async def test_scene_build_with_groups_and_waypoints_produces_loadable_document(
    tmp_path: Path,
) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)

    await backend.scene_build(
        spec={
            "doc_id": doc_id,
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
                },
                {
                    "id": "prop",
                    "type": "rectangle",
                    "depth": 1,
                    "params": {},
                },
            ],
            "groups": [{"id": "bundle", "layer_ids": ["hero", "prop"]}],
        }
    )

    sif = await assert_loadable(backend, doc_id, tmp_path)
    content = sif.read_text(encoding="utf-8")
    assert "<waypoint" in content, "scene_build dropped the requested waypoints"
    assert "bundle" in content, "scene_build dropped the requested group"


async def test_document_properties_and_time_range_produce_loadable_document(
    tmp_path: Path,
) -> None:
    backend = HeadlessBackend(runner=CliRunner(BINARY))
    doc_id = await _new_doc(backend)

    await backend.doc_set_properties(
        doc_id=doc_id,
        name="Validation Doc",
        desc="Round-trip validation",
        width=640,
        height=480,
        fps=30.0,
    )
    await backend.doc_set_time_range(doc_id=doc_id, start_time=0.0, end_time=2.0, fps=30.0)

    await assert_loadable(backend, doc_id, tmp_path)
