"""
The production workspace.

A production lives in a directory inside the roots the server already
protects: nothing outside the configured workspace roots is ever written to.
The directory layout is the one a studio uses on disk::

    <root>/<slug>/
        project.json      the manifest (brief, registries, versions)
        assets/           staged source assets
        shots/            the editable Synfig file of every shot
        renders/          preview and final renders
        logs/             the structured production log
        checkpoints/      the resumable state of the production run
        reports/          the production reports

Every path the workspace hands out is validated with the same path
validator the rest of the server uses, so a production project cannot be
used to read or write outside the workspace.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from synfig_mcp.errors import SecuritySandboxError, SynfigError
from synfig_mcp.production.models import (
    AssetRecord,
    ProductionBrief,
    ProductionManifest,
    VersionRecord,
    slugify,
)
from synfig_mcp.security.sandbox import get_default_allowed_roots, validate_path

PROJECT_DIRECTORIES = ("assets", "shots", "renders", "logs", "checkpoints", "reports")


def _now() -> str:
    """Return the current UTC timestamp in ISO 8601."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _atomic_write(path: Path, text: str) -> None:
    """Write a file atomically so a crash never leaves a half written manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class ProductionWorkspace:
    """The on-disk home of one production."""

    def __init__(self, root: Path | str, slug: str) -> None:
        self.root = Path(root)
        self.slug = slug
        self.project_dir = self.root / slug
        self.manifest_path = self.project_dir / "project.json"

    @classmethod
    def create(cls, brief: ProductionBrief, base_dir: Path | str) -> ProductionWorkspace:
        """Create the directory layout of a new production."""
        root = validate_path(base_dir, allowed_roots=get_default_allowed_roots())
        slug = brief.project_slug
        workspace = cls(root / "projects", slug)
        workspace.project_dir.mkdir(parents=True, exist_ok=True)
        if any(workspace.project_dir.iterdir()):
            raise SynfigError(
                f"The production '{slug}' already exists at '{workspace.project_dir}'. "
                "Choose another slug or remove the directory first."
            )
        for name in PROJECT_DIRECTORIES:
            (workspace.project_dir / name).mkdir(parents=True, exist_ok=True)
        return workspace

    @classmethod
    def open(cls, root: Path | str, slug: str) -> ProductionWorkspace:
        """Open an existing production."""
        root = validate_path(root, allowed_roots=get_default_allowed_roots())
        workspace = cls(root, slugify(slug))
        if not workspace.manifest_path.is_file():
            raise SynfigError(
                f"No production manifest at '{workspace.manifest_path}'. "
                "Create the production first."
            )
        return workspace

    def path(self, *parts: str) -> Path:
        """Return a validated path inside the production directory."""
        return validate_path(
            self.project_dir.joinpath(*parts), allowed_roots=[self.project_dir]
        )

    @property
    def assets_dir(self) -> Path:
        return self.path("assets")

    @property
    def shots_dir(self) -> Path:
        return self.path("shots")

    @property
    def renders_dir(self) -> Path:
        return self.path("renders")

    @property
    def logs_dir(self) -> Path:
        return self.path("logs")

    @property
    def checkpoints_dir(self) -> Path:
        return self.path("checkpoints")

    @property
    def reports_dir(self) -> Path:
        return self.path("reports")

    def shot_file(self, shot_id: str) -> Path:
        """Return the path of the editable Synfig file of a shot."""
        return self.path("shots", slugify(shot_id) + ".sif")

    def render_dir(self, shot_id: str) -> Path:
        """Return the directory the renders of a shot go to."""
        directory = self.path("renders", slugify(shot_id))
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write_manifest(self, manifest: ProductionManifest) -> None:
        """Write the manifest of the production."""
        manifest.updated_at = _now()
        _atomic_write(
            self.manifest_path, json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n"
        )

    def read_manifest(self) -> ProductionManifest:
        """Read the manifest of the production."""
        return ProductionManifest.model_validate(
            json.loads(self.manifest_path.read_text(encoding="utf-8"))
        )

    def record_version(self, manifest: ProductionManifest, label: str, path: Path | str) -> None:
        """Record a version of the production in the history."""
        file_path = Path(path)
        sha = ""
        if file_path.is_file():
            sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        manifest.versions.append(
            VersionRecord(label=label, path=str(file_path), sha256=sha, recorded_at=_now())
        )
        self.write_manifest(manifest)

    def register_asset(self, manifest: ProductionManifest, record: AssetRecord) -> None:
        """Add or replace an asset in the registry."""
        manifest.assets = [a for a in manifest.assets if a.id != record.id]
        manifest.assets.append(record)
        self.write_manifest(manifest)

    def find_asset(self, manifest: ProductionManifest, asset_id: str) -> AssetRecord | None:
        """Look an asset up in the registry."""
        return next((a for a in manifest.assets if a.id == asset_id), None)

    def log_event(self, event: dict[str, Any]) -> None:
        """Append a structured event to the production log."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        payload = {"time": _now(), **event}
        with self.path("logs", "production.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")

    def read_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Read the production log."""
        log_path = self.path("logs", "production.jsonl")
        if not log_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events[-limit:]

    def write_state(self, name: str, payload: dict[str, Any]) -> None:
        """Write the resumable state of the production run."""
        _atomic_write(self.path("checkpoints", name), json.dumps(payload, indent=2) + "\n")

    def read_state(self, name: str) -> dict[str, Any] | None:
        """Read the resumable state of the production run."""
        state_path = self.path("checkpoints", name)
        if not state_path.is_file():
            return None
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def sha256_of(path: Path | str) -> str:
        """Return the SHA-256 of a file."""
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1048576), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def assert_inside(self, path: Path | str) -> None:
        """Assert that a path is inside the production directory."""
        resolved = Path(path).resolve()
        if self.project_dir.resolve() not in resolved.parents and resolved != self.project_dir.resolve():
            raise SecuritySandboxError(
                f"Path '{path}' is outside the production directory '{self.project_dir}'."
            )