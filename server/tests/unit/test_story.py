"""Story bible + screenplay: structural derivation, continuity validation, pipeline stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.production.models import AssetRequest, CharacterDescriptor, ProductionBrief
from synfig_mcp.production.pipeline import AnimeProductionPipeline
from synfig_mcp.production.story import (
    STORY_FILENAME,
    build_screenplay,
    compile_story,
    validate_story,
)


def _brief(**over: object) -> ProductionBrief:
    data: dict[str, object] = {
        "title": "Sky Duel",
        "style": "shonen_action",
        "width": 320,
        "height": 180,
        "duration": 4.0,
        "background": {"generator": "landscape"},
        "characters": [CharacterDescriptor(id="hero"), CharacterDescriptor(id="rival")],
        "shots": [
            {
                "shot_id": "shot_01",
                "description": "hero faces rival",
                "duration_seconds": 2.0,
                "characters_present": ["hero", "rival"],
            },
            {
                "shot_id": "shot_02",
                "description": "clash",
                "duration_seconds": 2.0,
                "characters_present": ["hero"],
                "dialogue": "En garde!",
            },
        ],
    }
    data.update(over)
    return ProductionBrief.model_validate(data)


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def test_derived_bible_is_structural_and_consistent() -> None:
    brief = _brief()
    bible = compile_story(brief)

    assert bible.authored is False
    assert [c.id for c in bible.characters] == ["hero", "rival"]
    assert bible.characters[0].role == "protagonist"
    assert bible.characters[1].role == "supporting"
    assert len(bible.scenes) == 1
    assert bible.scenes[0].shots == ["shot_01", "shot_02"]
    assert [b.label for b in bible.timeline] == ["shot_01", "shot_02"]
    assert validate_story(brief, bible) == []


def test_timeline_tracks_shot_start_times() -> None:
    bible = compile_story(_brief())
    assert [b.time for b in bible.timeline] == [0.0, 2.0]


def test_locations_and_props_are_derived_from_the_brief() -> None:
    brief = _brief(assets=[AssetRequest(id="sword", kind="prop", procedural={"generator": "rock"})])
    bible = compile_story(brief)
    assert bible.locations and bible.locations[0].id == "loc_main"
    assert [p.id for p in bible.props] == ["sword"]


def test_single_shot_brief_still_gets_a_bible() -> None:
    bible = compile_story(ProductionBrief(title="Solo", duration=2.0))
    assert len(bible.timeline) == 1
    assert bible.scenes[0].shots == ["shot_01"]


# ---------------------------------------------------------------------------
# Authored bibles are never overwritten
# ---------------------------------------------------------------------------


def test_authored_bible_passes_through_unchanged() -> None:
    base = _brief()
    authored = compile_story(base).model_copy(deep=True)
    authored.authored = True
    authored.logline = "A hand-written logline."

    brief = base.model_copy(update={"story": authored.model_dump()})
    bible = compile_story(brief)

    assert bible.authored is True
    assert bible.logline == "A hand-written logline."


def test_authored_bible_accepts_a_plain_dict() -> None:
    base = _brief()
    authored = compile_story(base)
    authored.authored = True
    brief = base.model_copy(update={"story": authored.model_dump()})
    assert compile_story(brief).authored is True


# ---------------------------------------------------------------------------
# Continuity validation
# ---------------------------------------------------------------------------


def test_unknown_character_is_reported() -> None:
    brief = _brief()
    bible = compile_story(brief).model_copy(deep=True)
    bible.characters[0].id = "ghost"
    issues = validate_story(brief, bible)
    assert any("ghost" in issue for issue in issues)
    assert any("missing" in issue for issue in issues)


def test_timeline_drift_is_reported() -> None:
    brief = _brief()
    bible = compile_story(brief).model_copy(deep=True)
    bible.timeline.pop()
    assert any("timeline" in issue for issue in validate_story(brief, bible))


def test_scene_referencing_unknown_shot_is_reported() -> None:
    brief = _brief()
    bible = compile_story(brief).model_copy(deep=True)
    bible.scenes[0].shots.append("shot_99")
    assert any("shot_99" in issue for issue in validate_story(brief, bible))


def test_duplicate_character_is_reported() -> None:
    brief = _brief()
    bible = compile_story(brief).model_copy(deep=True)
    bible.characters.append(bible.characters[0].model_copy(deep=True))
    assert any("twice" in issue for issue in validate_story(brief, bible))


def test_screenplay_view_flattens_the_bible() -> None:
    brief = _brief()
    bible = compile_story(brief)
    screenplay = build_screenplay(brief, bible)
    assert screenplay.title == "Sky Duel"
    assert screenplay.shot_count == 2
    assert screenplay.total_duration == pytest.approx(4.0)
    assert screenplay.scenes == bible.scenes


# ---------------------------------------------------------------------------
# Pipeline stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_writes_and_reports_the_bible(tmp_path: Path) -> None:
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    report = await pipeline.run(_brief())

    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]
    story = report.stage("story")
    assert story is not None and story.status == "ok"
    assert "derived from the brief" in story.detail

    path = Path(report.artifacts["story_bible"])
    assert path.is_file() and path.name == STORY_FILENAME
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["authored"] is False
    assert [c["id"] for c in written["characters"]] == ["hero", "rival"]


@pytest.mark.asyncio
async def test_pipeline_fails_the_story_stage_on_an_inconsistent_bible(tmp_path: Path) -> None:
    base = _brief()
    bible = compile_story(base).model_copy(deep=True)
    bible.authored = True
    bible.characters[0].id = "ghost"  # not in the brief

    brief = base.model_copy(update={"story": bible.model_dump()})
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    report = await pipeline.run(brief)

    assert report.success is False
    story = report.stage("story")
    assert story is not None and story.status == "failed"
    assert "inconsistent" in story.detail


@pytest.mark.asyncio
async def test_dry_run_reports_the_story_stage_without_writing(tmp_path: Path) -> None:
    pipeline = AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path)
    report = await pipeline.run(_brief(), dry_run=True)
    assert report.stage("story") is not None
    assert not (tmp_path / STORY_FILENAME).exists()


@pytest.mark.asyncio
async def test_story_stage_is_restored_on_resume(tmp_path: Path) -> None:
    first = await AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path).run(
        _brief()
    )
    assert first.success is True
    assert Path(first.artifacts["story_bible"]).is_file()

    # A restarted process finds the bible file and restores the stage.
    resumed = await AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path).run(
        _brief()
    )
    assert resumed.success is True
    story = resumed.stage("story")
    assert story is not None and story.status == "ok"
    assert resumed.artifacts.get("story_bible") == str(tmp_path / STORY_FILENAME)
    restored = resumed.stage("resume")
    assert restored is not None
    assert "story" in restored.metrics["restored"]


@pytest.mark.asyncio
async def test_deleted_bible_is_regenerated_on_resume(tmp_path: Path) -> None:
    await AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path).run(_brief())
    (tmp_path / STORY_FILENAME).unlink()

    resumed = await AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path).run(
        _brief()
    )
    story = resumed.stage("story")
    assert story is not None and story.status == "ok"
    assert "derived from the brief" in story.detail
    assert (tmp_path / STORY_FILENAME).is_file()
