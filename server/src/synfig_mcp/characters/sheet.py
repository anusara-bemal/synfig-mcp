"""Rig-sheet extraction: turn one character sheet image into animated parts.

A rig sheet ("model sheet") is a single raster with the character drawn several
times plus notes. To animate a cut-out puppet we need the front view separated
into overlapping body bands with real alpha.

The hard part is not cutting: it is that the *paper white* and the character's
*white clothing* are the same colour, and the clothing is open to the page at
sleeve hems and cuffs. Colour thresholding alone therefore cannot tell them
apart. This module resolves that by producing two masks from the same sheet:

``parts``   precise silhouette from a border flood fill. Correct edges, but
            white garments become transparent because the flood reached them.
``backing`` a sealed silhouette (the ink outline grown, flooded, then eroded
            back to the true edge) filled flat white. Placed behind the parts it
            re-opaques white clothing while the precise edges still cut the
            outside.

Interior pockets that must stay open (the slot between legs) are punched from
both masks via explicit seeds.

Everything here is pure Pillow/NumPy and does not touch Synfig, so it is
unit-testable and reusable from the CLI.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pydantic import BaseModel, Field

__all__ = [
    "BandSpec",
    "CutoutParts",
    "PartImage",
    "SheetSpec",
    "extract_sheet",
    "load_manifest",
    "prepare_background",
    "render_shadow",
]


class BandSpec(BaseModel):
    """One horizontal band of the figure, in normalised figure coordinates."""

    name: str = Field(description="Part name, e.g. 'head', 'torso', 'lower'.")
    top: float = Field(ge=0.0, le=1.0, description="Band top as a fraction of figure height.")
    bottom: float = Field(ge=0.0, le=1.0, description="Band bottom as a fraction of figure height.")

    def rows(self, height: int) -> tuple[int, int]:
        return round(self.top * height), round(self.bottom * height)


class SheetSpec(BaseModel):
    """How to cut one sheet into parts."""

    sheet_path: str = Field(description="Path to the character sheet image.")
    output_dir: str = Field(description="Directory to write parts and manifest into.")
    background_path: str | None = Field(
        default=None, description="Optional background image stored in the manifest."
    )
    crop: tuple[int, int, int, int] | None = Field(
        default=None,
        description="Optional (left, top, right, bottom) crop isolating the front view.",
    )
    bands: list[BandSpec] = Field(
        default_factory=lambda: [
            BandSpec(name="head", top=0.0, bottom=0.245),
            BandSpec(name="torso", top=0.215, bottom=0.668),
            BandSpec(name="lower", top=0.645, bottom=1.0),
        ],
        description="Body bands, listed top of stack first. Keep adjacent bands overlapping.",
    )
    pocket_seeds: list[tuple[int, int]] = Field(
        default_factory=list,
        description="(x, y) points in figure pixels of background pockets to keep transparent.",
    )
    pocket_bounds: tuple[int, int, int, int] | None = Field(
        default=None,
        description="(x0, y0, x1, y1) in figure pixels limiting how far a pocket flood may grow.",
    )
    paper_threshold: int = Field(
        default=205, description="Minimum channel value counted as paper white."
    )
    paper_spread: int = Field(default=26, description="Max RGB spread still counted as paper white.")
    ink_luma: int = Field(default=235, description="Luminance below which a pixel counts as ink.")
    seal_px: int = Field(default=4, description="Pixels the ink outline is grown to seal pen gaps.")
    isolate_px: int = Field(
        default=2,
        description=(
            "Radius used to sever guide lines that stitch note sketches to the figure. "
            "The figure is eroded by this much to find its true body, then dilated back "
            "and intersected with the raw cut. Raise it for sheets whose guide lines are "
            "thick, but very thin fingers start to disappear above 3."
        ),
    )
    min_part_px: int = Field(
        default=40, description="Restored blobs smaller than this are dropped as sheet noise."
    )
    ignore_regions: list[tuple[int, int, int, int]] = Field(
        default_factory=list,
        description=(
            "Boxes (left, top, right, bottom) in sheet coordinates to erase before cutting, "
            "e.g. stray hand studies, colour swatches or notes that touch the figure."
        ),
    )
    make_backing: bool = Field(default=True, description="Write a white backing plate part.")

    @property
    def out(self) -> Path:
        return Path(self.output_dir)


class PartImage(BaseModel):
    """A written part image plus where it sits in figure space."""

    name: str
    file: str
    x: int
    y: int
    w: int
    h: int


class CutoutParts(BaseModel):
    """Result of a sheet extraction."""

    figure_w: int
    figure_h: int
    parts: list[PartImage]
    pivots: dict[str, tuple[int, int]] = Field(
        default_factory=dict, description="Neck / hip / feet pivot in figure pixels."
    )
    background_path: str | None = None
    manifest_path: str


# ---------------------------------------------------------------------------
# masks
# ---------------------------------------------------------------------------
def _paper_mask(rgb: np.ndarray, threshold: int, spread: int) -> np.ndarray:
    return (rgb.min(axis=2) >= threshold) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= spread)


def _outside_mask(passable: np.ndarray) -> np.ndarray:
    """Flood the `passable` region inwards from the image border.

    Uses Pillow's flood fill (C) instead of a Python BFS so large sheets stay
    fast. Pillow floods *equal-valued* neighbours, so passable pixels are written
    as 0 and barriers as 255; a 0-valued frame around the image guarantees the
    seed pixel is always passable.
    """
    h, w = passable.shape
    canvas = np.full((h + 2, w + 2), 255, np.uint8)
    canvas[1:-1, 1:-1] = np.where(passable, 0, 255).astype(np.uint8)
    canvas[0, :] = canvas[-1, :] = canvas[:, 0] = canvas[:, -1] = 0
    # .copy() detaches the buffer: writing into an array-backed image is a no-op
    img = Image.fromarray(canvas, "L").copy()
    ImageDraw.floodfill(img, (0, 0), 128, thresh=0)
    return np.asarray(img)[1:-1, 1:-1] == 128


def _components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Label 4-connected components of `mask` by unioning runs per row.

    Row-run union-find keeps this O(runs) instead of a per-pixel Python BFS,
    which matters on multi-megapixel sheets.
    """
    h, w = mask.shape
    parent: list[int] = []

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    labels = np.zeros((h, w), np.int32)
    prev: list[tuple[int, int, int]] = []  # (start, end, label)
    for y in range(h):
        row = mask[y]
        if not row.any():
            prev = []
            continue
        edges = np.diff(np.concatenate(([0], row.view(np.int8), [0])).astype(np.int8))
        starts = np.flatnonzero(edges == 1)
        ends = np.flatnonzero(edges == -1) - 1
        cur: list[tuple[int, int, int]] = []
        for s, e in zip(starts, ends, strict=True):
            label = len(parent)
            parent.append(label)
            labels[y, s:e + 1] = label
            for ps, pe, pl in prev:
                if ps <= e and s <= pe:
                    union(label, pl)
            cur.append((int(s), int(e), label))
        prev = cur

    # flatten
    remap: dict[int, int] = {}
    flat = np.zeros((h, w), np.int32)
    for y in range(h):
        row = mask[y]
        if not row.any():
            continue
        idx = np.flatnonzero(row)
        for x in idx:
            root = find(int(labels[y, x]))
            if root not in remap:
                remap[root] = len(remap) + 1
            flat[y, x] = remap[root]
    return flat, len(remap)


