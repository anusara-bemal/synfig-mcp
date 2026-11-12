"""
Unit tests for the anime production pipeline (Steps 0-5).

These run against the headless backend and never touch the network, so they are
part of the default ``poe test`` gate.  The contract tests in
``tests/contract/test_sif_synfig_validity.py`` cover the real-engine gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.errors import SynfigError
from synfig_mcp.production import (
    AnimeProductionPipeline,
    AssetRequest,
    CharacterDescriptor,
    ProductionBrief,
)
from synfig_mcp.production.asset_generator import AssetGenerator
from synfig_mcp.production.character_builder import CharacterBuilder
from synfig_mcp.production.models import RenderOptions
from synfig_mcp.production.palette import parse_color, shift
from synfig_mcp.production.rig_sheet import RigSheetGenerator
from synfig_mcp.production.slicer import PartSlicer

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------


def test_parse_color_linearises_and_reads_alpha() -> None:
    white = parse_color("#ffffff")
    assert white["r"] == pytest.approx(1.0)
    assert white["a"] == 1.0
    half = parse_color("#ff000080")
    assert half["g"] == 0.0
    assert half["a"] == pytest.approx(128 / 255, abs=1e-6)


def test_parse_color_rejects_bad_input() -> None:
    with pytest.raises(SynfigError):
        parse_color("not-a-colour")


def test_shift_clamps_to_unit_range() -> None:
    colour = {"type": "color", "r": 0.9, "g": 0.5, "b": 0.1, "a": 1.0}
    lighter = shift(colour, 0.5)
    assert lighter["r"] == 1.0
    assert lighter["b"] == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# Asset generator
# ---------------------------------------------------------------------------


def test_every_generator_produces_typed_layers() -> None:
    generator = AssetGenerator(style="shonen_action")
    frame = (-5.3, 3.0, 5.3, -3.0)
    for name in AssetGenerator.background_generators():
        layers = generator.background(name, frame, seed=1)
        assert layers and all({"id", "type", "params"} <= set(layer) for layer in layers)
    for name in AssetGenerator.prop_generators():
        assert generator.prop(name, (0.0, 0.0), 1.0, seed=1)
    for name in AssetGenerator.texture_generators():
        assert generator.texture(name, frame, seed=1)


def test_generation_is_seeded_and_reproducible() -> None:
    generator = AssetGenerator(style="dark_fantasy")
    frame = (-5.3, 3.0, 5.3, -3.0)
    assert generator.background("starfield", frame, seed=5) == generator.background(
        "starfield", frame, seed=5
    )
    assert generator.background("starfield", frame, seed=5) != generator.background(
        "starfield", frame, seed=6
    )


def test_unknown_generator_raises() -> None:
    generator = AssetGenerator()
    with pytest.raises(ValueError):
        generator.background("nope", (0.0, 0.0, 1.0, 1.0))


# ---------------------------------------------------------------------------
# Character builder
# ---------------------------------------------------------------------------


def test_humanoid_and_chibi_expand_to_riggable_parts() -> None:
    builder = CharacterBuilder(style_palette=["#112233", "#445566", "#778899", "#aabbcc"])
    for archetype in ("humanoid", "chibi"):
        parts = builder.expand(CharacterDescriptor(id="hero", archetype=archetype))
        names = [part.id for part in parts]
        assert "torso" in names and "head" in names
        assert len(parts) == len(set(names)), "part ids must be unique"
        assert all(part.primitive_type for part in parts)


def test_descriptor_palette_overrides_style() -> None:
    builder = CharacterBuilder(style_palette=["#000000"])
    parts = builder.expand(CharacterDescriptor(id="hero", palette=["#ff0000"]))
    head = next(p for p in parts if p.id == "head")
    assert head.primitive_params["color"]["r"] == pytest.approx(1.0)


def test_invalid_palette_colour_is_rejected() -> None:
    with pytest.raises(ValueError):
        CharacterDescriptor(id="hero", palette=["zzz"])


# ---------------------------------------------------------------------------
# Asset request validation
# ---------------------------------------------------------------------------


def test_asset_request_needs_a_source() -> None:
    with pytest.raises(ValueError):
        AssetRequest(id="x")
    assert AssetRequest(id="x", procedural={"generator": "tree"})


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dry_run_reports_every_stage_without_building(tmp_path: Path) -> None:
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    brief = ProductionBrief(
        title="Dry",
        duration=2.0,
        characters=[CharacterDescriptor(id="hero")],
    )
    report = await pipeline.run(brief, dry_run=True)
    assert report.dry_run is True
    assert report.doc_id is None
    assert {s.name for s in report.stages} >= {
        "document",
        "storyboard",
        "characters",
        "assets",
        "style",
        "render",
        "review",
    }


@pytest.mark.asyncio
async def test_full_run_builds_and_saves_a_document(tmp_path: Path) -> None:
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    brief = ProductionBrief(
        title="Run It",
        width=320,
        height=180,
        duration=2.0,
        characters=[
            CharacterDescriptor(
                id="hero",
                position={"x": 80.0, "y": 170.0},
                actions=[{"motion": "walk", "start": 0.0, "end": 2.0}],
            )
        ],
    )
    report = await pipeline.run(brief)
    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]
    document = Path(report.artifacts["document"])
    assert document.is_file() and document.suffix == ".sif"


@pytest.mark.asyncio
async def test_unknown_stage_is_rejected(tmp_path: Path) -> None:
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    with pytest.raises(SynfigError):
        await pipeline.run(ProductionBrief(title="x"), stages=["nope"])


@pytest.mark.asyncio
async def test_render_options_can_disable_video(tmp_path: Path) -> None:
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    brief = ProductionBrief(title="NoVideo", render=RenderOptions(video=False))
    report = await pipeline.run(brief)
    assert report.success is True
    assert "video" not in report.artifacts


# ---------------------------------------------------------------------------
# Slicer
# ---------------------------------------------------------------------------


def _make_sheet(path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (120, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 30, 40), fill=(255, 0, 0, 255))
    draw.rectangle((70, 10, 100, 50), fill=(0, 255, 0, 255))
    image.save(path)


def test_alpha_slice_finds_both_parts(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    _make_sheet(sheet)
    result = PartSlicer(tmp_path / "parts").slice(sheet, strategy="alpha")
    assert result["detected_parts"] == 2
    for part in result["parts"]:
        assert Path(part["file"]).is_file()


def test_grid_slice_makes_rows_times_cols(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    _make_sheet(sheet)
    result = PartSlicer(tmp_path / "grid").slice(sheet, strategy="grid", rows=1, cols=3)
    assert result["detected_parts"] == 3


def test_explicit_rectangles_win(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    _make_sheet(sheet)
    result = PartSlicer(tmp_path / "rects").slice(
        sheet,
        strategy="alpha",
        rectangles=[{"name": "only", "x": 0, "y": 0, "width": 60, "height": 60}],
    )
    assert result["detected_parts"] == 1
    assert result["parts"][0]["name"] == "only"


# ---------------------------------------------------------------------------
# Rig sheet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_model_sheet_builds_three_views(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    info = await backend.doc_new(width=320, height=180, fps=24.0)
    assert tmp_path.is_dir()
    builder = CharacterBuilder(style_palette=["#112233", "#445566", "#778899", "#aabbcc"])
    parts = builder.as_cutout_parts(builder.expand(CharacterDescriptor(id="hero")))
    result = await RigSheetGenerator(backend).generate(
        character_id="hero", parts=parts, doc_id=info.id, height=140.0
    )
    assert result["success"] is True
    assert set(result["views"]) == {"front", "threequarter", "side"}
