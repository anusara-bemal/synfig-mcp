"""Phase 7: orchestration hardening — transitions, audio cues and build verification."""

from __future__ import annotations

import struct
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.production.models import (
    AudioCue,
    CharacterDescriptor,
    ProductionBrief,
    ProductionReport,
    StageReport,
)
from synfig_mcp.production.pipeline import AnimeProductionPipeline


def _wav(path: Path) -> Path:
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(struct.pack("<h", 0) * 800)
    return path


def _scene_stage(report: ProductionReport) -> StageReport:
    return next(s for s in report.stages if s.name == "scene_build")


@pytest.mark.asyncio
async def test_default_brief_gets_fade_in_and_fade_out(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    report = await pipeline.run(ProductionBrief(title="Fades", width=320, height=180, duration=3.0))
    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]

    stage = _scene_stage(report)
    assert stage.metrics["transitions"] == 2
    document = Path(report.artifacts["document"])
    assert document.is_file()


@pytest.mark.asyncio
async def test_default_fades_go_in_then_out(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    report = await pipeline.run(ProductionBrief(title="Fades", width=320, height=180, duration=4.0))
    assert report.success is True
    root = ET.fromstring(Path(report.artifacts["document"]).read_bytes())

    def _alphas(layer_desc: str) -> list[float]:
        layer = next(e for e in root.iter("layer") if e.get("desc") == layer_desc)
        param = next(p for p in layer.findall("param") if p.get("name") == "color")
        alphas: list[float] = []
        for wp in param.iter("waypoint"):
            color = wp.find("color")
            assert color is not None
            alpha = color.find("a")
            assert alpha is not None
            alphas.append(float(alpha.text or "0"))
        return alphas

    fade_in = _alphas("Transition_1")
    fade_out = _alphas("Transition_2")
    # Fade-in clears from opaque to transparent; fade-out ends opaque.
    assert fade_in[0] > fade_in[-1]
    assert fade_out[0] < fade_out[-1]


@pytest.mark.asyncio
async def test_explicit_dissolve_is_built(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    brief = ProductionBrief(
        title="Dissolve",
        width=320,
        height=180,
        duration=2.0,
        transitions=[{"type": "dissolve", "time": 1.0, "duration": 0.4}],
    )
    report = await pipeline.run(brief)
    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]
    assert _scene_stage(report).metrics["transitions"] == 1


@pytest.mark.asyncio
async def test_unknown_transition_is_rejected(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    brief = ProductionBrief(
        title="Bad",
        width=320,
        height=180,
        duration=2.0,
        transitions=[{"type": "swipe", "duration": 0.3}],
    )
    report = await pipeline.run(brief)
    assert report.success is False
    failed = next(s for s in report.stages if s.status == "failed")
    assert "swipe" in failed.detail


@pytest.mark.asyncio
async def test_audio_cue_becomes_a_sound_layer(tmp_path: Path) -> None:
    wav = _wav(tmp_path / "hit.wav")
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    brief = ProductionBrief(
        title="Sound",
        width=320,
        height=180,
        duration=2.0,
        audio=[AudioCue(file=str(wav), time=0.5, volume=0.8)],
    )
    report = await pipeline.run(brief)
    assert report.success is True, [s.model_dump() for s in report.stages if s.status == "failed"]
    assert _scene_stage(report).metrics["audio"] == 1


@pytest.mark.asyncio
async def test_missing_audio_file_fails_the_scene_stage(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    brief = ProductionBrief(
        title="Missing",
        width=320,
        height=180,
        duration=2.0,
        audio=[AudioCue(file=str(tmp_path / "nope.wav"))],
    )
    report = await pipeline.run(brief)
    assert report.success is False
    failed = next(s for s in report.stages if s.status == "failed")
    assert "audio cue 1" in failed.detail


@pytest.mark.asyncio
async def test_scene_build_verifies_the_document_grew(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    report = await pipeline.run(
        ProductionBrief(title="Verify", width=320, height=180, duration=2.0)
    )
    assert report.success is True
    metrics = _scene_stage(report).metrics
    # The read-back must confirm the requested top-level layers are really in the document.
    assert metrics["verified"] is True
    assert metrics["top_level_layers"] >= metrics["groups"] + metrics["transitions"]
    assert metrics["requested_layers"] > 0


@pytest.mark.asyncio
async def test_final_verification_reports_a_loadable_animated_document(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    brief = ProductionBrief(
        title="Animated",
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
    assert report.success is True
    verification = report.verification
    assert verification["document_loads"] is True
    assert verification["is_animated"] is True
    assert verification["animated_params"] > 0
    assert verification["all_artifacts_present"] is True


@pytest.mark.asyncio
async def test_production_report_is_persisted(tmp_path: Path) -> None:
    import json

    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    report = await pipeline.run(
        ProductionBrief(title="Reported", width=320, height=180, duration=2.0)
    )
    assert report.success is True
    report_path = Path(report.artifacts["report"])
    assert report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["success"] is True
    assert payload["title"] == "Reported"
    assert "verification" in payload


@pytest.mark.asyncio
async def test_dry_run_does_not_write_a_report(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    pipeline = AnimeProductionPipeline(backend=backend, output_dir=tmp_path)
    report = await pipeline.run(
        ProductionBrief(title="Dry", width=320, height=180, duration=2.0), dry_run=True
    )
    assert report.dry_run is True
    assert "report" not in report.artifacts
    assert report.verification == {}
