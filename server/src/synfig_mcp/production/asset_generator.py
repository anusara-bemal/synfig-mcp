"""
Procedural, IP-safe asset generators (Step 1).

Every generator emits native Synfig vector layers (``SceneLayerSpec`` dicts) so
the result is original geometry with no network access and no third-party
rights.  Randomness is seeded from the brief, so the same brief always produces
byte-identical layers.

The palette is taken from the active :class:`~synfig_mcp.recipes.models.StylePreset`
unless the request overrides it, which keeps generated art on-style.
"""

from __future__ import annotations

import random
from typing import Any

from synfig_mcp.production.palette import gradient, parse_color, shift, vector
from synfig_mcp.recipes.styles import get_style_preset

#: Canvas frame in Synfig units, given to generators as ``(left, top, right, bottom)``.
Frame = tuple[float, float, float, float]


def _bbox(frame: Frame) -> tuple[float, float, float, float]:
    left, top, right, bottom = frame
    return min(left, right), min(top, bottom), max(left, right), max(top, bottom)


class AssetGenerator:
    """Build procedural background, prop and texture layers.

    All methods are pure: they take a seed and a frame and return layer specs,
    which makes the pipeline reproducible and the generators trivial to test.
    """

    def __init__(self, palette: list[str] | None = None, style: str | None = None) -> None:
        preset = get_style_preset(style) if style else None
        source = palette or (preset.palette if preset else [])
        if not source:
            source = ["#1a1a24", "#2b3a55", "#6fa8dc", "#f2e8cf", "#ff5c5c"]
        self._palette = [parse_color(colour) for colour in source]

    # -- palette helpers ---------------------------------------------------

    def _pick(self, index: int) -> dict[str, Any]:
        return self._palette[index % len(self._palette)]

    def _sky_colors(self, rng: random.Random) -> tuple[dict[str, Any], dict[str, Any]]:
        """A bright top and a darker horizon, nudged by the seed."""
        top = shift(self._pick(2), 0.05 + rng.uniform(-0.04, 0.04))
        horizon = shift(self._pick(0), -0.02 + rng.uniform(-0.04, 0.04))
        return top, horizon

    # -- generators --------------------------------------------------------

    def background(
        self,
        generator: str,
        frame: Frame,
        seed: int = 0,
        colors: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the layers for one background generator."""
        left, top, right, bottom = _bbox(frame)
        span_x, span_y = right - left, top - bottom
        rng = random.Random(seed)
        overlay = [parse_color(c) for c in (colors or [])]
        sky = overlay[0] if overlay else None
        ground = overlay[1] if len(overlay) > 1 else None

        if generator == "flat":
            colour = sky or self._pick(0)
            return [
                {
                    "id": "bg_flat",
                    "type": "solid_color",
                    "params": {"color": colour},
                }
            ]

        if generator in ("sky", "gradient"):
            top_colour, horizon = self._sky_colors(rng)
            if sky:
                top_colour, horizon = sky, shift(sky, -0.06)
            return [
                {
                    "id": "bg_sky",
                    "type": "linear_gradient",
                    "params": {
                        "p1": vector(left, top),
                        "p2": vector(left, bottom),
                        "gradient": gradient([(0.0, top_colour), (1.0, horizon)]),
                    },
                }
            ]

        if generator == "landscape":
            top_colour, horizon = self._sky_colors(rng)
            if sky:
                top_colour, horizon = sky, shift(sky, -0.06)
            ground_colour = ground or shift(self._pick(1), -0.05)
            layers: list[dict[str, Any]] = [
                {
                    "id": "bg_sky",
                    "type": "linear_gradient",
                    "params": {
                        "p1": vector(left, top),
                        "p2": vector(left, bottom),
                        "gradient": gradient([(0.0, top_colour), (1.0, horizon)]),
                    },
                }
            ]
            # A sun and two rolling hills, deterministic from the seed.
            sun_x = left + span_x * rng.uniform(0.6, 0.85)
            sun_y = bottom + span_y * rng.uniform(0.55, 0.72)
            layers.append(
                {
                    "id": "bg_sun",
                    "type": "circle",
                    "params": {
                        "origin": vector(sun_x, sun_y),
                        "radius": round(span_y * rng.uniform(0.05, 0.08), 6),
                        "color": shift(self._pick(3), 0.05),
                    },
                }
            )
            horizon_y = bottom + span_y * 0.3
            layers.append(
                {
                    "id": "bg_ground",
                    "type": "rectangle",
                    "params": {
                        "point1": vector(left, bottom),
                        "point2": vector(right, horizon_y),
                        "color": ground_colour,
                    },
                }
            )
            for index, height in enumerate((0.12, 0.18)):
                peak_x = left + span_x * (0.3 + 0.35 * index)
                layers.append(
                    {
                        "id": f"bg_hill_{index}",
                        "type": "star",
                        "params": {
                            "origin": vector(peak_x, horizon_y),
                            "radius1": round(span_x * (0.16 + 0.04 * index), 6),
                            "radius2": round(span_y * height, 6),
                            "points": 3,
                            "regular_polygon": True,
                            "angle": {"type": "angle", "degrees": 90.0},
                            "color": shift(ground_colour, -0.03 + 0.03 * index),
                        },
                    }
                )
            return layers

        if generator == "starfield":
            layers = [
                {
                    "id": "bg_space",
                    "type": "solid_color",
                    "params": {"color": sky or shift(self._pick(0), -0.02)},
                }
            ]
            count = 60
            for index in range(count):
                star_x = rng.uniform(left, right)
                star_y = rng.uniform(bottom, top)
                layers.append(
                    {
                        "id": f"star_{index:03d}",
                        "type": "star",
                        "params": {
                            "origin": vector(star_x, star_y),
                            "radius1": round(rng.uniform(0.01, 0.03), 6),
                            "radius2": round(rng.uniform(0.005, 0.012), 6),
                            "points": 5,
                            "color": shift(self._pick(3), rng.uniform(-0.1, 0.1)),
                        },
                    }
                )
            return layers

        raise ValueError(
            f"Unknown background generator '{generator}'. "
            f"Available: {', '.join(self.background_generators())}."
        )

    def prop(
        self,
        generator: str,
        origin: tuple[float, float],
        size: float,
        seed: int = 0,
        colors: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the layers for one prop, anchored at ``origin`` (its base)."""
        x, y = origin
        rng = random.Random(seed)
        overlay = [parse_color(c) for c in (colors or [])]
        primary = overlay[0] if overlay else self._pick(1)
        accent = overlay[1] if len(overlay) > 1 else shift(primary, 0.08)

        if generator == "tree":
            trunk_w = size * 0.12
            canopy_x = x + rng.uniform(-0.05, 0.05) * size
            canopy_r = size * rng.uniform(0.32, 0.38)
            return [
                {
                    "id": "prop_trunk",
                    "type": "rectangle",
                    "params": {
                        "point1": vector(x - trunk_w / 2, y),
                        "point2": vector(x + trunk_w / 2, y + size * 0.45),
                        "color": shift(primary, -0.06),
                    },
                },
                {
                    "id": "prop_canopy",
                    "type": "circle",
                    "params": {
                        "origin": vector(canopy_x, y + size * 0.72),
                        "radius": round(canopy_r, 6),
                        "color": accent,
                    },
                },
            ]

        if generator == "cloud":
            layers: list[dict[str, Any]] = []
            for index, (dx, scale) in enumerate(((-0.3, 0.5), (0.0, 0.7), (0.32, 0.45))):
                layers.append(
                    {
                        "id": f"cloud_{index}",
                        "type": "circle",
                        "params": {
                            "origin": vector(x + dx * size, y + size * 0.4),
                            "radius": round(size * scale, 6),
                            "color": accent,
                        },
                    }
                )
            return layers

        if generator == "building":
            width = size * 0.5
            return [
                {
                    "id": "prop_building",
                    "type": "rectangle",
                    "params": {
                        "point1": vector(x - width / 2, y),
                        "point2": vector(x + width / 2, y + size),
                        "color": primary,
                    },
                },
                {
                    "id": "prop_roof",
                    "type": "star",
                    "params": {
                        "origin": vector(x, y + size),
                        "radius1": round(width * 0.75, 6),
                        "radius2": round(size * 0.18, 6),
                        "points": 3,
                        "regular_polygon": True,
                        "angle": {"type": "angle", "degrees": 90.0},
                        "color": shift(primary, -0.05),
                    },
                },
            ]

        if generator == "rock":
            return [
                {
                    "id": "prop_rock",
                    "type": "star",
                    "params": {
                        "origin": vector(x, y + size * 0.4),
                        "radius1": round(size * 0.5, 6),
                        "radius2": round(size * 0.34, 6),
                        "points": 6,
                        "color": primary,
                    },
                }
            ]

        raise ValueError(
            f"Unknown prop generator '{generator}'. Available: {', '.join(self.prop_generators())}."
        )

    def texture(
        self,
        generator: str,
        frame: Frame,
        seed: int = 0,
        amount: float = 0.25,
    ) -> list[dict[str, Any]]:
        """Return an overlay layer (grain / vignette / speed lines)."""
        left, top, right, bottom = _bbox(frame)
        rng = random.Random(seed)
        span_x, span_y = right - left, top - bottom

        if generator == "grain":
            return [
                {
                    "id": "fx_grain",
                    "type": "noise",
                    "params": {
                        "size": vector(0.06, 0.06),
                        "seed": seed,
                        "detail": 4,
                        "do_alpha": True,
                        "amount": {"type": "real", "value": round(amount, 6)},
                    },
                }
            ]

        if generator == "vignette":
            return [
                {
                    "id": "fx_vignette",
                    "type": "radial_gradient",
                    "params": {
                        "center": vector(0.0, 0.0),
                        "radius": round(max(span_x, span_y) * 0.7, 6),
                        "gradient": gradient(
                            [
                                (0.0, {"type": "color", "r": 0.0, "g": 0.0, "b": 0.0, "a": 0.0}),
                                (
                                    1.0,
                                    {
                                        "type": "color",
                                        "r": 0.0,
                                        "g": 0.0,
                                        "b": 0.0,
                                        "a": round(min(0.9, amount), 6),
                                    },
                                ),
                            ]
                        ),
                    },
                }
            ]

        if generator == "speed_lines":
            layers: list[dict[str, Any]] = []
            for index in range(12):
                line_y = bottom + span_y * rng.uniform(0.1, 0.9)
                width = span_x * rng.uniform(0.25, 0.7)
                layers.append(
                    {
                        "id": f"fx_line_{index:02d}",
                        "type": "rectangle",
                        "params": {
                            "point1": vector(left, line_y),
                            "point2": vector(left + width, line_y + span_y * 0.012),
                            "color": {
                                "type": "color",
                                "r": 1.0,
                                "g": 1.0,
                                "b": 1.0,
                                "a": round(amount * rng.uniform(0.3, 0.7), 6),
                            },
                        },
                    }
                )
            return layers

        raise ValueError(
            f"Unknown texture generator '{generator}'. "
            f"Available: {', '.join(self.texture_generators())}."
        )

    # -- discovery ---------------------------------------------------------

    @staticmethod
    def background_generators() -> list[str]:
        return ["flat", "sky", "gradient", "landscape", "starfield"]

    @staticmethod
    def prop_generators() -> list[str]:
        return ["tree", "cloud", "building", "rock"]

    @staticmethod
    def texture_generators() -> list[str]:
        return ["grain", "vignette", "speed_lines"]

    @classmethod
    def list_generators(cls) -> dict[str, list[str]]:
        """Every generator name, grouped by kind (used by the help text)."""
        return {
            "background": cls.background_generators(),
            "prop": cls.prop_generators(),
            "texture": cls.texture_generators(),
        }
