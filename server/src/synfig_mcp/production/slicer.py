"""
Accurate cut-out slicer (Step 4).

``PartSlicer`` takes a source sprite sheet or layered raster and produces one
transparent PNG per part.  Three strategies are available, tried in order:

* ``grid`` - a uniform ``rows x cols`` grid, or explicit per-part rectangles;
* ``alpha`` - connected-component bounding boxes of the non-background pixels
  (delegated to :mod:`synfig_mcp.characters.sheet`, which already merges specks
  and nested highlights);
* ``trim`` - the ``alpha`` boxes, further trimmed to a polygon outline.

Outputs are hardened (re-encoded through Pillow, so no embedded payloads) and
returned as :class:`~synfig_mcp.characters.cutout.CutoutPart` entries with the
source rectangles needed by the ``in_place`` rig layout, ready for
``character_rig_from_parts``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image

from synfig_mcp.characters.cutout import CutoutPart
from synfig_mcp.characters.sheet import (
    MAX_SHEET_EDGE,
    detect_parts,
    foreground_mask,
    safe_part_name,
)
from synfig_mcp.errors import SynfigError

Strategy = Literal["grid", "alpha", "trim"]


class PartSlicer:
    """Cut a source image into named, rig-ready part PNGs."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)

    def slice(
        self,
        source: str | Path,
        strategy: Strategy = "alpha",
        rows: int = 1,
        cols: int = 1,
        rectangles: list[dict[str, Any]] | None = None,
        min_area: int | None = None,
        bg_tolerance: int = 28,
        padding: int = 2,
    ) -> dict[str, Any]:
        """Slice ``source`` and return ``{parts, manifest, ...}``.

        ``rectangles`` (when given) wins over the grid: each entry is
        ``{name, x, y, width, height}``.
        """
        source_path = Path(source)
        try:
            with Image.open(source_path) as handle:
                image = handle.convert("RGBA")
        except Exception as err:
            raise SynfigError(f"Cannot read source image '{source_path}': {err}") from err
        if max(image.size) > MAX_SHEET_EDGE:
            raise SynfigError(
                f"Source image is {image.width}x{image.height}; the longest edge may not exceed "
                f"{MAX_SHEET_EDGE} pixels."
            )

        rgba = np.asarray(image)
        boxes = self._boxes(
            rgba,
            image,
            strategy=strategy,
            rows=rows,
            cols=cols,
            rectangles=rectangles,
            min_area=min_area,
            bg_tolerance=bg_tolerance,
        )
        if not boxes:
            raise SynfigError(
                "No parts were found. For 'alpha'/'trim' the image needs a transparent or "
                "uniform background; for 'grid' check rows/cols; or pass explicit 'rectangles'."
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        parts: list[CutoutPart] = []
        written: list[dict[str, Any]] = []
        for index, (name, box, mask) in enumerate(boxes, start=1):
            safe = safe_part_name(name)
            x, y, w, h = box
            x0, y0 = max(0, x - padding), max(0, y - padding)
            x1, y1 = min(image.width, x + w + padding), min(image.height, y + h + padding)
            crop = rgba[y0:y1, x0:x1].copy()
            if mask is not None:
                own = mask[y0:y1, x0:x1]
                crop[..., 3] = np.where(own, crop[..., 3], 0)
            target = self.output_dir / f"{safe}.png"
            Image.fromarray(crop, "RGBA").save(target, format="PNG", optimize=True)
            parts.append(
                CutoutPart(
                    name=safe,
                    file=str(target),
                    bbox={
                        "x": float(x0),
                        "y": float(y0),
                        "width": float(x1 - x0),
                        "height": float(y1 - y0),
                    },
                )
            )
            written.append(
                {
                    "index": index,
                    "name": safe,
                    "file": str(target),
                    "bbox": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
                }
            )

        return {
            "success": True,
            "source": str(source_path),
            "source_size": {"width": image.width, "height": image.height},
            "strategy": strategy,
            "output_dir": str(self.output_dir),
            "detected_parts": len(written),
            "parts": written,
        }

    # -- strategies --------------------------------------------------------

    def _boxes(
        self,
        rgba: np.ndarray,
        image: Image.Image,
        *,
        strategy: Strategy,
        rows: int,
        cols: int,
        rectangles: list[dict[str, Any]] | None,
        min_area: int | None,
        bg_tolerance: int,
    ) -> list[tuple[str, tuple[int, int, int, int], np.ndarray | None]]:
        if rectangles:
            explicit: list[tuple[str, tuple[int, int, int, int], np.ndarray | None]] = []
            for index, item in enumerate(rectangles):
                explicit.append(
                    (
                        str(item.get("name", f"part_{index + 1:02d}")),
                        (
                            int(item["x"]),
                            int(item["y"]),
                            int(item["width"]),
                            int(item["height"]),
                        ),
                        None,
                    )
                )
            return explicit
        if strategy == "grid":
            if rows < 1 or cols < 1:
                raise SynfigError("Grid slicing needs rows >= 1 and cols >= 1.")
            return self._grid_boxes(image, rows, cols)

        mask, _method = foreground_mask(rgba, bg_tolerance=bg_tolerance)
        _labels, sheet_parts = detect_parts(mask, min_area=min_area)
        boxes: list[tuple[str, tuple[int, int, int, int], np.ndarray | None]] = []
        for part in sheet_parts:
            boxes.append((f"part_{part.index:02d}", part.bbox, np.isin(_labels, part.labels)))
        if strategy == "trim":
            boxes = [(name, self._trim(mask, box), own) for name, box, own in boxes]
        return boxes

    @staticmethod
    def _grid_boxes(
        image: Image.Image, rows: int, cols: int
    ) -> list[tuple[str, tuple[int, int, int, int], np.ndarray | None]]:
        cell_w = image.width / cols
        cell_h = image.height / rows
        boxes: list[tuple[str, tuple[int, int, int, int], np.ndarray | None]] = []
        index = 0
        for row in range(rows):
            for col in range(cols):
                index += 1
                x = int(round(col * cell_w))
                y = int(round(row * cell_h))
                w = int(round((col + 1) * cell_w)) - x
                h = int(round((row + 1) * cell_h)) - y
                boxes.append((f"cell_{index:02d}", (x, y, w, h), None))
        return boxes

    @staticmethod
    def _trim(mask: np.ndarray, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Tighten a box to the pixels actually set inside it."""
        x, y, w, h = box
        window = mask[y : y + h, x : x + w]
        ys, xs = np.nonzero(window)
        if len(xs) == 0:
            return box
        return (
            x + int(xs.min()),
            y + int(ys.min()),
            int(xs.max() - xs.min()) + 1,
            int(ys.max() - ys.min()) + 1,
        )
