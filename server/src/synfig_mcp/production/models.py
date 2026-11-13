"""
Data models for the anime production pipeline (Step 0).

``ProductionBrief`` is the single input a caller gives; ``ProductionReport`` is
the structured, per-stage result returned.  Both are plain Pydantic models so
they can be embedded directly in an MCP tool schema.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from synfig_mcp.characters.models import StoryboardShot


class RenderOptions(BaseModel):
    """What to render once the scene is built."""

    video: bool = Field(default=True, description="Encode a video file.")
    video_format: Literal["mp4", "gif"] = Field(
        default="mp4", description="'mp4' needs ffmpeg; 'gif' only needs Pillow."
    )
    contact_sheet: bool = Field(default=True, description="Render a tiled contact sheet.")
    review: bool = Field(default=True, description="Run the objective review metrics.")
    preview_frames: int = Field(default=6, ge=2, le=9, description="Frames in the review loop.")


class AudioCue(BaseModel):
    """One sound file placed on the production timeline."""

    file: str = Field(description="Path to a sound file (wav, ogg, mp3, flac, ...).")
    time: float = Field(default=0.0, ge=0.0, description="Start offset in seconds.")
    volume: float = Field(default=1.0, ge=0.0, le=4.0)


class CharacterDescriptor(BaseModel):
    """A high-level character brief that expands into rig-ready parts.

    No franchise names: a descriptor is anatomy, proportions and a palette, so
    the generated character is always original geometry.
    """

    id: str = Field(description="Character id (letters, digits, underscore).")
    archetype: Literal["humanoid", "chibi"] = Field(
        default="humanoid",
        description="Proportion preset: 'humanoid' (7 heads) or 'chibi' (3 heads, big head).",
    )
    height: float = Field(
        default=0.62,
        gt=0.0,
        le=1.0,
        description="Height as a fraction of the canvas height.",
    )
    palette: list[str] = Field(
        default_factory=list,
        description="Optional hex colours (#rrggbb): [skin, hair, primary, secondary]. "
        "Falls back to the active style preset.",
    )
    facing: Literal["right", "left"] = Field(default="right")
    position: dict[str, float] | None = Field(
        default=None,
        description="Where the character stands, in canvas pixels {x, y}. "
        "Omitted characters are spread across the floor.",
    )
    z: float = Field(default=0.0, description="Scene stacking; higher is in front.")
    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Motion list, e.g. [{'motion': 'walk', 'start': 0, 'end': 3, "
        "'move_to': {'x': 900, 'y': 640}}].",
    )

    @field_validator("palette")
    @classmethod
    def _palette_shape(cls, value: list[str]) -> list[str]:
        for colour in value:
            raw = colour.strip().lstrip("#")
            if len(raw) not in (3, 6, 8) or any(c not in "0123456789abcdefABCDEF" for c in raw):
                raise ValueError(f"palette colour '{colour}' must look like #rrggbb")
        return value


class AssetRequest(BaseModel):
    """One asset the scene needs: procedural, or fetched from an open provider."""

    id: str = Field(description="Asset id, used as the layer/group prefix.")
    kind: Literal["background", "prop", "texture"] = Field(default="prop")
    procedural: dict[str, Any] | None = Field(
        default=None,
        description="Procedural params: {generator, ...}. See AssetGenerator.list_generators().",
    )
    search: dict[str, Any] | None = Field(
        default=None,
        description="Opt-in network fetch: {query, provider, license, rights, title, creator}.",
    )
    position: dict[str, float] | None = Field(
        default=None, description="Canvas pixels {x, y} for a prop."
    )
    height: float | None = Field(default=None, description="Height in canvas pixels for a prop.")
    z: float = Field(default=0.0)

    @model_validator(mode="after")
    def _one_source(self) -> AssetRequest:
        if self.procedural is None and self.search is None:
            raise ValueError("an asset needs either 'procedural' or 'search'")
        return self


class ProductionBrief(BaseModel):
    """The single input to :meth:`AnimeProductionPipeline.run`."""

    title: str = Field(default="Untitled Production", description="Project title.")
    style: str = Field(
        default="shonen_action",
        description="Style preset name (see style_list). Drives palette and effect stack.",
    )
    width: int = Field(default=1280, ge=16, le=8192)
    height: int = Field(default=720, ge=16, le=8192)
    fps: float = Field(default=24.0, gt=0.0, le=240.0)
    duration: float = Field(
        default=6.0,
        gt=0.0,
        le=3600.0,
        description="Total duration in seconds. When shots are given, their durations win.",
    )
    seed: int = Field(
        default=0,
        ge=0,
        description="Seed for all procedural randomness; the same brief reproduces byte-identical layers.",
    )
    shots: list[StoryboardShot] = Field(
        default_factory=list,
        description="Optional shot list; when empty a single shot spanning 'duration' is used.",
    )
    characters: list[CharacterDescriptor] = Field(default_factory=list)
    assets: list[AssetRequest] = Field(
        default_factory=list,
        description="Extra assets beyond each character's generated rig.",
    )
    background: dict[str, Any] | None = Field(
        default=None,
        description="Convenience background: a procedural spec {generator, ...} or "
        "{file: 'bg.png', fit: 'cover'}.",
    )
    camera: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Camera keys [{time, zoom, center: {x, y}}]; a gentle default is used when empty.",
    )
    transitions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Shot-boundary transitions [{type: 'fade'|'dissolve', duration, time?}]. When "
        "empty, a fade-in at 0s and a fade-out at the end are used so the edit reads cleanly.",
    )
    audio: list[AudioCue] = Field(
        default_factory=list,
        description="Sound cues placed on the timeline, e.g. a music bed or a hit at a beat.",
    )
    render: RenderOptions = Field(default_factory=RenderOptions)
    story: Any | None = Field(
        default=None,
        description="Optional authored StoryBible (see the story_bible tool). When set, the "
        "pipeline validates and consumes it instead of deriving one from the brief.",
    )
    save_path: str | None = Field(
        default=None, description="Where to write the .sif/.sifz. Defaults under the workspace."
    )
    output_dir: str | None = Field(
        default=None, description="Directory for the video, contact sheet and rig sheets."
    )


class StageReport(BaseModel):
    """The outcome of one pipeline stage."""

    name: str
    status: Literal["ok", "skipped", "failed"] = "ok"
    detail: str = ""
    artifacts: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ProductionReport(BaseModel):
    """The structured result of a production run."""

    success: bool = Field(description="True when every attempted stage succeeded.")
    title: str
    style: str
    doc_id: str | None = None
    total_shots: int = 0
    duration_seconds: float = 0.0
    stages: list[StageReport] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Named output paths: document, video, contact_sheet, rig_sheets, manifest.",
    )
    review: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(
        default_factory=dict,
        description="Final read-back checks: document loads, animated waypoints present, "
        "and every requested artifact exists on disk.",
    )
    dry_run: bool = False

    def stage(self, name: str) -> StageReport | None:
        return next((s for s in self.stages if s.name == name), None)
