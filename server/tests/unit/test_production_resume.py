"""On-disk production state: a killed run resumes without rebuilding (Phase 4c)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.production.models import CharacterDescriptor, ProductionBrief
from synfig_mcp.production.pipeline import AnimeProductionPipeline
from synfig_mcp.production.state import (
    STATE_FILENAME,
    ProductionState,
    brief_fingerprint,
)


def _brief(**over: object) -> ProductionBrief:
    data: dict[str, object] = {
        "title": "Resume Me",
        "width": 320,
        "height": 180,
        "duration": 2.0,
        "characters": [
            CharacterDescriptor(
                id="hero",
                position={"x": 80.0, "y": 170.0},
                actions=[{"motion": "walk", "start": 0.0, "end": 2.0}],
            )
        ],
    }
    data.update(over)
    return ProductionBrief.model_validate(data)


async def _layer_count(backend: HeadlessBackend, doc_id: str) -> int:
    summary = await backend.scene_summary(doc_id)
    return int(summary["layer_count"])


@pytest.mark.asyncio
async def test_state_file_is_written_after_a_run(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    report = await pipeline.run(_brief())
    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]

    state_path = tmp_path / STATE_FILENAME
    assert state_path.is_file()
    state = ProductionState.load(state_path)
    assert state is not None
    assert state.fingerprint == brief_fingerprint(_brief())
    assert state.scene_built is True
    assert state.document_path and Path(state.document_path).is_file()
    assert "document" in state.stages and "render" in state.stages


@pytest.mark.asyncio
async def test_second_run_resumes_without_rebuilding(tmp_path: Path) -> None:
    first = HeadlessBackend()
    report = await AnimeProductionPipeline(backend=first, output_dir=tmp_path).run(_brief())
    doc_id = report.doc_id
    assert doc_id is not None
    layers_before = await _layer_count(first, doc_id)

    # A brand-new backend simulates a restarted process reading the state from disk.
    second = HeadlessBackend()
    resumed = await AnimeProductionPipeline(backend=second, output_dir=tmp_path).run(_brief())

    assert resumed.success is True
    statuses = {s.name: s.status for s in resumed.stages}
    assert statuses.get("document") == "ok"
    assert statuses.get("characters") == "ok"
    # The scene is restored, never rebuilt: the layer count must not grow.
    scene = next(s for s in resumed.stages if s.name == "scene_build")
    assert "restored" in scene.detail
    assert resumed.doc_id is not None
    assert await _layer_count(second, resumed.doc_id) == layers_before
    # A resume marker is reported.
    assert any(s.name == "resume" for s in resumed.stages)


@pytest.mark.asyncio
async def test_resume_false_forces_a_clean_rebuild(tmp_path: Path) -> None:
    await AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path).run(_brief())
    fresh = HeadlessBackend()
    report = await AnimeProductionPipeline(backend=fresh, output_dir=tmp_path).run(
        _brief(), resume=False
    )
    scene = next(s for s in report.stages if s.name == "scene_build")
    assert "assembled" in scene.detail
    assert not any(s.name == "resume" for s in report.stages)


@pytest.mark.asyncio
async def test_changed_brief_ignores_stale_state(tmp_path: Path) -> None:
    await AnimeProductionPipeline(backend=HeadlessBackend(), output_dir=tmp_path).run(_brief())
    changed = _brief(duration=3.0)
    fresh = HeadlessBackend()
    report = await AnimeProductionPipeline(backend=fresh, output_dir=tmp_path).run(changed)
    assert not any(s.name == "resume" for s in report.stages)
    scene = next(s for s in report.stages if s.name == "scene_build")
    assert "assembled" in scene.detail


@pytest.mark.asyncio
async def test_partial_run_resumes_from_the_first_missing_stage(tmp_path: Path) -> None:
    """A crash after the document stage must not throw away that work."""
    state = ProductionState(
        title="Resume Me",
        style="default",
        fingerprint=brief_fingerprint(_brief()),
        output_dir=str(tmp_path),
    )
    state_path = tmp_path / STATE_FILENAME
    state.save(state_path)

    backend = HeadlessBackend()
    report = await AnimeProductionPipeline(backend=backend, output_dir=tmp_path).run(_brief())
    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]
    # No document existed in the partial state, so the run built one from scratch.
    scene = next(s for s in report.stages if s.name == "scene_build")
    assert "assembled" in scene.detail


def test_state_load_rejects_corrupt_or_old_files(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert ProductionState.load(bad) is None

    old = tmp_path / "old.json"
    old.write_text(json.dumps({"version": 999, "title": "x"}), encoding="utf-8")
    assert ProductionState.load(old) is None

    assert ProductionState.load(tmp_path / "missing.json") is None
