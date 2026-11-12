"""
High-level character brief to rig-ready parts (Step 2).

``CharacterBuilder.expand`` turns a :class:`CharacterDescriptor` into the
:class:`~synfig_mcp.characters.models.CharacterPartSpec` list that
``RiggingEngine.character_rig_from_parts`` already consumes.  Anatomy is drawn
from a small proportion table (7 heads for ``humanoid``, 3 for ``chibi``) and
coloured from the descriptor palette, so the result is original geometry.

Parts are ``primitive`` (Synfig vector layers), which is what keeps the
pipeline deterministic and free of third-party artwork.  The coordinates are in
canvas units for a character that is one unit tall, so the rig scales cleanly to
any ``height``.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.characters.cutout import CutoutPart
from synfig_mcp.characters.models import CharacterPartSpec
from synfig_mcp.production.models import CharacterDescriptor
from synfig_mcp.production.palette import parse_color, shift

#: Default palette when the descriptor and the style preset are both silent.
_DEFAULT_PALETTE = ["#f2c9a0", "#3a2b23", "#2b5dab", "#e8e3d8"]

#: Proportions per archetype.  ``head`` is the head height as a fraction of the
#: body; the rest are measured down from the top of the head in the same units.
_PROPORTIONS: dict[str, dict[str, float]] = {
    "humanoid": {
        "head": 1.0 / 7.0,
        "torso_w": 0.16,
        "torso_h": 0.30,
        "limb_w": 0.055,
        "arm_h": 0.30,
        "leg_h": 0.36,
        "shoulder": 0.075,
        "hip": 0.055,
    },
    "chibi": {
        "head": 1.0 / 3.0,
        "torso_w": 0.18,
        "torso_h": 0.20,
        "limb_w": 0.06,
        "arm_h": 0.22,
        "leg_h": 0.24,
        "shoulder": 0.08,
        "hip": 0.06,
    },
}


def _colour(value: str) -> dict[str, Any]:
    return parse_color(value)


class CharacterBuilder:
    """Expand a descriptor into primitive parts and their joint origins."""

    def __init__(self, style_palette: list[str] | None = None) -> None:
        self._style_palette = style_palette or []

    def _resolve_palette(self, descriptor: CharacterDescriptor) -> list[dict[str, Any]]:
        source = list(descriptor.palette) or list(self._style_palette) or _DEFAULT_PALETTE
        while len(source) < 4:
            source.append(_DEFAULT_PALETTE[len(source) % len(_DEFAULT_PALETTE)])
        return [_colour(colour) for colour in source[:4]]

    def expand(self, descriptor: CharacterDescriptor) -> list[CharacterPartSpec]:
        """Return the parts for one descriptor, bottom-up in z order."""
        prop = _PROPORTIONS[descriptor.archetype]
        skin, hair, primary, secondary = self._resolve_palette(descriptor)
        # The character occupies y in [0, 1] with the feet at y = 0.
        head_h = prop["head"]
        torso_h = prop["torso_h"]
        leg_h = prop["leg_h"]
        head_cy = 1.0 - head_h / 2.0
        torso_top = 1.0 - head_h
        torso_bottom = torso_top - torso_h
        limb_w = prop["limb_w"]

        def rect(
            part_id: str,
            part_type: str,
            x0: float,
            y0: float,
            x1: float,
            y1: float,
            colour: dict[str, Any],
            origin: dict[str, float],
            z: int,
        ) -> CharacterPartSpec:
            return CharacterPartSpec(
                id=part_id,
                part_type=part_type,
                geometry_type="primitive",
                primitive_type="rectangle",
                primitive_params={
                    "point1": {"type": "vector", "x": round(x0, 6), "y": round(y0, 6)},
                    "point2": {"type": "vector", "x": round(x1, 6), "y": round(y1, 6)},
                    "color": colour,
                },
                origin=origin,
                z_depth=z,
            )

        parts: list[CharacterPartSpec] = []

        # Legs (behind the torso).
        for side, sx in (("l", -1.0), ("r", 1.0)):
            x = sx * prop["hip"]
            parts.append(
                rect(
                    f"upper_leg_{side}",
                    "upper_leg",
                    x - limb_w / 2,
                    torso_bottom - leg_h / 2,
                    x + limb_w / 2,
                    torso_bottom,
                    secondary,
                    {"x": round(x, 6), "y": round(torso_bottom, 6)},
                    0,
                )
            )
            parts.append(
                rect(
                    f"lower_leg_{side}",
                    "lower_leg",
                    x - limb_w / 2,
                    0.0,
                    x + limb_w / 2,
                    torso_bottom - leg_h / 2,
                    shift(secondary, -0.04),
                    {"x": round(x, 6), "y": round(torso_bottom - leg_h / 2, 6)},
                    1,
                )
            )

        # Torso.
        parts.append(
            rect(
                "torso",
                "torso",
                -prop["torso_w"] / 2,
                torso_bottom,
                prop["torso_w"] / 2,
                torso_top,
                primary,
                {"x": 0.0, "y": round(torso_bottom, 6)},
                5,
            )
        )

        # Arms.
        for side, sx in (("l", -1.0), ("r", 1.0)):
            x = sx * prop["shoulder"]
            shoulder_y = torso_top - 0.02
            elbow_y = shoulder_y - prop["arm_h"] / 2
            parts.append(
                rect(
                    f"upper_arm_{side}",
                    "upper_arm",
                    x - limb_w / 2,
                    elbow_y,
                    x + limb_w / 2,
                    shoulder_y,
                    primary,
                    {"x": round(x, 6), "y": round(shoulder_y, 6)},
                    6,
                )
            )
            parts.append(
                rect(
                    f"forearm_{side}",
                    "forearm",
                    x - limb_w / 2,
                    elbow_y - prop["arm_h"] / 2,
                    x + limb_w / 2,
                    elbow_y,
                    skin,
                    {"x": round(x, 6), "y": round(elbow_y, 6)},
                    7,
                )
            )

        # Head, hair and face.
        head_r = head_h / 2
        parts.append(
            CharacterPartSpec(
                id="head",
                part_type="head",
                geometry_type="primitive",
                primitive_type="circle",
                primitive_params={
                    "origin": {"type": "vector", "x": 0.0, "y": round(head_cy, 6)},
                    "radius": round(head_r, 6),
                    "color": skin,
                },
                origin={"x": 0.0, "y": round(torso_top, 6)},
                z_depth=8,
            )
        )
        parts.append(
            CharacterPartSpec(
                id="hair",
                part_type="head",
                geometry_type="primitive",
                primitive_type="circle",
                primitive_params={
                    "origin": {"type": "vector", "x": 0.0, "y": round(head_cy + head_r * 0.35, 6)},
                    "radius": round(head_r * 0.92, 6),
                    "color": hair,
                },
                origin={"x": 0.0, "y": round(head_cy, 6)},
                z_depth=9,
            )
        )
        for side, sx in (("l", -1.0), ("r", 1.0)):
            parts.append(
                CharacterPartSpec(
                    id=f"eye_{side}",
                    part_type="eye",
                    geometry_type="primitive",
                    primitive_type="circle",
                    primitive_params={
                        "origin": {
                            "type": "vector",
                            "x": round(sx * head_r * 0.38, 6),
                            "y": round(head_cy + head_r * 0.1, 6),
                        },
                        "radius": round(head_r * 0.13, 6),
                        "color": {"type": "color", "r": 0.02, "g": 0.02, "b": 0.03, "a": 1.0},
                    },
                    origin={"x": 0.0, "y": round(head_cy, 6)},
                    z_depth=10,
                )
            )
        parts.append(
            rect(
                "mouth",
                "mouth",
                -head_r * 0.22,
                head_cy - head_r * 0.55,
                head_r * 0.22,
                head_cy - head_r * 0.45,
                shift(skin, -0.12),
                {"x": 0.0, "y": round(head_cy, 6)},
                11,
            )
        )
        return parts

    @staticmethod
    def part_roles(parts: list[CharacterPartSpec]) -> list[str]:
        """The anatomical roles present, for reporting."""
        return sorted({p.part_type for p in parts})

    @staticmethod
    def as_cutout_parts(parts: list[CharacterPartSpec]) -> list[CutoutPart]:
        """Convert rig specs into the ``CutoutPart`` shape the compiler consumes."""
        return [
            CutoutPart(
                name=spec.id,
                role=spec.part_type,
                primitive_type=spec.primitive_type,
                primitive_params=spec.primitive_params,
                origin=spec.origin,
                z=float(spec.z_depth),
            )
            for spec in parts
        ]
