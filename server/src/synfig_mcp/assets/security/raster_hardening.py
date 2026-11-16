"""
Raster Image Hardening: Validates magic bytes, enforces pixel caps, and strips EXIF (Phase A5).
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

# 16 Megapixels max (e.g. 4096 x 4096)
MAX_IMAGE_PIXELS = 16 * 1024 * 1024

MAGIC_BYTES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
    "gif": b"GIF8",
    "webp": b"RIFF",
}


def detect_image_format(data: bytes) -> str | None:
    """Detect image format by magic bytes."""
    for fmt, magic in MAGIC_BYTES.items():
        if data.startswith(magic):
            return fmt
    return None


def sanitize_raster_bytes(raw_bytes: bytes) -> Image.Image:
    """
    Validate raw raster bytes and return a metadata-free copy of the image.

    1. Checks magic bytes.
    2. Enforces pixel dimensions <= MAX_IMAGE_PIXELS (and blocks PIL decompression bombs).
    3. Rebuilds the pixels so no EXIF/metadata or embedded payload survives.
    """
    fmt = detect_image_format(raw_bytes)
    if not fmt:
        raise ValueError("Invalid image file: magic bytes do not match supported raster formats.")

    # Prevent decompression bomb in PIL
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            w, h = img.size
            if w * h > MAX_IMAGE_PIXELS:
                raise ValueError(
                    f"Image dimension {w}x{h} ({w * h} pixels) exceeds safety limit of {MAX_IMAGE_PIXELS} pixels."
                )
            # Strip EXIF and re-encode
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            return clean_img
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Raster image decode failed: {exc}") from exc


def harden_raster_image(input_path: str | Path, output_path: str | Path) -> dict[str, int]:
    """
    Validate and harden raster image:
    1. Checks magic bytes.
    2. Enforces pixel dimensions <= MAX_IMAGE_PIXELS.
    3. Strips all EXIF/metadata and re-encodes clean image.
    Returns: {"width": int, "height": int, "filesize": int}
    """
    p_in = Path(input_path)
    p_out = Path(output_path)

    clean_img = sanitize_raster_bytes(p_in.read_bytes())
    p_out.parent.mkdir(parents=True, exist_ok=True)
    clean_img.save(p_out, format="PNG", optimize=True)
    return {
        "width": clean_img.width,
        "height": clean_img.height,
        "filesize": p_out.stat().st_size,
    }
