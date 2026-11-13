"""
On-disk production state (Phase 4c).

A long production run can be killed (editor crash, Ctrl-C, a stage that needs a
manual fix).  Without state the next run starts from scratch and redoes hours of
work.  This module records, after every stage, what completed and the
JSON-serializable hand-off the next stage needs, so
:class:`~synfig_mcp.production.pipeline.AnimeProductionPipeline` can reopen the
saved document and continue instead of rebuilding.

The state is a single ``pipeline_state.json`` inside the production's output
directory.  It is keyed by a fingerprint of the brief: change the brief and the
stale state is ignored rather than trusted.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from synfig_mcp.production.models import ProductionBrief, StageReport

#: Bumped whenever the on-disk shape changes incompatibly.
STATE_VERSION = 1

#: File name of the state inside the output directory.
STATE_FILENAME = "pipeline_state.json"


def brief_fingerprint(brief: ProductionBrief) -> str:
    """A stable hash of everything that changes the produced artifacts."""
    payload = json.dumps(brief.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class StageState(BaseModel):
    """One completed stage's report."""

    report: StageReport


class ProductionState(BaseModel):
    """Everything needed to resume a production run."""

    version: int = STATE_VERSION
    title: str
    style: str
    fingerprint: str
    output_dir: str
    doc_id: str | None = None
    document_path: str | None = None
    #: True once characters and assets were assembled into the saved document.
    scene_built: bool = False
    #: The latest stage whose effect is in the saved document ("storyboard" | "style").
    saved_through: str | None = None
    stages: dict[str, StageState] = Field(default_factory=dict)
    updated_at: str = ""

    # -- persistence -------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> ProductionState | None:
        """Read the state, or return ``None`` when it is missing or unreadable."""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            state = cls.model_validate(json.loads(raw))
        except (ValueError, TypeError):
            return None
        if state.version != STATE_VERSION:
            return None
        return state

    def save(self, path: Path) -> None:
        """Write the state atomically so a crash mid-write cannot corrupt it."""
        self.updated_at = datetime.now(UTC).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)

    # -- queries -----------------------------------------------------------

    def matches(self, brief: ProductionBrief) -> bool:
        return self.fingerprint == brief_fingerprint(brief)

    def completed(self, name: str) -> StageState | None:
        """The recorded state of a stage that finished (ok or skipped)."""
        entry = self.stages.get(name)
        if entry is None or entry.report.status == "failed":
            return None
        return entry

    def record(self, report: StageReport) -> None:
        self.stages[report.name] = StageState(report=report)

    def report(self) -> StageReport:
        """A synthetic report describing what a resumed run restored."""
        restored = [
            name for name, entry in self.stages.items() if entry.report.status in ("ok", "skipped")
        ]
        return StageReport(
            name="resume",
            detail=f"resumed from state; restored {len(restored)} completed stage(s)",
            metrics={"restored": sorted(restored)},
        )
