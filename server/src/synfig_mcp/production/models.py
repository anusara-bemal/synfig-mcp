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
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Turn a title into a filesystem-safe slug."""
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "production"


class TaskStatus(str, Enum):
    """Lifecycle of a single production task."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"


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
    episodes: list[EpisodeSpec] = Field(default_factory=list)
    characters: list[CharacterSpec] = Field(default_factory=list)
    backgrounds: list[dict[str, Any]] = Field(default_factory=list)
    props: list[dict[str, Any]] = Field(default_factory=list)
    rigs: list[dict[str, Any]] = Field(default_factory=list)
    render_profiles: list[RenderProfile] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)
    root: str | None = None
    render_final: bool = False

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

    @property
    def project_slug(self) -> str:
        """The slug of the project directory."""
        return self.slug or slugify(self.title)

    @property
    def shots(self) -> list[ShotSpec]:
        """Return every shot with the episode and sequence it belongs to."""
        return [
            shot
            for episode in self.episodes
            for sequence in episode.sequences
            for shot in sequence.shots
        ]

    @property
    def total_duration(self) -> float:
        """Total duration of the production in seconds."""
        return sum(shot.duration for shot in self.shots)


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