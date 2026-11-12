"""A small synthetic rig sheet, a background and a scene spec that uses them."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

PART_NAMES = {
    "1": "head",
    "2": "torso",
    "3": "upper_arm_l",
    "4": "upper_arm_r",
    "5": "upper_leg_l",
    "6": "upper_leg_r",
    "7": "lower_leg_l",
    "8": "lower_leg_r",
}


def make_assets(folder: Path) -> dict[str, str]:
    """Draw a small rig sheet (8 parts and a caption-like mark) and a background."""
    sheet = Image.new("RGBA", (520, 330), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    draw.ellipse((20, 20, 110, 110), fill=(240, 200, 160, 255))
    draw.rounded_rectangle((150, 20, 250, 170), 12, fill=(40, 90, 200, 255))
    for x in (290, 350):
        draw.rounded_rectangle((x, 20, x + 30, 110), 10, fill=(60, 110, 220, 255))
    for x in (20, 90):
        draw.rounded_rectangle((x, 200, x + 40, 300), 10, fill=(50, 50, 70, 255))
    for x in (160, 230):
        draw.rounded_rectangle((x, 200, x + 34, 300), 10, fill=(70, 70, 90, 255))
    draw.rectangle((420, 250, 500, 290), fill=(0, 0, 0, 255))  # a caption box, not a part
    sheet.save(folder / "sheet.png")
    background = Image.new("RGB", (640, 360), (135, 206, 235))
    ImageDraw.Draw(background).rectangle((0, 280, 640, 360), fill=(90, 170, 90))
    background.save(folder / "bg.png")
    return {"sheet": str(folder / "sheet.png"), "background": str(folder / "bg.png")}


def scene_spec(assets: dict[str, str], manifest: str) -> dict[str, Any]:
    return {
        "width": 640,
        "height": 360,
        "fps": 24,
        "duration": 4,
        "background": {"file": assets["background"], "color": "#87ceeb"},
        "characters": [
            {
                "id": "hero",
                "manifest": manifest,
                "position": {"x": 100, "y": 300},
                "height": 180,
                "actions": [
                    {"motion": "walk", "start": 0, "end": 3, "move_to": {"x": 480, "y": 300}},
                    {"motion": "wave", "start": 3, "end": 4},
                ],
            }
        ],
        "props": [
            {
                "id": "sun",
                "file": str(Path(manifest).parent / "head.png"),
                "position": {"x": 560, "y": 60},
                "height": 70,
            }
        ],
        "camera": [{"time": 0, "zoom": 1.0}, {"time": 4, "zoom": 1.2}],
        "preview": False,
    }
