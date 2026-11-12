"""
Colour helpers shared by the production modules.

Synfig stores colours linearly; briefs and palettes are given in sRGB.  Every
generator therefore goes through :func:`parse_color` / :func:`linearise` so the
rendered result matches the requested hex.
"""

from __future__ import annotations

import math
from typing import Any

from synfig_mcp.errors import ValidationError as SpecError


def _hex_channels(text: str) -> tuple[float, float, float, float]:
    raw = text.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) not in (6, 8):
        raise SpecError(f"Colour '{text}' must look like #rrggbb or #rrggbbaa.")
    try:
        channels = [int(raw[i : i + 2], 16) / 255.0 for i in range(0, len(raw), 2)]
    except ValueError as err:
        raise SpecError(f"Colour '{text}' must look like #rrggbb or #rrggbbaa.") from err
    alpha = channels[3] if len(channels) == 4 else 1.0
    return channels[0], channels[1], channels[2], alpha


def linearise(channel: float) -> float:
    """sRGB channel (0..1) to Synfig's linear colour space."""
    return round(math.pow(max(0.0, min(1.0, channel)), 2.2), 6)


def parse_color(text: str) -> dict[str, Any]:
    """Parse ``#rgb`` / ``#rrggbb`` / ``#rrggbbaa`` into a typed Synfig colour."""
    red, green, blue, alpha = _hex_channels(text)
    return {
        "type": "color",
        "r": linearise(red),
        "g": linearise(green),
        "b": linearise(blue),
        "a": round(alpha, 6),
    }


def shift(color: dict[str, Any], amount: float) -> dict[str, Any]:
    """Lighten (amount > 0) or darken (amount < 0) a typed colour, in linear space."""
    return {
        "type": "color",
        "r": round(max(0.0, min(1.0, float(color["r"]) + amount)), 6),
        "g": round(max(0.0, min(1.0, float(color["g"]) + amount)), 6),
        "b": round(max(0.0, min(1.0, float(color["b"]) + amount)), 6),
        "a": round(float(color.get("a", 1.0)), 6),
    }


def vector(x: float, y: float) -> dict[str, Any]:
    return {"type": "vector", "x": round(x, 6), "y": round(y, 6)}


def gradient(stops: list[tuple[float, dict[str, Any]]]) -> dict[str, Any]:
    """A typed Synfig gradient from ``(position, colour)`` stops."""
    return {
        "type": "gradient",
        "cpoints": [{"pos": round(pos, 6), "color": colour} for pos, colour in stops],
    }
