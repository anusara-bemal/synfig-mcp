"""
Typed models of the production system.

A *production* is a tree: a project holds episodes, an episode holds
sequences and a sequence holds shots.  Everything else - the asset
registries, the render profiles, the version history - hangs off the project.

The models are strict on purpose: a brief that does not describe a coherent
production is rejected before a single layer is created, so a production run
never leaves half-built shots behind because of a typo in the brief.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Turn a title into a filesystem-safe slug."""
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "production"


class TaskStatus(StrEnum):
    """Lifecycle of a single production task."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"


class RenderOptions(BaseModel):
    """What to render once the scene is built."""

    video: bool = Field(default=True, description="Encode a video file.")
    video_format: str = Field(
        default="mp4", description="'mp4' needs ffmpeg; 'gif' only needs Pillow."
    )
    contact_sheet: bool = Field(default=True, description="Render a tiled contact sheet.")
    review: bool = Field(default=True, description="Run the objective review metrics.")
    preview_frames: int = Field(default=6, ge=2, le=9, description="Frames in the review loop.")


class RenderProfile(BaseModel):
    """A named output configuration."""

    name: str
    width: int = 1920
    height: int = 1080
    fps: float = 24.0
    target: str = "png"
    description: str = ""

    @field_validator("width", "height")
    @classmethod
    def _positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("A render profile needs a positive width and height.")
        return value

    @field_validator("fps")
    @classmethod
    def _valid_fps(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("A render profile needs a positive frame rate.")
        return value


class ShotSpec(BaseModel):
    """One shot of a sequence."""

    id: str
    title: str = ""
    duration: float = 2.0
    description: str = ""
    characters: list[str] = Field(default_factory=list)
    background: str | None = None
    effects: list[Any] = Field(default_factory=list)
    camera: list[dict[str, Any]] = Field(default_factory=list)
    dialogue: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A shot needs an id.")
        return value

    @field_validator("duration")
    @classmethod
    def _positive_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("A shot needs a positive duration.")
        return value

    @property
    def shot_id(self) -> str:
        return self.id

    @property
    def duration_seconds(self) -> float:
        return self.duration


class SequenceSpec(BaseModel):
    """A sequence of shots."""

    id: str
    title: str = ""
    shots: list[ShotSpec] = Field(default_factory=list)


class EpisodeSpec(BaseModel):
    """An episode of sequences."""

    id: str
    title: str = ""
    sequences: list[SequenceSpec] = Field(default_factory=list)


class CharacterSpec(BaseModel):
    """A character of the production."""

    id: str
    manifest: str | None = None
    parts: list[dict[str, Any]] = Field(default_factory=list)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    height: float = 200.0
    flip: bool = False
    rig: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)


class ProductionBrief(BaseModel):
    """The structured request an agent hands to the orchestrator."""

    title: str
    slug: str | None = None
    logline: str = ""
    width: int = 1920
    height: int = 1080
    fps: float = 24.0
    style: str = "shonen_action"
    duration: float = 2.0
    seed: int = 0
    # Flat character descriptors used by the anime pipeline.
    # Accept both CharacterSpec (episode tree) and CharacterDescriptor (flat).
    characters: list[Any] = Field(default_factory=list)
    assets: list[Any] = Field(default_factory=list)
    background: dict[str, Any] | None = None
    backgrounds: list[dict[str, Any]] = Field(default_factory=list)
    props: list[dict[str, Any]] = Field(default_factory=list)
    rigs: list[dict[str, Any]] = Field(default_factory=list)
    camera: list[dict[str, Any]] = Field(default_factory=list)
    audio: list[Any] = Field(default_factory=list)  # list[AudioCue]
    transitions: list[dict[str, Any]] = Field(default_factory=list)
    shots: list[Any] = Field(default_factory=list)  # list[StoryboardShot | ShotSpec]
    episodes: list[EpisodeSpec] = Field(default_factory=list)
    render_profiles: list[RenderProfile] = Field(default_factory=list)
    render: RenderOptions = Field(default_factory=RenderOptions)
    checkpoints: list[str] = Field(default_factory=list)
    root: str | None = None
    save_path: str | None = None
    output_dir: str | None = None
    render_final: bool = False
    story: Any | None = None

    @field_validator("slug")
    @classmethod
    def _valid_slug(cls, value: str | None) -> str | None:
        if value is not None and not slugify(value):
            raise ValueError("A project slug must contain at least one letter or digit.")
        return value

    @field_validator("width", "height")
    @classmethod
    def _positive_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("A production needs a positive width and height.")
        return value

    @field_validator("fps")
    @classmethod
    def _valid_fps(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("A production needs a positive frame rate.")
        return value

    @model_validator(mode="after")
    def _resolve_shots_and_characters(self) -> ProductionBrief:
        # If episodes provided and shots empty, populate shots from episodes
        if not self.shots and self.episodes:
            self.shots = [
                shot
                for episode in self.episodes
                for sequence in episode.sequences
                for shot in sequence.shots
            ]
        else:
            from synfig_mcp.characters.models import StoryboardShot

            parsed_shots: list[Any] = []
            for s in self.shots:
                if isinstance(s, dict):
                    if "shot_id" in s or "duration_seconds" in s:
                        parsed_shots.append(StoryboardShot.model_validate(s))
                    elif "id" in s:
                        parsed_shots.append(ShotSpec.model_validate(s))
                    else:
                        parsed_shots.append(StoryboardShot.model_validate(s))
                else:
                    parsed_shots.append(s)
            self.shots = parsed_shots

        parsed_chars: list[Any] = []
        for c in self.characters:
            if isinstance(c, dict):
                if (
                    "archetype" in c
                    or "palette" in c
                    or ("position" in c and "id" in c and "actions" in c and "parts" not in c)
                ):
                    parsed_chars.append(CharacterDescriptor.model_validate(c))
                elif "parts" in c:
                    parsed_chars.append(CharacterSpec.model_validate(c))
                else:
                    parsed_chars.append(CharacterDescriptor.model_validate(c))
            else:
                parsed_chars.append(c)
        self.characters = parsed_chars

        self.audio = [AudioCue.model_validate(a) if isinstance(a, dict) else a for a in self.audio]
        self.assets = [
            AssetRequest.model_validate(a) if isinstance(a, dict) else a for a in self.assets
        ]
        if isinstance(self.render, dict):
            self.render = RenderOptions.model_validate(self.render)
        return self

    @property
    def project_slug(self) -> str:
        """The slug of the project directory."""
        return self.slug or slugify(self.title)

    @property
    def total_duration(self) -> float:
        """Total duration of the production in seconds."""
        if self.shots:
            return sum(
                getattr(s, "duration", getattr(s, "duration_seconds", 0.0)) for s in self.shots
            )
        return self.duration


# ---------------------------------------------------------------------------
# Flat-brief models used by the anime pipeline
# ---------------------------------------------------------------------------


class CharacterDescriptor(BaseModel):
    """Lightweight character specification used by the anime production pipeline.

    Unlike :class:`CharacterSpec` (which is part of the episode/sequence tree)
    this descriptor is a *flat* per-character entry used as a direct member of
    ``ProductionBrief.characters``.
    """

    id: str
    archetype: str = "humanoid"
    height: float = 0.62
    palette: list[str] = Field(default_factory=list)
    facing: str = "right"
    position: dict[str, float] | None = None
    z: float = 0.0
    actions: list[dict[str, Any]] = Field(default_factory=list)
    manifest: str | None = None
    rig: str | None = None

    @property
    def flip(self) -> bool:
        return self.facing == "left"


class AudioCue(BaseModel):
    """A single audio cue placed on the timeline."""

    file: str
    time: float = 0.0
    volume: float = 1.0


class AssetRequest(BaseModel):
    """An opt-in external asset that the pipeline should try to fetch."""

    id: str
    kind: str = "prop"
    procedural: dict[str, Any] | None = None
    search: dict[str, Any] | None = None
    local_path: str | None = None
    position: dict[str, float] | None = None
    height: float | None = None
    z: float = 0.0


class StageReport(BaseModel):
    """Result record for one pipeline stage."""

    name: str
    status: str = "ok"
    detail: str = ""
    artifacts: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ProductionReport(BaseModel):
    """Aggregate result returned by :class:`AnimeProductionPipeline.run`."""

    success: bool = True
    title: str = ""
    style: str = ""
    dry_run: bool = False
    doc_id: str | None = None
    total_shots: int = 0
    duration_seconds: float = 0.0
    stages: list[StageReport] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    def stage(self, name: str) -> StageReport | None:
        return next((s for s in self.stages if s.name == name), None)


class AssetRecord(BaseModel):
    """One entry of the asset registry."""

    id: str
    kind: str = "asset"
    path: str | None = None
    title: str = ""
    creator: str = ""
    license_code: str = "own"
    rights: str = ""
    source_url: str = ""
    sha256: str = ""
    width: int | None = None
    height: int | None = None
    created_at: str = ""


class VersionRecord(BaseModel):
    """One entry of the version history."""

    label: str
    path: str | None = None
    sha256: str = ""
    recorded_at: str = ""


class ProductionTask(BaseModel):
    """One step of the production plan."""

    id: str
    kind: str
    title: str = ""
    depends_on: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    checkpoint: str | None = None
    critical: bool = False


class ProductionPlan(BaseModel):
    """The ordered list of tasks of a production."""

    project: str
    tasks: list[ProductionTask] = Field(default_factory=list)
    approved_checkpoints: list[str] = Field(default_factory=list)

    def task(self, task_id: str) -> ProductionTask | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def pending(self) -> list[ProductionTask]:
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def is_approved(self, checkpoint: str) -> bool:
        return checkpoint in self.approved_checkpoints


class ProductionManifest(BaseModel):
    """The on-disk manifest of a production project."""

    schema_version: str = "1.0"
    title: str
    slug: str
    logline: str = ""
    created_at: str = ""
    updated_at: str = ""
    width: int = 1920
    height: int = 1080
    fps: float = 24.0
    style: str = "shonen_action"
    brief: dict[str, Any] = Field(default_factory=dict)
    render_profiles: list[RenderProfile] = Field(default_factory=list)
    assets: list[AssetRecord] = Field(default_factory=list)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    backgrounds: list[dict[str, Any]] = Field(default_factory=list)
    props: list[dict[str, Any]] = Field(default_factory=list)
    rigs: list[dict[str, Any]] = Field(default_factory=list)
    episodes: list[dict[str, Any]] = Field(default_factory=list)
    shots: list[dict[str, Any]] = Field(default_factory=list)
    versions: list[VersionRecord] = Field(default_factory=list)
    doc_id: str | None = None
    project_file: str | None = None
    status: str = "created"
