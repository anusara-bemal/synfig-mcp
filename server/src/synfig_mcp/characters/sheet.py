"""
Rig sheet slicing: turn one character sheet image into separate, transparent part images.

A rig sheet is a single picture with the body parts of a cut-out character laid
out next to each other.  ``slice_rig_sheet`` finds every part (connected
component of non-background pixels), crops it to its own PNG and writes a
manifest.  It also draws a numbered preview so that a vision-capable MCP client
can look at the sheet once and name the parts ("3 is the head").

Only numpy and Pillow are used; the labelling is a run-based union-find, which
is fast enough for 4K sheets without SciPy.
"""

from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from synfig_mcp.errors import SynfigError

#: Largest sheet edge that is analysed at full resolution.
MAX_SHEET_EDGE = 8192
#: Longest edge of the numbered preview handed back to the client.
PREVIEW_EDGE = 768
#: Enclosed-hole fill is reported for approval above this share of the foreground.
APPROVAL_HOLE_FRACTION = 0.02

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_]+")


def safe_part_name(name: str) -> str:
    """Normalise a part name so that it is usable as a file name and a layer id."""
    cleaned = _SAFE_NAME.sub("_", name.strip()).strip("_").lower()
    return cleaned or "part"


@dataclass
class SheetPart:
    """One part found on a rig sheet, plus the rig metadata derived from its name."""

    index: int
    bbox: tuple[int, int, int, int]  # x, y, width, height in sheet pixels
    area: int
    name: str = ""
    file: str = ""
    labels: list[int] = field(default_factory=list)
    role: str | None = None
    parent: str | None = None
    pivot: tuple[float, float] | None = None  # fractions of the part image
    z: float = 0.0
    transparency: float = 0.0  # fraction of transparent pixels in the crop
    confidence: float = 1.0  # heuristic 0..1; low means "look at the preview"
    reconstructed_pixels: int = 0

    def as_dict(self) -> dict[str, Any]:
        x, y, w, h = self.bbox
        return {
            "index": self.index,
            "name": self.name,
            "file": self.file,
            "bbox": {"x": x, "y": y, "width": w, "height": h},
            "area": self.area,
            "role": self.role,
            "parent": self.parent,
            "pivot": (
                {"fx": self.pivot[0], "fy": self.pivot[1]} if self.pivot is not None else None
            ),
            "z": self.z,
            "transparency": round(self.transparency, 4),
            "confidence": round(self.confidence, 2),
            "reconstructed_pixels": self.reconstructed_pixels,
        }


# ---------------------------------------------------------------------------
# Connected component labelling (8-connectivity, run based)
# ---------------------------------------------------------------------------


