"""
Visual Review Service orchestrator: produces rendered frames/contact-sheets
and pairs them with objective computer-vision metrics for LLM critique.
"""

from __future__ import annotations

import base64
import io
import math
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.review.metrics import (
    check_empty_or_uniform,
    check_safe_areas,
    compute_frame_motion,
    detect_flash_strobe,
    detect_luminance_clipping,
    extract_dominant_palette,
    generate_diff_heatmap,
)


def _image_to_base64(img: Image.Image) -> str:
    """Helper to convert PIL Image to PNG base64 string."""
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class ReviewService:
    """Service providing visual review actions paired with objective metrics."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    async def review_frame(
        self,
        doc_id: str = "doc_0",
        time: float = 0.0,
        focus_region: list[int] | None = None,
        width: int = 320,
        height: int = 240,
    ) -> dict[str, Any]:
        """
        Render a single frame and evaluate objective vision metrics.
        Returns: {image_base64, metrics: {clipping, safe_area, palette, empty_check}, warnings}
        """
        with tempfile.TemporaryDirectory() as td:
            out_png = Path(td) / "review_frame.png"
            await self.backend.render_frame(
                doc_id=doc_id,
                output_path=str(out_png),
                width=width,
                height=height,
                time=time,
            )
            pil_img = Image.open(out_png).convert("RGBA")
            arr = np.array(pil_img)

        # Apply crop if focus_region specified [x, y, w, h]
        cropped = False
        if focus_region and len(focus_region) == 4:
            fx, fy, fw, fh = focus_region
            pil_img = pil_img.crop((fx, fy, fx + fw, fy + fh))
            cropped = True

        empty_res = check_empty_or_uniform(arr)
        clipping_res = detect_luminance_clipping(arr)
        safe_res = check_safe_areas(arr)
        palette = extract_dominant_palette(arr, k=5)

        all_warnings = (
            empty_res.get("warnings", [])
            + clipping_res.get("warnings", [])
            + safe_res.get("warnings", [])
        )

        return {
            "doc_id": doc_id,
            "time": time,
            "resolution": f"{width}x{height}",
            "cropped": cropped,
            "image_base64": _image_to_base64(pil_img),
            "metrics": {
                "empty_canvas": empty_res["is_empty"],
                "uniform_canvas": empty_res["is_uniform"],
                "crushed_black": clipping_res["crushed_black"],
                "blown_highlight": clipping_res["blown_highlight"],
                "boundary_clipping": safe_res["boundary_clipping_detected"],
                "dominant_palette": palette,
            },
            "warnings": all_warnings,
            "rubrics_resource": "synfig://rubrics/general",
        }

    async def review_sequence(
        self,
        doc_id: str = "doc_0",
        start_time: float = 0.0,
        end_time: float = 1.0,
        frame_count: int = 4,
        width: int = 320,
        height: int = 240,
    ) -> dict[str, Any]:
        """
        Render a sequence of frames, compile into a contact sheet, and check motion + photosensitivity.
        """
        frame_count = max(2, min(frame_count, 9))
        step = (end_time - start_time) / (frame_count - 1) if frame_count > 1 else 0.0
        times = [start_time + i * step for i in range(frame_count)]

        frames_pil: list[Image.Image] = []
        frames_np: list[np.ndarray] = []

        with tempfile.TemporaryDirectory() as td:
            for idx, t in enumerate(times):
                out_png = Path(td) / f"frame_{idx:03d}.png"
                await self.backend.render_frame(
                    doc_id=doc_id,
                    output_path=str(out_png),
                    width=width,
                    height=height,
                    time=t,
                )
                f_pil = Image.open(out_png).convert("RGB")
                frames_pil.append(f_pil)
                frames_np.append(np.array(f_pil))

        # Check strobe / photosensitivity
        strobe_res = detect_flash_strobe(frames_np, fps=24.0)

        # Compute adjacent frame motion
        motion_deltas: list[dict[str, Any]] = []
        for i in range(1, len(frames_np)):
            m = compute_frame_motion(frames_np[i - 1], frames_np[i])
            motion_deltas.append(
                {
                    "from_time": times[i - 1],
                    "to_time": times[i],
                    **m,
                }
            )

        # Assemble contact sheet grid
        cols = 2 if frame_count <= 4 else 3
        rows = math.ceil(frame_count / cols)
        sheet_w = cols * width
        sheet_h = rows * height
        sheet = Image.new("RGB", (sheet_w, sheet_h), color=(20, 20, 20))

        for idx, f_img in enumerate(frames_pil):
            r = idx // cols
            c = idx % cols
            sheet.paste(f_img, (c * width, r * height))

        return {
            "doc_id": doc_id,
            "times": times,
            "frame_count": frame_count,
            "contact_sheet_base64": _image_to_base64(sheet),
            "strobe_check": strobe_res,
            "motion_stats": motion_deltas,
            "warnings": strobe_res.get("warnings", []),
        }

    async def review_compare(
        self,
        doc_id_a: str = "doc_0",
        time_a: float = 0.0,
        doc_id_b: str = "doc_0",
        time_b: float = 0.0,
        width: int = 320,
        height: int = 240,
    ) -> dict[str, Any]:
        """
        Compare two animation iterations/frames, generate a diff heatmap, and calculate SSIM.
        """
        with tempfile.TemporaryDirectory() as td:
            out_a = Path(td) / "frame_a.png"
            out_b = Path(td) / "frame_b.png"

            await self.backend.render_frame(
                doc_id=doc_id_a, output_path=str(out_a), width=width, height=height, time=time_a
            )
            await self.backend.render_frame(
                doc_id=doc_id_b, output_path=str(out_b), width=width, height=height, time=time_b
            )

            img_a = Image.open(out_a).convert("RGB")
            img_b = Image.open(out_b).convert("RGB")
            arr_a = np.array(img_a)
            arr_b = np.array(img_b)

        motion = compute_frame_motion(arr_a, arr_b)
        heatmap = generate_diff_heatmap(arr_a, arr_b)

        # Assemble side-by-side composite: A | B | Heatmap
        side_by_side = Image.new("RGB", (width * 3, height))
        side_by_side.paste(img_a, (0, 0))
        side_by_side.paste(img_b, (width, 0))
        side_by_side.paste(heatmap, (width * 2, 0))

        return {
            "comparison": {
                "a": {"doc_id": doc_id_a, "time": time_a},
                "b": {"doc_id": doc_id_b, "time": time_b},
            },
            "ssim": motion["ssim"],
            "pixel_change_ratio": motion["pixel_change_ratio"],
            "mean_pixel_delta": motion["mean_pixel_delta"],
            "heatmap_composite_base64": _image_to_base64(side_by_side),
        }
