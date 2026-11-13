"""Rig sheet slicing: parts are found, cropped with transparency and named."""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from synfig_mcp.characters.sheet import (
    detect_parts,
    foreground_mask,
    label_components,
    slice_rig_sheet,
)
from synfig_mcp.errors import SynfigError
from synfig_mcp.image_payload import MAX_IMAGE_BYTES


def _sheet(path: Path, background: tuple[int, int, int, int]) -> Path:
    """Three parts in two rows, one detached highlight and one speck of noise."""
    img = Image.new("RGBA", (400, 300), background)
    draw = ImageDraw.Draw(img)
    draw.ellipse((20, 20, 120, 120), fill=(240, 200, 160, 255))  # 1: head
    draw.ellipse((50, 50, 70, 70), fill=(255, 255, 255, 255))  # white eye inside the head
    draw.rectangle((200, 20, 300, 140), fill=(40, 90, 200, 255))  # 2: torso
    draw.rectangle((20, 180, 60, 280), fill=(50, 50, 70, 255))  # 3: leg
    draw.rectangle((63, 180, 66, 184), fill=(50, 50, 70, 255))  # detail next to the leg
    draw.point((380, 290), fill=(255, 0, 0, 255))  # noise
    img.save(path)
    return path


def test_label_components_counts_separate_blobs() -> None:
    mask = np.zeros((6, 8), dtype=bool)
    mask[0:2, 0:2] = True
    mask[4:6, 5:8] = True
    mask[2, 2] = True  # touches the first blob diagonally
    labels, count = label_components(mask)
    assert count == 2
    assert labels[0, 0] == labels[2, 2] != labels[5, 6]


def test_u_shaped_blob_is_one_component() -> None:
    mask = np.zeros((5, 5), dtype=bool)
    mask[0:4, 0] = True
    mask[0:4, 4] = True
    mask[4, :] = True
    _labels, count = label_components(mask)
    assert count == 1