def _largest_component(mask: np.ndarray) -> np.ndarray:
    labels, count = _components(mask)
    if count == 0:
        return mask
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(sizes.argmax())


def _pocket_mask(paper: np.ndarray, seeds: list[tuple[int, int]], bounds: tuple[int, int, int, int] | None):
    """Punch paper pockets that the border flood cannot reach."""
    mask = np.zeros_like(paper)
    h, w = paper.shape
    for sx, sy in seeds:
        if not (0 <= sy < h and 0 <= sx < w):
            continue
        if not paper[sy, sx]:
            # seed landed on ink: nudge to the nearest paper pixel in a small window
            found = None
            for radius in range(1, 6):
                ys = slice(max(0, sy - radius), min(h, sy + radius + 1))
                xs = slice(max(0, sx - radius), min(w, sx + radius + 1))
                window = paper[ys, xs]
                if window.any():
                    dy, dx = np.argwhere(window)[0]
                    found = (xs.start + dx, ys.start + dy)
                    break
            if found is None:
                raise ValueError(f"pocket seed {(sx, sy)} is not on a paper pocket")
            sx, sy = found
        stack, seen = [(sy, sx)], {(sy, sx)}
        while stack:
            cy, cx = stack.pop()
            mask[cy, cx] = True
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if bounds and not (bounds[1] <= ny < bounds[3] and bounds[0] <= nx < bounds[2]):
                    continue
                if not (0 <= ny < h and 0 <= nx < w):
                    continue
                if paper[ny, nx] and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    stack.append((ny, nx))
    mask[~paper] = False
    return mask