def _row_runs(row: np.ndarray) -> list[tuple[int, int]]:
    """Return the [start, end) runs of True values in a boolean row."""
    if not row.any():
        return []
    padded = np.concatenate(([False], row, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    return list(zip(edges[0::2].tolist(), edges[1::2].tolist(), strict=True))


def label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Label the 8-connected components of a boolean mask.

    Returns ``(labels, count)`` where ``labels`` has 0 for background and
    ``1..count`` for the components.
    """
    height, width = mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    parent: list[int] = [0]

    def find(item: int) -> int:
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    previous: list[tuple[int, int, int]] = []
    for y in range(height):
        current: list[tuple[int, int, int]] = []
        pointer = 0
        for start, end in _row_runs(mask[y]):
            label = 0
            # Runs of the previous row that touch this run (diagonals included).
            while pointer < len(previous) and previous[pointer][1] < start:
                pointer += 1
            probe = pointer
            while probe < len(previous) and previous[probe][0] <= end:
                other = find(previous[probe][2])
                if label == 0:
                    label = other
                elif other != label:
                    low, high = (label, other) if label < other else (other, label)
                    parent[high] = low
                    label = low
                probe += 1
            if label == 0:
                label = len(parent)
                parent.append(label)
            labels[y, start:end] = label
            current.append((start, end, label))
        previous = current

    # Compact the label ids.
    lookup = np.zeros(len(parent), dtype=np.int32)
    count = 0
    remap: dict[int, int] = {}
    for label in range(1, len(parent)):
        root = find(label)
        if root not in remap:
            count += 1
            remap[root] = count
        lookup[label] = remap[root]
    return lookup[labels], count


# ---------------------------------------------------------------------------
# Foreground detection
# ---------------------------------------------------------------------------


def foreground_mask(rgba: np.ndarray, bg_tolerance: int = 28) -> tuple[np.ndarray, str]:
    """Return the foreground mask of a sheet and how the background was detected.

    A sheet with real transparency uses its alpha channel.  An opaque sheet uses
    the border colour: only background-coloured pixels that are *connected to
    the border* count as background, so white eyes on a white sheet survive.
    """
    alpha = rgba[..., 3]
    transparent = float((alpha < 16).mean())
    if transparent > 0.01:
        return alpha >= 16, "alpha"

    rgb = rgba[..., :3].astype(np.int16)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg_colour = np.median(border, axis=0)
    distance = np.abs(rgb - bg_colour).max(axis=-1)
    similar = distance <= bg_tolerance

    labels, _count = label_components(similar)
    edge_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    edge_labels = edge_labels[edge_labels != 0]
    background = np.isin(labels, edge_labels)
    return ~background, "border_colour"


# ---------------------------------------------------------------------------
# Part detection
# ---------------------------------------------------------------------------


def _bbox_gap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    """Pixel gap between two x0,y0,x1,y1 boxes (0 when they touch or overlap)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return max(dx, dy)


def _contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def detect_parts(
    mask: np.ndarray,
    min_area: int | None = None,
    merge_gap: int = 6,
) -> tuple[np.ndarray, list[SheetPart]]:
    """Find the parts of a sheet.

    Specks smaller than ``min_area`` are attached to a part within ``merge_gap``
    pixels (a detached highlight, an eyebrow) or dropped as noise.  A component
    that lies completely inside the bounding box of a bigger one is merged into
    it.  The parts are returned in reading order.
    """
    labels, count = label_components(mask)
    if count == 0:
        return labels, []

    height, width = mask.shape
    if min_area is None:
        min_area = max(48, int(width * height * 0.0004))

    areas = np.bincount(labels.ravel(), minlength=count + 1)
    boxes: dict[int, tuple[int, int, int, int]] = {}
    ys, xs = np.nonzero(labels)
    values = labels[ys, xs]
    order = np.argsort(values, kind="stable")
    values, ys, xs = values[order], ys[order], xs[order]
    starts = np.flatnonzero(np.concatenate(([True], values[1:] != values[:-1])))
    ends = np.concatenate((starts[1:], [len(values)]))
    for start, end in zip(starts.tolist(), ends.tolist(), strict=True):
        label = int(values[start])
        boxes[label] = (
            int(xs[start:end].min()),
            int(ys[start:end].min()),
            int(xs[start:end].max()) + 1,
            int(ys[start:end].max()) + 1,
        )

    big = sorted((lb for lb in boxes if areas[lb] >= min_area), key=lambda lb: -int(areas[lb]))
    small = [lb for lb in boxes if areas[lb] < min_area]

    groups: list[dict[str, Any]] = []
    for label in big:
        box = boxes[label]
        host = next((g for g in groups if _contains(g["box"], box)), None)
        if host is not None:
            host["labels"].append(label)
            host["area"] += int(areas[label])
        else:
            groups.append({"box": box, "labels": [label], "area": int(areas[label])})

    for label in small:
        box = boxes[label]
        best: dict[str, Any] | None = None
        best_gap = merge_gap + 1
        for group in groups:
            gap = _bbox_gap(group["box"], box)
            if gap < best_gap:
                best, best_gap = group, gap
        if best is not None:
            best["labels"].append(label)
            best["area"] += int(areas[label])
            old = best["box"]
            best["box"] = (
                min(old[0], box[0]),
                min(old[1], box[1]),
                max(old[2], box[2]),
                max(old[3], box[3]),
            )

    # Reading order: rows of parts from top to bottom, left to right inside a row.
    groups.sort(key=lambda g: (g["box"][1], g["box"][0]))
    rows: list[list[dict[str, Any]]] = []
    for group in groups:
        centre = (group["box"][1] + group["box"][3]) / 2
        if rows and centre < max(g["box"][3] for g in rows[-1]):
            rows[-1].append(group)
        else:
            rows.append([group])

    parts: list[SheetPart] = []
    for row in rows:
        for group in sorted(row, key=lambda g: g["box"][0]):
            x0, y0, x1, y1 = group["box"]
            parts.append(
                SheetPart(
                    index=len(parts) + 1,
                    bbox=(x0, y0, x1 - x0, y1 - y0),
                    area=group["area"],
                    labels=list(group["labels"]),
                )
            )
    return labels, parts


# ---------------------------------------------------------------------------
# Best-effort reconstruction and rig metadata
# ---------------------------------------------------------------------------


def fill_enclosed_holes(crop: np.ndarray, mask: np.ndarray, limit: int) -> tuple[np.ndarray, int]:
    """Fill background pixels fully enclosed by a part (occlusion reconstruction).

    A hole is background that the border of the crop cannot reach, i.e. an area
    the part paints around - a gap left where a limb covered the torso on the
    sheet.  Each hole is inpainted with the median colour of the surrounding
    opaque pixels so the part stays a single opaque silhouette.  Holes larger
    than ``limit`` pixels are left transparent: that is a deliberate cut-out
    (a mouth, a gap between the legs), not missing artwork.

    Returns ``(rgba, filled_pixel_count)``.
    """
    height, width = mask.shape
    outside = np.zeros((height, width), dtype=bool)
    stack: list[tuple[int, int]] = []
    for x in range(width):
        for y in (0, height - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                stack.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                stack.append((y, x))
    while stack:
        y, x = stack.pop()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and not mask[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                stack.append((ny, nx))

    holes = ~mask & ~outside
    if not holes.any():
        return crop, 0

    labels, count = label_components(holes)
    filled = 0
    for label in range(1, count + 1):
        blob = labels == label
        size = int(blob.sum())
        if size > limit:
            continue
        ring = np.zeros_like(blob)
        ys, xs = np.nonzero(blob)
        y0, y1 = max(0, ys.min() - 1), min(height, ys.max() + 2)
        x0, x1 = max(0, xs.min() - 1), min(width, xs.max() + 2)
        ring[y0:y1, x0:x1] = True
        ring &= ~blob
        ring &= mask
        if not ring.any():
            continue
        colour = np.median(crop[ring][:, :3], axis=0).astype(np.uint8)
        crop[blob, 0:3] = colour
        crop[blob, 3] = 255
        filled += size
    return crop, filled


def infer_pivot(role: str | None) -> tuple[float, float]:
    """Return the joint pivot (fractions of the part image) for a role."""
    from synfig_mcp.characters.cutout import HUMANOID, split_role

    base, _side = split_role(role)
    default = HUMANOID.get(base or "")
    if default is not None:
        return default.pivot
    return (0.5, 0.5)


def _role_z(role: str | None) -> float:
    """Default stacking for a role (matches the cut-out assembly defaults)."""
    from synfig_mcp.characters.cutout import HUMANOID, split_role

    base, side = split_role(role)
    default = HUMANOID.get(base or "")
    if default is None:
        return 0.0
    return default.z_left if side == "l" else default.z_right


def rig_compatibility(parts: list[SheetPart]) -> dict[str, Any]:
    """Assess how well a set of named parts assembles into a cut-out rig.

    The checks mirror the assembly rules in :mod:`synfig_mcp.characters.cutout`:
    every part should resolve to a known anatomical role, the rig needs a
    torso/hips root, and every non-root part needs a parent role that is present.
    Parts may sit anywhere on the sheet (assembly joins them at their pivots, not
    at their sheet positions), so layout is not part of this check.  Results are
    heuristic - they flag what a human should confirm, they do not block the
    slice.
    """
    from synfig_mcp.characters.cutout import HUMANOID, split_role

    named = [p for p in parts if p.name and not p.name.startswith("part_")]
    if not named:
        return {
            "level": "unknown",
            "score": 0.0,
            "issues": ["no named parts"],
            "hint": "Name parts by body role (head, torso, upper_arm_l, ...) then slice again.",
        }

    roles = {p.name: p.role for p in named}
    owners: dict[str, str] = {}
    for name, role in roles.items():
        if role and role not in owners:
            owners[role] = name

    root_name = owners.get("torso") or owners.get("hips")
    known_roles = set(HUMANOID) | {"torso", "hips"}
    issues: list[str] = []
    if root_name is None:
        issues.append("no 'torso' or 'hips' part to root the rig on")

    for part in named:
        base, side = split_role(part.role)
        if part.name == root_name:
            part.parent = None
            continue
        if base is None or base not in known_roles:
            issues.append(f"part '{part.name}' has an unrecognized role")
            part.parent = root_name
            continue
        candidates = list(HUMANOID[base].parents) if base in HUMANOID else ["torso", "hips"]
        parent = next(
            (
                owners.get(f"{c}_{side}") or owners.get(c)
                for c in candidates
                if owners.get(f"{c}_{side}") or owners.get(c)
            ),
            None,
        )
        part.parent = parent
        if parent is None:
            issues.append(f"part '{part.name}' has no parent role present")

    present_roles = {r for r in roles.values() if r}
    score = round(len(present_roles & known_roles) / max(1, len(known_roles)), 2)
    level = ("low" if len(issues) > 2 else "medium") if issues else "high"
    return {
        "level": level,
        "score": score,
        "roles": sorted(present_roles),
        "missing_roles": sorted(set(HUMANOID) - present_roles),
        "issues": issues,
    }


def _assign_metadata(part: SheetPart, crop: np.ndarray) -> None:
    """Fill a part's role/parent/pivot/z/transparency/confidence from its name and pixels."""
    from synfig_mcp.characters.cutout import infer_role

    part.role = infer_role(part.name)
    part.pivot = infer_pivot(part.role)
    part.transparency = float((crop[..., 3] < 16).mean())
    part.z = _role_z(part.role)
    if part.role:
        part.confidence = 0.9 if not part.name.startswith("part_") else 0.5
    else:
        part.confidence = 0.4


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _preview(image: Image.Image, parts: list[SheetPart]) -> str:
    """Draw numbered boxes over the sheet and return a base64 PNG."""
    scale = min(1.0, PREVIEW_EDGE / max(image.size))
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    canvas.alpha_composite(image.resize(size, Image.Resampling.LANCZOS))
    draw = ImageDraw.Draw(canvas)
    for part in parts:
        x, y, w, h = part.bbox
        box = (x * scale, y * scale, (x + w) * scale - 1, (y + h) * scale - 1)
        draw.rectangle(box, outline=(230, 30, 60, 255), width=2)
        label = f"{part.index}" + (f" {part.name}" if part.name else "")
        text_box = draw.textbbox((box[0] + 3, box[1] + 2), label)
        draw.rectangle(
            (text_box[0] - 2, text_box[1] - 1, text_box[2] + 2, text_box[3] + 1),
            fill=(230, 30, 60, 255),
        )
        draw.text((box[0] + 3, box[1] + 2), label, fill=(255, 255, 255, 255))
    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def slice_rig_sheet(
    sheet_path: Path,
    output_dir: Path,
    names: dict[str, str] | None = None,
    min_area: int | None = None,
    merge_gap: int = 6,
    bg_tolerance: int = 28,
    padding: int = 2,
    preview: bool = True,
    reconstruct: bool = True,
    source: str = "file_path",
) -> dict[str, Any]:
    """Slice a rig sheet into one transparent PNG per part.

    ``names`` maps the part number (as shown in the preview) to a part name, for
    example ``{"1": "head", "2": "torso"}``.  When names are given only the named
    parts are written, which is how captions and stray marks on a sheet are
    left out.  Without names every part is written as ``part_NN``.

    With ``reconstruct`` the parts get a best-effort occlusion fill (enclosed
    gaps are inpainted) and each part is annotated with the rig metadata derived
    from its name (role, parent, pivot, z) plus transparency and a confidence
    score, so a client can feed the manifest straight into
    ``character_rig_from_parts``.  ``source`` records where the sheet came from
    (``file_path`` or ``image_content``).
    """
    try:
        with Image.open(sheet_path) as source_image:
            image = source_image.convert("RGBA")
    except Exception as err:
        raise SynfigError(f"Cannot read rig sheet '{sheet_path}': {err}") from err

    if max(image.size) > MAX_SHEET_EDGE:
        raise SynfigError(
            f"Rig sheet is {image.width}x{image.height}; the longest edge may not exceed "
            f"{MAX_SHEET_EDGE} pixels."
        )

    rgba = np.asarray(image)
    mask, method = foreground_mask(rgba, bg_tolerance=bg_tolerance)
    labels, parts = detect_parts(mask, min_area=min_area, merge_gap=merge_gap)
    if not parts:
        raise SynfigError(
            "No parts were found on the rig sheet. The sheet needs a transparent or a "
            "uniform background; try a larger bg_tolerance or a smaller min_area."
        )

    wanted: dict[int, str] = {}
    if names:
        for key, value in names.items():
            try:
                index = int(key)
            except (TypeError, ValueError) as err:
                raise SynfigError(f"names keys must be part numbers, got '{key}'.") from err
            if not 1 <= index <= len(parts):
                raise SynfigError(
                    f"names refers to part {index}, but the sheet has parts 1..{len(parts)}."
                )
            wanted[index] = safe_part_name(str(value))
        duplicates = {n for n in wanted.values() if list(wanted.values()).count(n) > 1}
        if duplicates:
            raise SynfigError(f"Part names must be unique, repeated: {sorted(duplicates)}.")

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[SheetPart] = []
    for part in parts:
        if wanted and part.index not in wanted:
            continue
        part.name = wanted.get(part.index, f"part_{part.index:02d}")
        x, y, w, h = part.bbox
        x0, y0 = max(0, x - padding), max(0, y - padding)
        x1, y1 = min(image.width, x + w + padding), min(image.height, y + h + padding)
        crop = rgba[y0:y1, x0:x1].copy()
        own = np.isin(labels[y0:y1, x0:x1], part.labels)
        crop[..., 3] = np.where(own, crop[..., 3], 0)
        if reconstruct:
            hole_limit = max(256, int(crop.shape[0] * crop.shape[1] * 0.2))
            crop, part.reconstructed_pixels = fill_enclosed_holes(crop, own, hole_limit)
        _assign_metadata(part, crop)
        target = output_dir / f"{part.name}.png"
        Image.fromarray(crop, "RGBA").save(target, format="PNG", optimize=True)
        part.bbox = (x0, y0, x1 - x0, y1 - y0)
        part.file = str(target)
        written.append(part)

    compatibility = rig_compatibility(written)
    foreground = int(mask.sum())
    reconstructed = sum(p.reconstructed_pixels for p in written)
    hole_fraction = reconstructed / foreground if foreground else 0.0

    manifest = {
        "version": 2,
        "source": source,
        "sheet": str(sheet_path),
        "sheet_size": {"width": image.width, "height": image.height},
        "background": method,
        "reconstruction": {
            "applied": reconstruct,
            "pixels": reconstructed,
            "fraction": round(hole_fraction, 4),
        },
        "rig_compatibility": compatibility,
        "parts": [p.as_dict() for p in written],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    warnings: list[str] = []
    if compatibility["level"] == "low":
        warnings.append("Rig compatibility is low: " + "; ".join(compatibility.get("issues", [])))
    if not wanted:
        warnings.append(
            "Parts are unnamed; call again with names={...} to map numbers to body roles."
        )

    result: dict[str, Any] = {
        "success": True,
        "sheet": str(sheet_path),
        "sheet_size": manifest["sheet_size"],
        "background": method,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "detected_parts": len(parts),
        "parts": manifest["parts"],
        "named": bool(wanted),
        "reconstruction": manifest["reconstruction"],
        "rig_compatibility": compatibility,
        "warnings": warnings,
        "requires_approval": hole_fraction >= APPROVAL_HOLE_FRACTION,
    }
    if preview:
        result["preview_base64"] = _preview(image, parts)
    return result
