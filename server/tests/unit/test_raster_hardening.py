"""Raster hardening: magic-byte validation, pixel caps and metadata stripping."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from synfig_mcp.assets.security.raster_hardening import (
    MAX_IMAGE_PIXELS,
    detect_image_format,
    harden_raster_image,
    sanitize_raster_bytes,
)


def _png_bytes(size: tuple[int, int] = (24, 16), mode: str = "RGB") -> bytes:
    img = Image.new(mode, size, (10, 20, 30) if mode == "RGB" else (10, 20, 30, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_detect_image_format_recognizes_supported_types() -> None:
    assert detect_image_format(_png_bytes()) == "png"
    assert detect_image_format(b"\xff\xd8\xff\xe0junk") == "jpeg"
    assert detect_image_format(b"GIF89a....") == "gif"
    assert detect_image_format(b"RIFFxxxxWEBP") == "webp"
    assert detect_image_format(b"not an image") is None


def test_sanitize_returns_decoded_image() -> None:
    clean = sanitize_raster_bytes(_png_bytes((40, 20)))
    assert clean.size == (40, 20)


def test_sanitize_rejects_non_image_bytes() -> None:
    with pytest.raises(ValueError, match="magic bytes"):
        sanitize_raster_bytes(b"plain text, not an image")


def test_sanitize_rejects_oversized_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # A tiny file that claims huge dimensions must be refused, not decoded fully.
    # Either the explicit cap or PIL's own decompression-bomb guard may fire first.
    monkeypatch.setattr("synfig_mcp.assets.security.raster_hardening.MAX_IMAGE_PIXELS", 100)
    with pytest.raises(ValueError, match="exceeds"):
        sanitize_raster_bytes(_png_bytes((40, 40)))  # 1600 pixels > 100


def test_sanitize_drops_exif_metadata() -> None:
    img = Image.new("RGB", (16, 16), (1, 2, 3))
    buf = io.BytesIO()
    exif = Image.Exif()
    exif[0x010E] = "secret description"  # ImageDescription
    img.save(buf, format="JPEG", exif=exif)
    assert buf.getvalue().find(b"secret description") != -1, "fixture must embed EXIF"

    clean = sanitize_raster_bytes(buf.getvalue())
    out = io.BytesIO()
    clean.save(out, format="PNG")
    assert b"secret description" not in out.getvalue()


def test_harden_raster_image_writes_png(tmp_path: Path) -> None:
    src = tmp_path / "in.png"
    src.write_bytes(_png_bytes((32, 24)))
    out = tmp_path / "nested" / "out.png"
    info = harden_raster_image(src, out)
    assert info["width"] == 32 and info["height"] == 24
    assert out.is_file() and info["filesize"] == out.stat().st_size
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (32, 24)


def test_pixel_cap_constant_is_16_megapixels() -> None:
    assert MAX_IMAGE_PIXELS == 16 * 1024 * 1024