def _pocket_bounds(seeds: list[tuple[int, int]], shape: tuple[int, int]) -> tuple[int, int, int, int] | None:
    """Allow the pocket flood to grow at most a quarter of the figure around a seed."""
    if not seeds:
        return None
    h, w = shape
    span = max(24, round(min(h, w) * 0.25))
    xs = [s[0] for s in seeds]
    ys = [s[1] for s in seeds]
    return (max(0, min(xs) - span), max(0, min(ys) - span),
            min(w, max(xs) + span), min(h, max(ys) + span))


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------
def extract_sheet(spec: SheetSpec) -> CutoutParts:
    """Cut one rig sheet into overlapping alpha parts plus a white backing plate."""
    sheet_path = Path(spec.sheet_path).expanduser()
    if not sheet_path.is_file():
        raise FileNotFoundError(f"sheet not found: {sheet_path}")
    out = spec.out
    parts_dir = out / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(sheet_path).convert("RGB")
    if spec.ignore_regions:
        draw = ImageDraw.Draw(image)
        for box in spec.ignore_regions:
            draw.rectangle(box, fill=(255, 255, 255))
    if spec.crop:
        left, top, right, bottom = spec.crop
        image = image.crop((left, top, right, bottom))

    # 1px paper margin so every border pixel can seed the flood
    rgb_pad = np.pad(np.asarray(image).astype(np.int16), ((1, 1), (1, 1), (0, 0)),
                     mode="constant", constant_values=255)
    h, w = rgb_pad.shape[:2]
    paper = _paper_mask(rgb_pad, spec.paper_threshold, spec.paper_spread)
    luma = rgb_pad.reshape(-1, 3).mean(axis=1).reshape(h, w)

    # --- precise cut -------------------------------------------------------
    # The raw cut is the whole ink drawing, including the stray note sketches
    # and any other view that shares the crop. Guide lines join those to the
    # figure, so we erode hard enough to sever them, keep the biggest body,
    # then dilate back and intersect with the raw cut to restore real edges.
    raw = ~_outside_mask(paper)
    radius = max(1, spec.isolate_px)
    eroded = np.asarray(
        Image.fromarray((raw * 255).astype(np.uint8), "L").filter(
            ImageFilter.MinFilter(radius * 2 + 1))
    ) > 127
    body = _largest_component(eroded)
    grown = np.asarray(
        Image.fromarray((body * 255).astype(np.uint8), "L").filter(
            ImageFilter.MaxFilter(radius * 2 + 1))
    ) > 127
    restored = grown & raw
    labels, count = _components(restored)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    keep = {i for i in range(1, count + 1) if sizes[i] >= max(1, spec.min_part_px)}
    precise = np.isin(labels, list(keep))
    precise = np.asarray(
        Image.fromarray((precise * 255).astype(np.uint8), "L").filter(
            ImageFilter.MedianFilter(3))
    ) > 127
    if not precise.any():
        raise ValueError("no character found: the sheet is blank or entirely paper")

    # --- sealed body -------------------------------------------------------
    ink = luma < spec.ink_luma
    grow = spec.seal_px * 2 + 1
    barrier = np.asarray(
        Image.fromarray((ink * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(grow))
    ) > 127
    solid = ~_outside_mask(~barrier)
    solid = _largest_component(solid)
    solid = np.asarray(
        Image.fromarray((solid * 255).astype(np.uint8), "L").filter(ImageFilter.MinFilter(grow))
    ) > 127
    # keep the backing on the figure only, never on note sketches
    body_area = np.asarray(
        Image.fromarray((body * 255).astype(np.uint8), "L").filter(
            ImageFilter.MaxFilter((radius + 2) * 2 + 1))
    ) > 127
    solid &= body_area

    # --- common trim box ---------------------------------------------------
    bbox = Image.fromarray((precise * 255).astype(np.uint8), "L").getbbox()
    if not bbox:
        raise ValueError("no character found: the sheet is blank or entirely paper")
    left, top, right, bottom = bbox
    x0, y0 = max(1, left - 2), max(1, top - 2)
    x1, y1 = min(w - 1, right + 2), min(h - 1, bottom + 2)
    crop_box = (x0 - 1, y0 - 1, x1 - 1, y1 - 1)
    figure = image.crop(crop_box)

    # --- pockets (in figure coordinates) -----------------------------------
    paper_fig = paper[y0:y1, x0:x1]
    pockets = _pocket_mask(
        paper_fig,
        spec.pocket_seeds,
        spec.pocket_bounds or _pocket_bounds(spec.pocket_seeds, paper_fig.shape),
    )
    precise_fig = precise[y0:y1, x0:x1].copy()
    solid_fig = solid[y0:y1, x0:x1].copy()
    precise_fig[pockets] = False
    solid_fig[pockets] = False

    rgba = figure.convert("RGBA")
    rgba.putalpha(Image.fromarray((precise_fig * 255).astype(np.uint8), "L")
                  .filter(ImageFilter.GaussianBlur(0.7)))

    if spec.make_backing:
        backing = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
        backing.putalpha(Image.fromarray((solid_fig * 255).astype(np.uint8), "L")
                         .filter(ImageFilter.GaussianBlur(0.6)))
        backing.save(parts_dir / "backing.png")

    # --- bands -------------------------------------------------------------
    written: list[PartImage] = []
    for band in spec.bands:
        y0, y1 = band.rows(rgba.height)
        y0, y1 = max(0, y0), min(rgba.height, y1)
        strip = rgba.crop((0, y0, rgba.width, y1))
        alpha = strip.getchannel("A")
        sb = alpha.getbbox()
        if not sb:
            raise ValueError(f"band '{band.name}' contains no pixels; check it against the figure")
        strip = strip.crop(sb)
        path = parts_dir / f"{band.name}.png"
        strip.save(path)
        written.append(PartImage(name=band.name, file=str(path), x=sb[0], y=y0 + sb[1],
                                 w=strip.width, h=strip.height))

    if spec.make_backing:
        written.append(PartImage(name="backing", file=str(parts_dir / "backing.png"),
                                 x=0, y=0, w=rgba.width, h=rgba.height))

    # --- pivots: neck at the head band's base, hips at the torso band's base -
    by_name = {band.name: band for band in spec.bands}
    height = rgba.height
    width = rgba.width

    def base_of(name: str, fallback: float) -> int:
        band = by_name.get(name)
        frac = band.bottom if band else fallback
        return round(frac * height)

    pivots = {
        "neck": (width // 2, base_of("head", 0.245)),
        "hip": (width // 2, base_of("torso", 0.668)),
        "feet": (width // 2, height),
    }

    manifest_path = out / "manifest.json"
    result = CutoutParts(
        figure_w=width,
        figure_h=height,
        parts=written,
        pivots={k: (int(v[0]), int(v[1])) for k, v in pivots.items()},
        background_path=spec.background_path,
        manifest_path=str(manifest_path),
    )
    manifest_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    rgba.save(out / "figure.png")
    (out / "parts" / "figure.png").write_bytes((out / "figure.png").read_bytes())
    return result


def prepare_background(source: str, dest: Path, size: tuple[int, int]) -> Path:
    """Cover-fit a background image to the canvas and sharpen the upscale."""
    img = Image.open(Path(source).expanduser()).convert("RGB")
    w, h = size
    scale = max(w / img.width, h / img.height)
    if abs(scale - 1.0) > 1e-3:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                         Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    img = img.crop((left, top, left + w, top + h))
    if scale > 1.35:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=3))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, quality=92)
    return dest


def render_shadow(dest: Path, width: int = 360, height: int = 104, strength: float = 0.8) -> Path:
    """Soft elliptical contact shadow with a transparent surround."""
    yy, xx = np.mgrid[0:height, 0:width]
    radius = np.sqrt(((xx - width / 2) / (width / 2)) ** 2
                     + ((yy - height / 2) / (height / 2)) ** 2)
    alpha = (np.clip(1.0 - radius, 0.0, 1.0) ** 1.45) * strength
    arr = np.zeros((height, width, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = 14, 20, 30
    arr[..., 3] = (alpha * 255).astype(np.uint8)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(dest)
    return dest


def load_manifest(path: str) -> CutoutParts:
    return CutoutParts.model_validate_json(Path(path).expanduser().read_text(encoding="utf-8"))