@pytest.mark.parametrize("background", [(0, 0, 0, 0), (255, 255, 255, 255)])
def test_slice_finds_parts_in_reading_order(
    tmp_path: Path, background: tuple[int, int, int, int]
) -> None:
    sheet = _sheet(tmp_path / "sheet.png", background)
    result = slice_rig_sheet(sheet, tmp_path / "parts")

    assert result["detected_parts"] == 3, "noise or details were counted as parts"
    assert result["background"] == ("alpha" if background[3] == 0 else "border_colour")
    boxes = [p["bbox"] for p in result["parts"]]
    assert boxes[0]["x"] < boxes[1]["x"] and boxes[2]["y"] > boxes[0]["y"]
    assert result["preview_base64"]

    head = Image.open(result["parts"][0]["file"]).convert("RGBA")
    assert head.getpixel((0, 0))[3] == 0, "the background of a part must be transparent"
    centre = head.getpixel((head.width // 2, head.height // 2))
    assert centre[3] == 255
    # The white eye is inside the head: it must survive on a white sheet too.
    assert head.getpixel((42, 42)) == (255, 255, 255, 255)


def test_names_select_and_name_the_parts(tmp_path: Path) -> None:
    sheet = _sheet(tmp_path / "sheet.png", (0, 0, 0, 0))
    result = slice_rig_sheet(
        sheet, tmp_path / "parts", names={"1": "Head", "3": "upper leg L"}, preview=False
    )
    assert [p["name"] for p in result["parts"]] == ["head", "upper_leg_l"]
    assert (tmp_path / "parts" / "upper_leg_l.png").is_file()
    assert "preview_base64" not in result
    manifest = json.loads(Path(result["manifest"]).read_text())
    assert [p["name"] for p in manifest["parts"]] == ["head", "upper_leg_l"]


def test_preview_stays_inside_the_result_budget(tmp_path: Path) -> None:
    """A detailed 2K sheet must not produce a tool result clients reject."""
    sheet = tmp_path / "sheet.png"
    image = Image.new("RGB", (2048, 2048), (250, 250, 250))
    draw = ImageDraw.Draw(image)
    for index in range(8):
        draw.ellipse(
            (
                60 + (index % 4) * 480,
                60 + (index // 4) * 900,
                420 + (index % 4) * 480,
                840 + (index // 4) * 900,
            ),
            fill=(180 + index * 7, 90, 160),
        )
    pixels = image.load()
    rng = random.Random(7)
    for _ in range(300_000):
        pixels[rng.randrange(2048), rng.randrange(2048)] = (
            rng.randrange(256),
            rng.randrange(256),
            rng.randrange(256),
        )
    image.save(sheet)

    result = slice_rig_sheet(sheet, tmp_path / "parts")

    assert result["preview_bytes"] <= MAX_IMAGE_BYTES
    assert result["preview_mime"] in {"image/png", "image/jpeg"}
    assert len(result["preview_base64"]) <= MAX_IMAGE_BYTES * 4 // 3 + 4
    preview_file = Path(result["preview_path"])
    assert preview_file.is_file()
    assert preview_file.stat().st_size == result["preview_bytes"]


def test_detail_next_to_a_part_is_merged_into_it(tmp_path: Path) -> None:
    sheet = _sheet(tmp_path / "sheet.png", (0, 0, 0, 0))
    mask, _ = foreground_mask(np.asarray(Image.open(sheet).convert("RGBA")))
    _labels, parts = detect_parts(mask)
    leg = parts[2]
    assert leg.bbox[2] > 41, "the detached detail was not merged into the leg"


def test_checkerboard_background_is_not_sliced_into_parts(tmp_path: Path) -> None:
    """Art exported over a checkerboard has two background tones."""
    image = Image.new("RGB", (400, 400), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for row in range(8):
        for col in range(8):
            if (row + col) % 2:
                draw.rectangle(
                    (col * 50, row * 50, col * 50 + 50, row * 50 + 50), fill=(190, 190, 190)
                )
    draw.ellipse((120, 120, 280, 280), fill=(40, 90, 200))
    sheet = tmp_path / "checker.png"
    image.save(sheet)

    mask, method = foreground_mask(np.asarray(image.convert("RGBA")))
    _labels, parts = detect_parts(mask)

    assert method == "two_tone_border"
    assert len(parts) == 1, "the checkerboard squares were counted as parts"
    assert parts[0].area > 10000


def test_a_banded_photo_is_not_mistaken_for_a_checkerboard() -> None:
    """A dark and a light band along the border is not a two-tone background."""
    image = Image.new("RGB", (400, 400), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 400, 40), fill=(20, 20, 20))
    draw.rectangle((0, 360, 400, 400), fill=(240, 240, 240))
    draw.ellipse((120, 120, 280, 280), fill=(40, 90, 200))

    mask, method = foreground_mask(np.asarray(image.convert("RGBA")))
    _labels, parts = detect_parts(mask)

    assert method == "border_colour"
    # The dark band stays a part: only a checkerboard is a two-tone background.
    assert len(parts) == 2
    assert any(part.bbox[0] == 0 and part.bbox[3] <= 41 for part in parts)


def test_bad_names_and_empty_sheets_are_rejected(tmp_path: Path) -> None:
    sheet = _sheet(tmp_path / "sheet.png", (0, 0, 0, 0))
    with pytest.raises(SynfigError, match="parts 1..3"):
        slice_rig_sheet(sheet, tmp_path / "parts", names={"9": "head"})
    with pytest.raises(SynfigError, match="unique"):
        slice_rig_sheet(sheet, tmp_path / "parts", names={"1": "head", "2": "head"})

    empty = tmp_path / "empty.png"
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(empty)
    with pytest.raises(SynfigError, match="No parts"):
        slice_rig_sheet(empty, tmp_path / "none")
