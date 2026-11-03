# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Render command construction, bounded render manager and job tracking."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from ..config import Settings
from ..errors import RenderCancelledError, RenderError, RenderTimeoutError, UnsupportedTargetError
from ..logging import get_logger
from .runner import get_process_registry, run_synfig

logger = get_logger(__name__)

# Targets this server knows how to ask for; availability is always verified
# against `synfig --targets` at runtime.
KNOWN_TARGETS = {
    "png": "PNG frames",
    "png-spritesheet": "PNG sprite sheet",
    "gif": "GIF animation",
    "ffmpeg": "MP4/WebM via ffmpeg",
    "libav": "Video via libavcodec",
    "bmp": "Windows BMP",
    "jpeg": "JPEG frames",
    "ppm": "PPM frames",
    "dv": "DV video",
    "yuv420p": "Raw YUV",
    "magick++": "Via ImageMagick (if the module loads)",
    "null": "Null (benchmark)",
}

_QUALITY_ANTIALIAS = {"low": 1, "preview": 1, "standard": 2, "normal": 2, "high": 4, "best": 4}


@dataclass
class RenderJob:
    render_id: str
    kind: str
    target: str
    output: str
    status: str = "queued"  # queued | running | done | failed | cancelled
    progress: float = 0.0
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["duration_seconds"] = round((self.finished_at or time.time()) - self.started_at, 3)
        return data


class RenderManager:
    """Bounds concurrent renders; records job outcomes for status queries."""

    MAX_JOBS = 100

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.render_workers)
        self._jobs: dict[str, RenderJob] = {}
        self._order: deque[str] = deque(maxlen=self.MAX_JOBS)
        self._lock = asyncio.Lock()

    async def _record(self, job: RenderJob) -> None:
        async with self._lock:
            is_new = job.render_id not in self._jobs
            self._jobs[job.render_id] = job
            if is_new:
                self._order.append(job.render_id)
            while len(self._jobs) > self.MAX_JOBS:
                oldest = self._order.popleft()
                self._jobs.pop(oldest, None)

    async def get(self, render_id: str) -> RenderJob | None:
        async with self._lock:
            return self._jobs.get(render_id)

    async def list_jobs(self) -> list[RenderJob]:
        async with self._lock:
            return [self._jobs[key] for key in self._order if key in self._jobs]

    async def run_render(
        self,
        *,
        kind: str,
        binary: str,
        args: list[str],
        target: str,
        output: str,
        timeout: float | None = None,
        progress_cb: Callable[[float], None] | None = None,
    ) -> RenderJob:
        job = RenderJob(
            render_id=f"render-{uuid.uuid4().hex[:12]}",
            kind=kind,
            target=target,
            output=str(output),
            status="queued",
        )
        await self._record(job)
        async with self._semaphore:
            job.status = "running"
            job.started_at = time.time()
            await self._record(job)
            try:
                result = await run_synfig(
                    binary,
                    args,
                    render_id=job.render_id,
                    timeout=timeout or self._settings.render_timeout,
                    description=f"{kind}:{target}",
                    progress_cb=progress_cb,
                )
            except RenderCancelledError as exc:
                job.status = "cancelled"
                job.error = exc.message
                job.finished_at = time.time()
                await self._record(job)
                raise
            except RenderTimeoutError as exc:
                job.status = "failed"
                job.error = exc.message
                job.finished_at = time.time()
                await self._record(job)
                raise
            if result.returncode != 0:
                job.status = "failed"
                job.error = _tail(result.stderr_text or result.stdout_text)
                job.finished_at = time.time()
                await self._record(job)
                raise RenderError(
                    f"synfig exited with code {result.returncode}.",
                    hint=_render_hint(result.stderr_text or result.stdout_text),
                    context={"render_id": job.render_id, "output": str(output)},
                )
            job.status = "done"
            job.progress = 100.0
            job.finished_at = time.time()
            await self._record(job)
            return job

    async def cancel(self, render_id: str) -> bool:
        registry = get_process_registry()
        cancelled = await registry.cancel(render_id)
        if cancelled:
            job = await self.get(render_id)
            if job is not None:
                job.status = "cancelled"
                job.error = "cancelled by user"
                job.finished_at = time.time()
                await self._record(job)
        return cancelled


def _tail(text: str, *, max_chars: int = 1200) -> str:
    cleaned = text.strip()
    return cleaned[-max_chars:]


def _render_hint(text: str) -> str:
    lowered = text.lower()
    if "no such file" in lowered or "cannot open" in lowered:
        return "The input file may be missing or unreadable. Check the path and permissions."
    if "unknown layer" in lowered or "unknown valuenode" in lowered:
        return "The document references layer/converter types this synfig build cannot load."
    if "parse" in lowered or "xml" in lowered:
        return "The .sif document failed to parse; run validate_project for details."
    if "out of" in lowered and "memory" in lowered:
        return "Synfig ran out of memory. Lower resolution/frames or reduce antialias."
    return "Check synfig's stderr; run synfig_doctor and validate_project for diagnostics."


def verify_target(target: str, available: list[str]) -> str:
    normalized = target.strip().lower()
    aliases = {
        "mp4": "ffmpeg",
        "webm": "ffmpeg",
        "mov": "ffmpeg",
        "mkv": "ffmpeg",
        "jpg": "jpeg",
        "jpeg": "jpeg",
        "apng": "png",
        "webp": "ffmpeg",
        "sif": "sif",
        "lottie": "lottie",
    }
    resolved = aliases.get(normalized, normalized)
    if resolved not in available:
        supported = ", ".join(sorted(available)) or "none"
        raise UnsupportedTargetError(
            f"Render target {target!r} is not available in this synfig build.",
            hint=f"Available targets: {supported}. See list_render_targets.",
            context={"requested": target, "resolved": resolved, "available": sorted(available)},
        )
    return resolved


def build_render_args(
    *,
    target: str,
    output: str,
    width: int | None,
    height: int | None,
    time_s: float | None = None,
    begin_s: float | None = None,
    end_s: float | None = None,
    fps: float | None = None,
    antialias: int | None = None,
    quality: str | None = None,
    input_file: str | None = None,
    extra: list[str] | None = None,
    sequence_separator: str | None = None,
) -> list[str]:
    args: list[str] = ["-t", target]
    if width:
        args += ["-w", str(int(width))]
    if height:
        args += ["-h", str(int(height))]
    aa = antialias
    if aa is None and quality:
        aa = _QUALITY_ANTIALIAS.get(quality.lower())
    if aa:
        args += ["-a", str(int(aa))]
    if fps:
        args += ["--fps", f"{fps:.3f}"]
    if time_s is not None:
        from ..document.timeutil import format_time

        args += ["--time", format_time(time_s, fps=fps or 24.0)]
    else:
        if begin_s is not None and end_s is not None:
            from ..document.timeutil import format_time

            args += ["--begin-time", format_time(begin_s, fps=fps or 24.0)]
            args += ["--end-time", format_time(end_s, fps=fps or 24.0)]
    if sequence_separator:
        args += ["--sequence-separator", sequence_separator]
    if extra:
        args += list(extra)
    args += ["-o", str(output)]
    if input_file:
        args.append(str(input_file))
    return args
