"""
High-performance render and preview pipeline with frame sequencing, video encoding,
contact sheet generation, progress notifications, cancellation, and cache integration.
"""

import asyncio
import contextlib
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.errors import SynfigError
from synfig_mcp.logging import get_logger
from synfig_mcp.render.cache import RenderCache

logger = get_logger("synfig_mcp.render.pipeline")


class CancellationToken:
    """Thread-safe cooperative cancellation token."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def check(self) -> None:
        if self._cancelled:
            raise SynfigError("Render operation cancelled by user")


class RenderPipeline:
    """Coordinates frame, sequence, video, and contact sheet rendering over any BackendBase."""

    def __init__(self, backend: BackendBase, cache: RenderCache | None = None) -> None:
        self.backend = backend
        self.cache = cache or RenderCache()

    async def render_cached_frame(
        self,
        doc_id: str,
        output_path: str | Path,
        time: float | str = 0.0,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
    ) -> bool:
        """Render a single frame, checking disk cache first."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        # Get doc metadata for cache key
        info = await self.backend.doc_info(doc_id)
        w = width or (info.width if info else 1920)
        h = height or (info.height if info else 1080)
        t_sec = float(time) if isinstance(time, (int, float)) else 0.0

        cache_params = {
            "time": t_sec,
            "width": w,
            "height": h,
            "target": target,
        }
        # In headless, doc_id and undo count define doc state; in live, info defines it
        doc_state = await self.backend.get_doc_state(doc_id)
        cache_key = self.cache.compute_key(doc_state, cache_params)

        cached_file = self.cache.get(cache_key, ext=f".{target}")
        if cached_file and cached_file.exists():
            logger.info("Render cache hit for frame at time %.2fs: %s", t_sec, cache_key)
            shutil.copy2(cached_file, out_p)
            return True

        # Render freshly
        ok = await self.backend.render_frame(
            doc_id=doc_id,
            output_path=str(out_p),
            time=t_sec,
            width=w,
            height=h,
            target=target,
        )
        if ok and out_p.is_file():
            self.cache.put(cache_key, out_p, ext=f".{target}")
        return ok

    async def render_sequence(
        self,
        doc_id: str,
        output_dir: str | Path,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
        target: str = "png",
        progress_cb: Callable[[int, int, float], None] | None = None,
        cancel_token: CancellationToken | None = None,
        cleanup_on_cancel: bool = True,
    ) -> list[str]:
        """Render an image sequence across the timeline with progress tracking and cancellation."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        info = await self.backend.doc_info(doc_id)
        s_time = start_time if start_time is not None else (info.start_time if info else 0.0)
        e_time = end_time if end_time is not None else (info.end_time if info else 5.0)
        frame_rate = fps if fps is not None else (info.fps if info else 24.0)
        if frame_rate <= 0:
            frame_rate = 24.0

        duration = max(0.0, e_time - s_time)
        total_frames = max(1, int(round(duration * frame_rate)) + 1)

        generated_files: list[str] = []
        try:
            for i in range(total_frames):
                if cancel_token:
                    cancel_token.check()

                t = s_time + (i / frame_rate)
                frame_filename = out_dir / f"frame_{i:04d}.{target}"

                ok = await self.render_cached_frame(
                    doc_id=doc_id,
                    output_path=frame_filename,
                    time=t,
                    width=width,
                    height=height,
                    target=target,
                )
                if not ok or not frame_filename.is_file():
                    raise SynfigError(f"Failed to render frame {i} at timeline {t:.3f}s")

                generated_files.append(str(frame_filename.resolve()))

                if progress_cb:
                    pct = round((i + 1) / total_frames * 100.0, 1)
                    progress_cb(i + 1, total_frames, pct)

            return generated_files
        except SynfigError:
            if cancel_token and cancel_token.is_cancelled and cleanup_on_cancel:
                for f in generated_files:
                    with contextlib.suppress(Exception):
                        Path(f).unlink(missing_ok=True)
            raise

    async def render_video(
        self,
        doc_id: str,
        output_path: str | Path,
        start_time: float | None = None,
        end_time: float | None = None,
        fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
        progress_cb: Callable[[int, int, float], None] | None = None,
        cancel_token: CancellationToken | None = None,
    ) -> bool:
        """Render animation to video (.mp4, .avi, or .gif) via frame sequence and ffmpeg/Pillow."""
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        info = await self.backend.doc_info(doc_id)
        frame_rate = fps if fps is not None else (info.fps if info else 24.0)
        if frame_rate <= 0:
            frame_rate = 24.0

        suffix = out_p.suffix.lower()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_seq_dir = Path(tmp_dir) / "frames"
            frame_files = await self.render_sequence(
                doc_id=doc_id,
                output_dir=tmp_seq_dir,
                start_time=start_time,
                end_time=end_time,
                fps=frame_rate,
                width=width,
                height=height,
                target="png",
                progress_cb=progress_cb,
                cancel_token=cancel_token,
            )

            if not frame_files:
                raise SynfigError("No frames generated for video")

            if cancel_token:
                cancel_token.check()

            # 1. Animated GIF via Pillow
            if suffix == ".gif":
                frames = [Image.open(f) for f in frame_files]
                duration_ms = int(round(1000.0 / frame_rate))
                frames[0].save(
                    out_p,
                    save_all=True,
                    append_images=frames[1:],
                    duration=duration_ms,
                    loop=0,
                )
                return out_p.is_file()

            # 2. Video via ffmpeg
            ffmpeg_bin = shutil.which("ffmpeg") or r"C:\msys64\ucrt64\bin\ffmpeg.exe"
            if os.path.isfile(ffmpeg_bin) or shutil.which(ffmpeg_bin):
                input_pattern = str(tmp_seq_dir / "frame_%04d.png")
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-framerate",
                    str(frame_rate),
                    "-i",
                    input_pattern,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(out_p),
                ]
                proc = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                )
                if proc.returncode != 0:
                    logger.error("ffmpeg failed: %s", proc.stderr)
                    raise SynfigError(f"ffmpeg video encoding failed: {proc.stderr[:200]}")
                return out_p.is_file()

            # Fallback if no ffmpeg: assemble as GIF with renamed suffix warning
            logger.warning("ffmpeg not found on PATH; falling back to GIF animation")
            fallback_gif = out_p.with_suffix(".gif")
            frames = [Image.open(f) for f in frame_files]
            frames[0].save(
                fallback_gif,
                save_all=True,
                append_images=frames[1:],
                duration=int(1000.0 / frame_rate),
                loop=0,
            )
            shutil.copy2(fallback_gif, out_p)
            return out_p.is_file()

    async def render_contact_sheet(
        self,
        doc_id: str,
        output_path: str | Path,
        cols: int = 4,
        rows: int = 3,
        width: int | None = None,
        height: int | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> bool:
        """Render a tiled grid of frames sampled uniformly across the timeline."""
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        info = await self.backend.doc_info(doc_id)
        s_time = start_time if start_time is not None else (info.start_time if info else 0.0)
        e_time = end_time if end_time is not None else (info.end_time if info else 5.0)

        total_cells = cols * rows
        if total_cells <= 0:
            total_cells = 12

        duration = max(0.0, e_time - s_time)
        times = [s_time + (i / max(1, total_cells - 1)) * duration for i in range(total_cells)]

        thumb_w = (width or (info.width if info else 1920)) // cols
        thumb_h = (height or (info.height if info else 1080)) // rows
        sheet_w = thumb_w * cols
        sheet_h = thumb_h * rows

        sheet_img = Image.new("RGBA", (sheet_w, sheet_h), (30, 30, 30, 255))
        draw = ImageDraw.Draw(sheet_img)

        with tempfile.TemporaryDirectory() as tmp_dir:
            for idx, t in enumerate(times):
                thumb_path = Path(tmp_dir) / f"thumb_{idx:02d}.png"
                ok = await self.render_cached_frame(
                    doc_id=doc_id,
                    output_path=thumb_path,
                    time=t,
                    width=thumb_w,
                    height=thumb_h,
                    target="png",
                )
                if not ok or not thumb_path.is_file():
                    continue

                col_idx = idx % cols
                row_idx = idx // cols
                x_pos = col_idx * thumb_w
                y_pos = row_idx * thumb_h

                with Image.open(thumb_path) as thumb:
                    sheet_img.paste(thumb, (x_pos, y_pos))

                # Draw timestamp badge
                badge_text = f"{t:.2f}s"
                draw.rectangle(
                    (x_pos + 4, y_pos + 4, x_pos + 48, y_pos + 18),
                    fill=(0, 0, 0, 180),
                )
                draw.text((x_pos + 6, y_pos + 5), badge_text, fill=(255, 255, 255, 255))

            sheet_img.save(out_p)
            return out_p.is_file()
