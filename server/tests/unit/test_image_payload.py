"""Image payloads stay inside the budget a tool result may occupy."""

from __future__ import annotations

import base64
import io
import random

from PIL import Image

from synfig_mcp.image_payload import MAX_IMAGE_BYTES, encode_image


def _noisy(size: int = 2048) -> Image.Image:
    image = Image.new("RGB", (size, size), (250, 250, 250))
    pixels = image.load()
    rng = random.Random(11)
    for _ in range(200_000):
        pixels[rng.randrange(size), rng.randrange(size)] = (
            rng.randrange(256),
            rng.randrange(256),
            rng.randrange(256),
        )
    return image


def test_small_image_stays_png() -> None:
    image = Image.new("RGB", (64, 64), (10, 20, 30))
    payload = encode_image(image)
    assert payload.mime_type == "image/png"
    assert payload.size_bytes <= MAX_IMAGE_BYTES
    assert payload.width == 64
    assert payload.height == 64


def test_noisy_image_is_re_encoded_under_the_budget() -> None:
    payload = encode_image(_noisy())
    assert payload.size_bytes <= MAX_IMAGE_BYTES
    assert payload.mime_type == "image/jpeg"
    # The bytes are a real image, not a truncated file.
    with Image.open(io.BytesIO(payload.data)) as handle:
        assert handle.format == "JPEG"


def test_transparency_is_flattened_onto_the_background() -> None:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    image.putpixel((16, 16), (255, 0, 0, 255))
    payload = encode_image(image)
    with Image.open(io.BytesIO(payload.data)) as handle:
        flat = handle.convert("RGB")
    assert flat.getpixel((0, 0)) == (255, 255, 255)
    assert flat.getpixel((16, 16)) == (255, 0, 0)


def test_base64_and_data_url_are_consistent() -> None:
    payload = encode_image(Image.new("RGB", (16, 16), (1, 2, 3)))
    assert base64.b64decode(payload.base64) == payload.data
    assert payload.data_url.startswith(f"data:{payload.mime_type};base64,")
    assert payload.suffix == ".png"
