"""
Render Job Manager for asynchronous background rendering and cancellation in synfig-mcp.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from synfig_mcp.errors import SynfigError
from synfig_mcp.logging import get_logger
from synfig_mcp.render.pipeline import CancellationToken

if TYPE_CHECKING:
    from synfig_mcp.backend.base import BackendBase

logger = get_logger("synfig_mcp.render.jobs")


@dataclass
class RenderJob:
    job_id: str
    doc_id: str
    output_dir: Path
    status: str = "running"  # running, completed, cancelled, failed
    current_frame: int = 0
    total_frames: int = 0
    percent: float = 0.0
    frames: list[str] = field(default_factory=list)
    error: str | None = None
    cancel_token: CancellationToken = field(default_factory=CancellationToken)
    task: asyncio.Task[Any] | None = None


class RenderJobManager:
    """Manages long-running render jobs independently of individual RPC request lifetimes."""

    def __init__(self) -> None:
        self._jobs: dict[str, RenderJob] = {}

    def start_job(
        self,
        backend: BackendBase,
        doc_id: str,
        output_dir: str | Path,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
        progress_cb: Any = None,
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        out_p = Path(output_dir).resolve()
        job = RenderJob(job_id=job_id, doc_id=doc_id, output_dir=out_p)
        self._jobs[job_id] = job

        async def _run() -> None:
            def _on_progress(cur: int, total: int, pct: float) -> None:
                job.current_frame = cur
                job.total_frames = total
                job.percent = pct
                if progress_cb:
                    res = progress_cb(cur, total, pct)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)

            try:
                frames = await backend.render_sequence(
                    doc_id=doc_id,
                    output_dir=str(out_p),
                    start_time=start_time,
                    end_time=end_time,
                    fps=fps,
                    width=width,
                    height=height,
                    target=target,
                    progress_cb=_on_progress,
                    cancel_token=job.cancel_token,
                )
                job.frames = frames
                job.status = "completed"
                job.percent = 100.0
            except (SynfigError, asyncio.CancelledError) as e:
                if job.cancel_token.is_cancelled:
                    job.status = "cancelled"
                    job.error = "Operation cancelled by user"
                else:
                    job.status = "failed"
                    job.error = str(e)
                # Cleanup partial output on cancellation
                if job.status == "cancelled":
                    with contextlib.suppress(Exception):
                        for f in out_p.glob(f"*.{target}"):
                            f.unlink(missing_ok=True)
            except Exception as e:
                job.status = "failed"
                job.error = str(e)

        job.task = asyncio.create_task(_run())
        return job_id

    def get_status(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            raise SynfigError(f"Render job '{job_id}' not found", code=4004)
        return {
            "job_id": job.job_id,
            "status": job.status,
            "current_frame": job.current_frame,
            "total_frames": job.total_frames,
            "percent": job.percent,
            "frames": job.frames if job.status == "completed" else None,
            "error": job.error,
        }

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            raise SynfigError(f"Render job '{job_id}' not found", code=4004)
        if job.status != "running":
            raise SynfigError(
                f"Render job '{job_id}' is not running (status: {job.status})", code=4005
            )

        job.cancel_token.cancel()
        if job.task and not job.task.done():
            job.task.cancel()
        job.status = "cancelled"
        job.error = "Operation cancelled by user"

        # Cleanup partial output files
        with contextlib.suppress(Exception):
            for f in job.output_dir.glob("*.png"):
                f.unlink(missing_ok=True)

        return {
            "job_id": job.job_id,
            "cancelled": True,
            "message": f"Render job '{job_id}' cancelled and partial frames cleaned up.",
        }

    def get_result(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            raise SynfigError(f"Render job '{job_id}' not found", code=4004)
        if job.status == "running":
            return {"job_id": job.job_id, "status": "running", "percent": job.percent}
        if job.status == "failed":
            raise SynfigError(f"Render job failed: {job.error}", code=4006)
        if job.status == "cancelled":
            raise SynfigError(f"Render job was cancelled: {job.error}", code=4007)
        return {
            "job_id": job.job_id,
            "status": "completed",
            "frames": job.frames,
            "total_frames": len(job.frames),
        }


job_manager = RenderJobManager()
