"""Rig sheet slicing: parts are found, cropped with transparency and named."""

from __future__ import annotations

import json
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


def test_detail_next_to_a_part_is_merged_into_it(tmp_path: Path) -> None:
    sheet = _sheet(tmp_path / "sheet.png", (0, 0, 0, 0))
    mask, _ = foreground_mask(np.asarray(Image.open(sheet).convert("RGBA")))
    _labels, parts = detect_parts(mask)
    leg = parts[2]
    assert leg.bbox[2] > 41, "the detached detail was not merged into the leg"


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


def _body_sheet(path: Path) -> Path:
    """A small but riggable sheet: torso with an enclosed gap, plus a head."""
    img = Image.new("RGBA", (240, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((20, 20, 100, 100), fill=(240, 200, 160, 255))  # 1: head
    draw.rectangle((140, 20, 220, 140), fill=(40, 90, 200, 255))  # 2: torso
    draw.rectangle((170, 60, 200, 90), fill=(0, 0, 0, 0))  # enclosed 30x30 gap
    img.save(path)
    return path


def test_manifest_carries_rig_metadata(tmp_path: Path) -> None:
    sheet = _body_sheet(tmp_path / "body.png")
    result = slice_rig_sheet(sheet, tmp_path / "parts", names={"1": "head", "2": "torso"})

    by_name = {p["name"]: p for p in result["parts"]}
    assert by_name["head"]["role"] == "head"
    assert by_name["head"]["parent"] == "torso"
    assert by_name["head"]["pivot"] == {"fx": 0.5, "fy": 0.9}
    assert by_name["torso"]["parent"] is None
    assert by_name["head"]["confidence"] > 0.5
    assert result["rig_compatibility"]["level"] == "high"
    assert result["rig_compatibility"]["issues"] == []

    manifest = json.loads(Path(result["manifest"]).read_text())
    assert manifest["version"] == 2
    assert manifest["source"] == "file_path"
    assert manifest["rig_compatibility"]["level"] == "high"
    assert manifest["parts"][0]["role"] is not None


def test_enclosed_gap_is_reconstructed(tmp_path: Path) -> None:
    sheet = _body_sheet(tmp_path / "body.png")
    result = slice_rig_sheet(sheet, tmp_path / "parts", names={"1": "head", "2": "torso"})

    assert result["reconstruction"]["pixels"] > 0
    torso = next(p for p in result["parts"] if p["name"] == "torso")
    assert torso["reconstructed_pixels"] > 0
    # The gap is now opaque: no transparent pixel left inside the torso.
    img = Image.open(torso["file"]).convert("RGBA")
    assert img.getpixel((img.width // 2, img.height // 2))[3] == 255


def test_reconstruct_can_be_disabled(tmp_path: Path) -> None:
    sheet = _body_sheet(tmp_path / "body.png")
    result = slice_rig_sheet(
        sheet, tmp_path / "parts", names={"1": "head", "2": "torso"}, reconstruct=False
    )
    assert result["reconstruction"]["applied"] is False
    assert result["reconstruction"]["pixels"] == 0


def test_unnamed_sheet_warns_and_flags_unknown_rig(tmp_path: Path) -> None:
    sheet = _body_sheet(tmp_path / "body.png")
    result = slice_rig_sheet(sheet, tmp_path / "parts", preview=False)
    assert result["named"] is False
    assert any("unnamed" in w for w in result["warnings"])
    assert result["rig_compatibility"]["level"] == "unknown"
