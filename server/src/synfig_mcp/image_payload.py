"""
Budgeted image payloads for tool results.

MCP clients cap the size of a single tool result (OpenCode rejects anything
above 1 MB) and a base64 blob inside the result text also burns model context
without telling the model anything it can see.  Images that a tool hands back
therefore go through :func:`encode_image`, which keeps the encoded bytes under
a fixed budget: it picks the cheapest format that fits and, if none does,
downscales the image.

The encoded bytes are meant to be delivered as an MCP ``ImageContent`` block
(a vision model reads a few hundred image tokens, not tens of thousands of
base64 tokens).  ``preview_path`` on disk is the fallback for clients that
cannot render image blocks.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from PIL import Image

#: Largest encoded image (raw bytes, before base64) a tool may hand back.
#: 120 KB encodes to ~160 KB of base64, which keeps a tool result far below
#: the 1 MB ceiling clients enforce.
MAX_IMAGE_BYTES = 120 * 1024

#: JPEG qualities tried, in order, before the image is downscaled.
JPEG_QUALITIES = (85, 75, 65, 55, 45, 35)

#: Smallest edge (pixels) a preview is scaled down to.
MIN_EDGE = 96

#: Background an image with transparency is flattened onto.
FLAT_BACKGROUND = (255, 255, 255, 255)


@dataclass(frozen=True)
class ImagePayload:
    """An encoded image plus everything a client needs to use it."""

    data: bytes
    mime_type: str
    width: int
    height: int

    @property
    def base64(self) -> str:
        """The image as an ASCII base64 string."""
        return base64.b64encode(self.data).decode("ascii")

    @property
    def data_url(self) -> str:
        """The image as a ``data:`` URL (ready for an HTML or markdown client)."""
        return f"data:{self.mime_type};base64,{self.base64}"

    @property
    def size_bytes(self) -> int:
        """Size of the encoded image in bytes."""
        return len(self.data)

    @property
    def suffix(self) -> str:
        """File extension that matches :attr:`mime_type`."""
        return ".jpg" if self.mime_type == "image/jpeg" else ".png"


def _flatten(image: Image.Image, background: tuple[int, int, int, int]) -> Image.Image:
    """Return ``image`` as RGB with any transparency flattened onto ``background``."""
    if image.mode == "RGB":
        return image
    rgba = image.convert("RGBA")
    canvas = Image.new("RGBA", rgba.size, background)
    canvas.alpha_composite(rgba)
    return canvas.convert("RGB")


def _encode_png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _payload(data: bytes, mime_type: str, image: Image.Image) -> ImagePayload:
    return ImagePayload(data=data, mime_type=mime_type, width=image.width, height=image.height)


def encode_image(
    image: Image.Image,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
    background: tuple[int, int, int, int] = FLAT_BACKGROUND,
) -> ImagePayload:
    """Encode ``image`` so that the result never exceeds ``max_bytes``.

    PNG is preferred (lossless, so line art stays crisp) but only when it fits
    the budget.  Otherwise JPEG is tried with a descending quality ladder and,
    as a last resort, the image is downscaled until the payload fits.
    """
    flat = _flatten(image, background)

    png = _encode_png(flat)
    if len(png) <= max_bytes:
        return _payload(png, "image/png", flat)

    for quality in JPEG_QUALITIES:
        jpeg = _encode_jpeg(flat, quality)
        if len(jpeg) <= max_bytes:
            return _payload(jpeg, "image/jpeg", flat)

    current = flat
    while min(current.size) > MIN_EDGE:
        width = max(MIN_EDGE, int(current.width * 0.8))
        height = max(MIN_EDGE, int(current.height * 0.8))
        current = current.resize((width, height), Image.Resampling.LANCZOS)
        for quality in (75, 60, 45):
            jpeg = _encode_jpeg(current, quality)
            if len(jpeg) <= max_bytes:
                return _payload(jpeg, "image/jpeg", current)

    # Smallest image we are willing to produce, at the lowest quality we use.
    return _payload(_encode_jpeg(current, 30), "image/jpeg", current)
