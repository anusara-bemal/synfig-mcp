# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Render tools: frames, animations, previews, thumbnails, job management."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

import mcp.types as mcp_types
from mcp.server.fastmcp import Context, Image

from ..cli.render import build_render_args, verify_target
from ..document import io
from ..document.timeutil import format_time, parse_time
from ..errors import ParameterError
from ..security.paths import ensure_output_path
from .common import AppContext, json_dumps, tool

FastMCPContext = Context[Any, Any, Any]

PREVIEW_WIDTH = 480
THUMB_WIDTH = 256


async def _render_input(ctx: AppContext, session, job_id: str):  # type: ignore[no-untyped-def]
    """Return (input_path, temp_path_or_None). Save a snapshot if unsaved."""
    if session.path and not session.dirty:
        return session.path, None
    tmp_dir = ctx.settings.workspace / ".synfig-mcp" / "render-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"render-{job_id}.sifz"
    io.write_project(session.tree, tmp_path, backup=False)
    return tmp_path, tmp_path


async def _prepare(
    ctx: AppContext,
    project_id: str,
    target: str,
    output: str | None,
    default_suffix: str,
    width: int | None,
    height: int | None,
    begin_s: float | None,
    end_s: float | None,
    fps: float | None,
) -> tuple[Any, int, int, int, str, Path]:
    settings = ctx.settings
    session = await ctx.registry.get(project_id)
    canvas_w = int(session.root.get("width", "0") or 0)
    canvas_h = int(session.root.get("height", "0") or 0)
    width = int(width or canvas_w)
    height = int(height or canvas_h)
    ctx.registry.limits.check_resolution(width, height)
    frame_count = 1
    if begin_s is not None and end_s is not None:
        frame_count = max(1, int((end_s - begin_s) * float(fps or 24.0)) + 1)
        ctx.registry.limits.check_frames(frame_count)
        ctx.registry.limits.check_render_pixels(width, height, frame_count)
    path = ensure_output_path(
        output,
        settings.workspace,
        default_name=f"{_base_name(session)}{default_suffix}",
        purpose="render output",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return session, width, height, frame_count, target, path


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def render_frame(
        project_id: str,
        output: str | None = None,
        width: int | None = None,
        height: int | None = None,
        time: str = "0f",
        quality: str | None = None,
        antialias: int | None = None,
        span: float | None = None,
        return_image: bool = True,
        context: FastMCPContext | None = None,
    ) -> Any:
        """Render a single frame to PNG.

        Returns JSON with the output path; if return_image=true the PNG is
        also attached as MCP image content. Unsaved changes are rendered from
        a temporary snapshot.
        """
        binary = ctx.require_binary()
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        time_s = parse_time(time, fps=fps)
        available_targets = await _targets(ctx)
        target = verify_target("png", available_targets)
        _, width, height, _, _, path = await _prepare(
            ctx, project_id, target, output, ".png", width, height, None, None, fps
        )
        job_id = _new_job_id()
        input_path, tmp_path = await _render_input(ctx, session, job_id)

        progress_cb = _make_progress_cb(context)
        args = build_render_args(
            target=target,
            output=str(path),
            width=width,
            height=height,
            time_s=time_s,
            fps=fps,
            antialias=antialias,
            quality=quality,
            input_file=str(input_path),
            extra=["--span", str(span)] if span else None,
        )
        binary = ctx.require_binary()
        try:
            job = await ctx.render_manager.run_render(
                kind="frame",
                binary=binary,
                args=args,
                target=target,
                output=str(path),
                progress_cb=progress_cb,
            )
        finally:
            if tmp_path is not None:
                _cleanup_tmp(tmp_path)
        payload = {
            "project_id": project_id,
            "render_id": job.render_id,
            "output": str(path),
            "target": target,
            "width": width,
            "height": height,
            "time": format_time(time_s, fps=fps),
            "status": job.status,
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        if return_image and path.exists() and path.suffix.lower() == ".png":
            png_bytes = path.read_bytes()
            return [
                mcp_types.TextContent(type="text", text=json_dumps(payload)),
                Image(data=png_bytes, format="png"),
            ]
        return json_dumps(payload)

    @tool(server)
    async def render_animation(
        project_id: str,
        target: str = "gif",
        output: str | None = None,
        width: int | None = None,
        height: int | None = None,
        begin_time: str | None = None,
        end_time: str | None = None,
        fps: float | None = None,
        quality: str | None = None,
        antialias: int | None = None,
        video_codec: str | None = None,
        video_bitrate: str | None = None,
        sprite_separator: str | None = None,
        context: FastMCPContext | None = None,
    ) -> str:
        """Render an animation.

        target: gif, ffmpeg (mp4/webm), png (sequence), png-spritesheet, bmp,
        jpeg, ppm. Targets not present in this synfig build fail with a
        clear error listing what's available. lottie is not supported by
        synfig and always fails with an actionable message.
        """
        binary = ctx.require_binary()
        requested = target.strip().lower()
        if requested in {"lottie", "sif"}:
            from ..errors import UnsupportedTargetError

            raise UnsupportedTargetError(
                f"Render target {target!r} is not supported by Synfig.",
                hint="Synfig cannot export .sif or lottie directly. Use '.sif' flattening in Studio, or render png sequence and post-process.",
                context={"requested": requested},
            )
        available_targets = await _targets(ctx)
        resolved = verify_target(requested, available_targets)
        session = await ctx.registry.get(project_id)
        canvas_fps = float(session.root.get("fps", "24") or 24)
        fps = float(fps or canvas_fps)
        begin_s = (
            parse_time(begin_time, fps=fps)
            if begin_time is not None
            else parse_time(session.root.get("begin-time", "0f"), fps=fps)
        )
        end_s = (
            parse_time(end_time, fps=fps)
            if end_time is not None
            else parse_time(session.root.get("end-time", "0f"), fps=fps)
        )
        if end_s < begin_s:
            raise ParameterError("end_time must be >= begin_time.")
        default_suffix = {
            "gif": ".gif",
            "ffmpeg": ".mp4",
            "libav": ".mp4",
            "png": "",
            "png-spritesheet": ".png",
            "bmp": ".bmp",
            "jpeg": ".jpg",
            "ppm": ".ppm",
        }.get(resolved, ".out")
        _, width, height, frame_count, _, path = await _prepare(
            ctx, project_id, resolved, output, default_suffix, width, height, begin_s, end_s, fps
        )
        job_id = _new_job_id()
        input_path, tmp_path = await _render_input(ctx, session, job_id)
        progress_cb = _make_progress_cb(context)
        extra: list[str] = []
        if video_codec and resolved in {"ffmpeg", "libav"}:
            extra += [f"--video-codec={video_codec}"]
        if video_bitrate and resolved in {"ffmpeg", "libav"}:
            extra += [f"--video-bitrate={video_bitrate}"]
        if sprite_separator:
            extra += [f"--sequence-separator={sprite_separator}"]
        args = build_render_args(
            target=resolved,
            output=str(path),
            width=width,
            height=height,
            begin_s=begin_s,
            end_s=end_s,
            fps=fps,
            antialias=antialias,
            quality=quality,
            input_file=str(input_path),
            extra=extra,
        )
        binary = ctx.require_binary()
        try:
            job = await ctx.render_manager.run_render(
                kind="animation",
                binary=binary,
                args=args,
                target=resolved,
                output=str(path),
                progress_cb=progress_cb,
            )
        finally:
            if tmp_path is not None:
                _cleanup_tmp(tmp_path)
        return json_dumps(
            {
                "project_id": project_id,
                "render_id": job.render_id,
                "output": str(path),
                "target": resolved,
                "width": width,
                "height": height,
                "fps": fps,
                "frames": frame_count,
                "begin_time": format_time(begin_s, fps=fps),
                "end_time": format_time(end_s, fps=fps),
                "status": job.status,
            }
        )

    @tool(server)
    async def render_preview(
        project_id: str,
        time: str | None = None,
        width: int = PREVIEW_WIDTH,
        context: FastMCPContext | None = None,
    ) -> Any:
        """Fast low-quality preview of a frame (default: current canvas start time)."""
        session = await ctx.registry.get(project_id)
        canvas_h = int(session.root.get("height", "512") or 512)
        canvas_w = int(session.root.get("width", "512") or 512)
        height = max(1, round(canvas_h * (width / canvas_w))) if canvas_w else width
        return await render_frame(
            project_id=project_id,
            width=width,
            height=height,
            time=time or session.root.get("begin-time", "0f") or "0f",
            quality="low",
            context=context,
        )

    @tool(server)
    async def render_thumbnail(
        project_id: str,
        output: str | None = None,
        time: str | None = None,
        size: int = THUMB_WIDTH,
        context: FastMCPContext | None = None,
    ) -> Any:
        """Small square-ish thumbnail of the canvas (default 256px wide)."""
        session = await ctx.registry.get(project_id)
        canvas_h = int(session.root.get("height", "512") or 512)
        canvas_w = int(session.root.get("width", "512") or 512)
        height = max(1, round(canvas_h * (size / canvas_w))) if canvas_w else size
        return await render_frame(
            project_id=project_id,
            output=output,
            width=size,
            height=height,
            time=time or session.root.get("begin-time", "0f") or "0f",
            quality="low",
            return_image=True,
            context=context,
        )

    @tool(server)
    async def get_render_status(render_id: str | None = None) -> str:
        """List recent render jobs (or one job when render_id is given)."""
        manager = ctx.render_manager
        if render_id:
            job = await manager.get(render_id)
            if job is None:
                return json_dumps({"render_id": render_id, "found": False})
            return json_dumps({"render_id": render_id, "found": True, "job": job.to_dict()})
        jobs = [job.to_dict() for job in await manager.list_jobs()]
        return json_dumps({"jobs": jobs})

    @tool(server)
    async def cancel_render(render_id: str) -> str:
        """Cancel a running render by id."""
        cancelled = await ctx.render_manager.cancel(render_id)
        return json_dumps({"render_id": render_id, "cancelled": bool(cancelled)})


async def _targets(ctx: AppContext) -> list[str]:
    probed = await ctx.probe()
    if probed.get("found"):
        raw_targets = probed.get("targets", [])
        if isinstance(raw_targets, list):
            return [str(t) for t in raw_targets]
    return []


def _new_job_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


def _cleanup_tmp(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink()


def _make_progress_cb(context: FastMCPContext | None) -> Any:
    if context is None:
        return None

    def cb(pct: float) -> None:
        with contextlib.suppress(RuntimeError):
            asyncio.get_event_loop().create_task(context.report_progress(pct, 100.0))

    return cb


def _base_name(session) -> str:  # type: ignore[no-untyped-def]
    name = getattr(session, "name", None) or "project"
    safe = "".join(ch for ch in str(name) if ch not in '<>:"/\\|?*').strip()
    return safe or "project"
