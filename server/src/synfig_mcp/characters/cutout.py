"""
Cut-out character rigs built from part images.

A rig is compiled into plain Synfig layers that both backends understand:

    Character_<id>                 group
      <id>_pos                     translate   - where the character stands
      <id>_flip                    stretch     - only when the character is mirrored
      <id>_<root part>             group
        <id>_<part>_rot            rotate      - the joint, centred on the pivot
        <child parts in front>     groups
        <id>_<part>_img            import      - the artwork
        <child parts behind>       groups

A rotate layer turns everything below it in its group, so turning the upper arm
carries the forearm and the hand with it (forward kinematics).  The whole rig is
emitted as one ``scene_build`` spec: one round trip and one undo step.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from PIL import Image
from pydantic import BaseModel, Field

from synfig_mcp.errors import ValidationError as SpecError
from synfig_mcp.security.sandbox import validate_path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


# ---------------------------------------------------------------------------
# Canvas frame: pixel <-> Synfig unit conversion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanvasFrame:
    """The visible area of a canvas, in pixels and in Synfig units."""

    width: int
    height: int
    left: float
    top: float
    right: float
    bottom: float
    coords: str = "pixels"

    @classmethod
    def for_document(
        cls,
        width: int,
        height: int,
        view_box: tuple[float, float, float, float] | None,
        coords: str = "pixels",
    ) -> CanvasFrame:
        """Build the frame of a document; without a view box Synfig's 60 px/unit is assumed."""
        if view_box is None:
            half_w, half_h = width / 120.0, height / 120.0
            view_box = (-half_w, half_h, half_w, -half_h)
        return cls(width, height, *view_box, coords=coords)

    @property
    def units_per_pixel(self) -> float:
        return abs(self.top - self.bottom) / max(1, self.height)

    def point(self, x: float, y: float) -> tuple[float, float]:
        """Convert a scene position to Synfig units."""
        if self.coords == "units":
            return (x, y)
        ux = self.left + (self.right - self.left) * (x / max(1, self.width))
        uy = self.top + (self.bottom - self.top) * (y / max(1, self.height))
        return (ux, uy)

    def length(self, value: float) -> float:
        """Convert a scene length to Synfig units."""
        return value if self.coords == "units" else value * self.units_per_pixel


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

_SIDE_TOKENS = {"l": "l", "left": "l", "lt": "l", "r": "r", "right": "r", "rt": "r"}
_UPPER = {"upper", "top", "up"}
_LOWER = {"lower", "bottom", "fore", "low"}


def infer_role(name: str) -> str | None:
    """Guess the anatomical role of a part from its name.

    ``arm_upper_l``, ``LeftUpperArm`` and ``l_bicep`` all become ``upper_arm_l``.
    Returns ``None`` when the name does not look like a body part.
    """
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    tokens = [t for t in re.split(r"[^A-Za-z]+", spaced.lower()) if t]
    if not tokens:
        return None
    side = next((_SIDE_TOKENS[t] for t in tokens if t in _SIDE_TOKENS), None)
    words = {t for t in tokens if t not in _SIDE_TOKENS}
    joined = "".join(tokens)

    def has(*candidates: str) -> bool:
        return any(c in words or c in joined for c in candidates)

    base: str | None = None
    if has("forearm", "lowerarm") or ("arm" in words and words & _LOWER):
        base = "forearm"
    elif has("upperarm", "bicep", "shoulder") or ("arm" in words and words & _UPPER):
        base = "upper_arm"
    elif has("hand", "fist", "palm"):
        base = "hand"
    elif has("thigh", "upperleg") or ("leg" in words and words & _UPPER):
        base = "upper_leg"
    elif has("shin", "calf", "lowerleg") or ("leg" in words and words & _LOWER):
        base = "lower_leg"
    elif has("foot", "feet", "shoe", "boot"):
        base = "foot"
    elif "arm" in words:
        base = "arm"
    elif "leg" in words:
        base = "leg"
    elif has("head", "face"):
        return "head"
    elif has("neck"):
        return "neck"
    elif has("torso", "body", "chest", "trunk"):
        return "torso"
    elif has("hip", "pelvis"):
        return "hips"
    if base is None:
        return None
    return f"{base}_{side}" if side else base


@dataclass(frozen=True)
class RoleDefault:
    """Where a part of a given role hangs when the caller does not say."""

    parents: tuple[str, ...]
    pivot: tuple[float, float]
    attach_torso: tuple[float, float]  # on the torso, for the right side (x mirrored for left)
    attach_limb: tuple[float, float] = (0.5, 0.92)
    z_right: float = 0.0
    z_left: float = 0.0


#: Humanoid defaults.  Fractions are of the part image: (0, 0) top-left, (1, 1) bottom-right.
HUMANOID: dict[str, RoleDefault] = {
    "hips": RoleDefault(("torso",), (0.5, 0.15), (0.5, 0.95), z_right=-0.5, z_left=-0.5),
    "neck": RoleDefault(("torso",), (0.5, 0.85), (0.5, 0.04), z_right=-0.5, z_left=-0.5),
    "head": RoleDefault(("neck", "torso"), (0.5, 0.9), (0.5, 0.05), (0.5, 0.2), 1.0, 1.0),
    "upper_arm": RoleDefault(("torso",), (0.5, 0.1), (0.84, 0.14), z_right=2.0, z_left=-2.0),
    "arm": RoleDefault(("torso",), (0.5, 0.08), (0.84, 0.14), z_right=2.0, z_left=-2.0),
    "forearm": RoleDefault(
        ("upper_arm", "arm", "torso"), (0.5, 0.08), (0.84, 0.5), z_right=-0.1, z_left=-0.1
    ),
    "hand": RoleDefault(
        ("forearm", "arm", "upper_arm", "torso"),
        (0.5, 0.12),
        (0.84, 0.8),
        z_right=-0.1,
        z_left=-0.1,
    ),
    "upper_leg": RoleDefault(("hips", "torso"), (0.5, 0.08), (0.68, 0.93), (0.68, 0.7), -1.0, -1.5),
    "leg": RoleDefault(("hips", "torso"), (0.5, 0.06), (0.68, 0.93), (0.68, 0.7), -1.0, -1.5),
    "lower_leg": RoleDefault(
        ("upper_leg", "leg", "torso"), (0.5, 0.06), (0.68, 0.95), z_right=-0.1, z_left=-0.1
    ),
    "foot": RoleDefault(
        ("lower_leg", "leg", "upper_leg", "torso"),
        (0.35, 0.2),
        (0.68, 0.98),
        (0.5, 0.95),
        -0.1,
        -0.1,
    ),
}


def split_role(role: str | None) -> tuple[str | None, str | None]:
    """Split ``upper_arm_l`` into ``("upper_arm", "l")``."""
    if not role:
        return None, None
    if role.endswith("_l") or role.endswith("_r"):
        return role[:-2], role[-1]
    return role, None


# ---------------------------------------------------------------------------
# Spec models
# ---------------------------------------------------------------------------


class MotionAction(BaseModel):
    """One thing a character does on the timeline."""

    motion: str = Field(
        description="Motion name, see the motion list (walk, run, idle, wave, ...)."
    )
    start: float = Field(default=0.0, description="Start time in seconds.")
    end: float | None = Field(default=None, description="End time in seconds.")
    speed: float = Field(default=1.0, gt=0.0, description="Cycle speed multiplier.")
    move_to: dict[str, float] | None = Field(
        default=None, description="Position {x, y} the character reaches at 'end'."
    )
    angles: dict[str, float] = Field(
        default_factory=dict,
        description="For motion 'pose': part name or role -> joint angle in degrees.",
    )
    settle: bool = Field(
        default=True,
        description="Looping motions: ease the joints back to the rest pose after 'end'.",
    )


class CutoutPart(BaseModel):
    """One piece of artwork and the joint it turns around."""

    name: str = Field(description="Part name, unique in the character (e.g. 'upper_arm_l').")
    file: str | None = Field(default=None, description="Image file of the part.")
    role: str | None = Field(default=None, description="Anatomical role; guessed from the name.")
    parent: str | None = Field(default=None, description="Name of the parent part.")
    pivot: dict[str, float] | None = Field(
        default=None,
        description="Joint in the part image: {fx, fy} as fractions or {x, y} in pixels.",
    )
    attach: dict[str, float] | None = Field(
        default=None,
        description="Where the joint sits on the parent image: {fx, fy} or {x, y}.",
    )
    bbox: dict[str, float] | None = Field(
        default=None, description="Position on the source sheet {x, y, width, height}."
    )
    z: float | None = Field(default=None, description="Stacking inside the parent; >0 is in front.")
    rest_angle: float = Field(default=0.0, description="Joint angle of the rest pose in degrees.")
    # Procedural parts (no artwork): a Synfig primitive in canvas units.
    primitive_type: str | None = Field(default=None, description="Synfig layer type to draw.")
    primitive_params: dict[str, Any] = Field(default_factory=dict)
    origin: dict[str, float] | None = Field(
        default=None, description="Joint of a primitive part in canvas units."
    )


class CutoutCharacter(BaseModel):
    """A cut-out character: parts, placement and what it does."""

    id: str = Field(description="Character id; prefix of every layer of the rig.")
    parts: list[CutoutPart] = Field(default_factory=list)
    manifest: str | None = Field(
        default=None, description="manifest.json written by rig_sheet_slice (instead of parts)."
    )
    root: str | None = Field(default=None, description="Name of the root part (default: torso).")
    layout: Literal["assemble", "in_place"] = Field(
        default="assemble",
        description="'assemble' joins parts at their joints; 'in_place' keeps the sheet layout.",
    )
    position: dict[str, float] | None = Field(default=None, description="Where the anchor stands.")
    anchor: Literal["feet", "center", "pivot"] = Field(default="feet")
    height: float | None = Field(default=None, description="Height of the character on canvas.")
    scale: float | None = Field(default=None, description="Canvas pixels per image pixel.")
    flip: bool = Field(default=False, description="Mirror the character horizontally.")
    z: float = Field(default=0.0, description="Stacking in the scene; higher is in front.")
    actions: list[MotionAction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Compiled rig
# ---------------------------------------------------------------------------


@dataclass
class RigPart:
    name: str
    role: str | None
    parent: str | None
    rot_layer: str
    rest_angle: float = 0.0


@dataclass
class CompiledRig:
    """Everything needed to build and later animate one character."""

    character_id: str
    root_group: str
    pos_layer: str
    position: tuple[float, float]
    height_units: float
    parts: dict[str, RigPart] = field(default_factory=dict)
    layers: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "root_group": self.root_group,
            "position_layer": self.pos_layer,
            "parts": [
                {"name": p.name, "role": p.role, "parent": p.parent, "joint_layer": p.rot_layer}
                for p in self.parts.values()
            ],
            "notes": self.notes,
        }

    def by_role(self) -> dict[str, RigPart]:
        return {p.role: p for p in self.parts.values() if p.role}


def vector(x: float, y: float) -> dict[str, Any]:
    return {"type": "vector", "x": round(x, 6), "y": round(y, 6)}


def angle(degrees: float) -> dict[str, Any]:
    return {"type": "angle", "degrees": round(degrees, 4)}


def _point_in_image(
    spec: dict[str, float] | None, size: tuple[int, int], default: tuple[float, float]
) -> tuple[float, float]:
    """Resolve {fx, fy} / {x, y} to pixels inside an image of ``size``."""
    width, height = size
    if spec is None:
        return (default[0] * width, default[1] * height)
    if "fx" in spec or "fy" in spec:
        return (float(spec.get("fx", 0.5)) * width, float(spec.get("fy", 0.5)) * height)
    if "x" in spec or "y" in spec:
        return (float(spec.get("x", width / 2)), float(spec.get("y", height / 2)))
    raise SpecError(f"A pivot/attach point needs fx, fy or x, y - got {sorted(spec)}.")


def load_manifest_parts(manifest_path: str) -> list[CutoutPart]:
    """Read the parts written by ``rig_sheet_slice``."""
    path = validate_path(
        manifest_path, allowed_extensions={".json"}, must_exist=True, user_intent=True
    )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [
            CutoutPart(name=str(p["name"]), file=str(p["file"]), bbox=p.get("bbox"))
            for p in data["parts"]
        ]
    except (KeyError, TypeError, ValueError) as err:
        raise SpecError(f"'{manifest_path}' is not a rig sheet manifest: {err}") from err


def _image_size(file_path: str) -> tuple[Path, tuple[int, int]]:
    path = validate_path(
        file_path, allowed_extensions=IMAGE_EXTENSIONS, must_exist=True, user_intent=True
    )
    try:
        with Image.open(path) as img:
            return path, (img.width, img.height)
    except Exception as err:
        raise SpecError(f"Cannot read part image '{file_path}': {err}") from err


def compile_character(spec: CutoutCharacter, frame: CanvasFrame) -> CompiledRig:
    """Turn a character spec into layers and groups, validating everything first."""
    char = spec.id
    if not _ID_PATTERN.match(char):
        raise SpecError(
            f"Character id '{char}' must start with a letter and use only letters, digits and '_'."
        )
    parts = list(spec.parts)
    if spec.manifest:
        known = {p.name for p in parts}
        parts += [p for p in load_manifest_parts(spec.manifest) if p.name not in known]
    if not parts:
        raise SpecError(f"Character '{char}' has no parts. Give 'parts' or a 'manifest'.")

    names = [p.name for p in parts]
    for name in names:
        if not _ID_PATTERN.match(name):
            raise SpecError(f"Part name '{name}' must use only letters, digits and '_'.")
    repeated = sorted({n for n in names if names.count(n) > 1})
    if repeated:
        raise SpecError(f"Character '{char}' has repeated part names: {repeated}.")
    by_name = {p.name: p for p in parts}
    notes: list[str] = []

    roles: dict[str, str | None] = {p.name: (p.role or infer_role(p.name)) for p in parts}
    role_owner: dict[str, str] = {}
    for name, role in roles.items():
        if role and role not in role_owner:
            role_owner[role] = name

    # --- root -------------------------------------------------------------
    root = spec.root
    if root is not None and root not in by_name:
        raise SpecError(f"Root part '{root}' is not one of the parts {names}.")
    if root is None:
        root = role_owner.get("torso") or role_owner.get("hips")
    if root is None:
        orphans = [p.name for p in parts if p.parent is None]
        root = orphans[0] if orphans else names[0]

    # --- parents ----------------------------------------------------------
    parents: dict[str, str | None] = {}
    for part in parts:
        if part.name == root:
            parents[part.name] = None
            continue
        if part.parent is not None:
            if part.parent not in by_name:
                raise SpecError(
                    f"Part '{part.name}' has parent '{part.parent}', which is not a part. "
                    f"Parts: {names}."
                )
            parents[part.name] = part.parent
            continue
        base, side = split_role(roles[part.name])
        chosen: str | None = None
        if base in HUMANOID:
            for candidate in HUMANOID[base].parents:
                owner = role_owner.get(f"{candidate}_{side}" if side else candidate)
                owner = owner or role_owner.get(candidate)
                if owner and owner != part.name:
                    chosen = owner
                    break
        parents[part.name] = chosen or root

    for name in names:  # cycle check
        seen = {name}
        cursor = parents[name]
        while cursor is not None:
            if cursor in seen:
                raise SpecError(f"Part hierarchy of '{char}' has a cycle through '{cursor}'.")
            seen.add(cursor)
            cursor = parents[cursor]

    children: dict[str, list[str]] = {n: [] for n in names}
    for name, parent in parents.items():
        if parent is not None:
            children[parent].append(name)

    # --- geometry in image pixels ----------------------------------------
    primitive = {p.name for p in parts if p.primitive_type}
    files: dict[str, Path] = {}
    sizes: dict[str, tuple[int, int]] = {}
    for part in parts:
        if part.name in primitive:
            continue
        if not part.file:
            raise SpecError(f"Part '{part.name}' needs a 'file' (or a 'primitive_type').")
        files[part.name], sizes[part.name] = _image_size(part.file)

    pivots: dict[str, tuple[float, float]] = {}  # in own image pixels
    top_left: dict[str, tuple[float, float]] = {}  # in assembled pixels
    z_order: dict[str, float] = {}

    def place(name: str) -> None:
        part = by_name[name]
        base, side = split_role(roles[name])
        default = HUMANOID.get(base or "")
        parent = parents[name]
        if name in primitive:
            z_order[name] = part.z if part.z is not None else 0.0
            for child in children[name]:
                place(child)
            return
        size = sizes[name]
        root_default = (0.5, 0.92) if parent is None else (0.5, 0.5)
        pivots[name] = _point_in_image(part.pivot, size, default.pivot if default else root_default)
        if part.z is not None:
            z_order[name] = part.z
        elif default:
            z_order[name] = default.z_left if side == "l" else default.z_right
        else:
            z_order[name] = 1.0

        in_place = spec.layout == "in_place"
        if in_place and part.bbox is None:
            if part.attach is not None or default is not None or parent is None:
                part.bbox = {"x": 0, "y": 0, "width": sizes[name][0], "height": sizes[name][1]}
            else:
                raise SpecError(f"Layout 'in_place' requires 'bbox' or 'attach' on part '{name}'.")
        if parent is None:
            top_left[name] = (
                (float(part.bbox["x"]), float(part.bbox["y"]))
                if in_place and part.bbox is not None
                else (0.0, 0.0)
            )
        elif part.attach is None and in_place and part.bbox is not None:
            top_left[name] = (float(part.bbox["x"]), float(part.bbox["y"]))
        elif part.attach is not None or default is not None:
            if parent in primitive:
                raise SpecError(f"Image part '{name}' cannot hang on primitive part '{parent}'.")
            parent_size = sizes[parent]
            if part.attach is not None:
                spot = _point_in_image(part.attach, parent_size, (0.5, 0.5))
            else:
                assert default is not None
                parent_base, _ = split_role(roles[parent])
                if parent_base in ("torso", "hips", None):
                    fx, fy = default.attach_torso
                    if side == "l":
                        fx = 1.0 - fx
                    elif side is None:
                        fx = 0.5
                else:
                    fx, fy = default.attach_limb
                spot = (fx * parent_size[0], fy * parent_size[1])
            top_left[name] = (
                top_left[parent][0] + spot[0] - pivots[name][0],
                top_left[parent][1] + spot[1] - pivots[name][1],
            )
        elif part.bbox is not None and by_name[root].bbox is not None:
            root_box = by_name[root].bbox or {}
            top_left[name] = (
                float(part.bbox["x"]) - float(root_box["x"]) + top_left[root][0],
                float(part.bbox["y"]) - float(root_box["y"]) + top_left[root][1],
            )
            notes.append(
                f"Part '{name}' has no known body role and no 'attach'; it keeps its sheet "
                "position relative to the root. Give 'parent' and 'attach' to place it."
            )
        else:
            raise SpecError(
                f"Part '{name}' has no known body role. Give it 'parent' and 'attach' "
                "(where its joint sits on the parent), or a 'role'."
            )
        for child in children[name]:
            place(child)

    place(root)

    # --- scale and anchor -------------------------------------------------
    image_parts = [n for n in names if n not in primitive]
    scale_px = 1.0  # canvas pixels per image pixel
    origin_px = (0.0, 0.0)
    height_units = 1.0
    if image_parts:
        min_x = min(top_left[n][0] for n in image_parts)
        min_y = min(top_left[n][1] for n in image_parts)
        max_x = max(top_left[n][0] + sizes[n][0] for n in image_parts)
        max_y = max(top_left[n][1] + sizes[n][1] for n in image_parts)
        box_h = max(1.0, max_y - min_y)
        upp = frame.units_per_pixel
        if spec.scale is not None:
            if spec.scale <= 0:
                raise SpecError("Character 'scale' must be positive.")
            scale_px = spec.scale
        elif spec.height is not None:
            if spec.height <= 0:
                raise SpecError("Character 'height' must be positive.")
            scale_px = frame.length(spec.height) / upp / box_h
        else:
            scale_px = min(1.0, 0.6 * frame.height / box_h)
        height_units = box_h * scale_px * upp
        if spec.anchor == "feet":
            origin_px = ((min_x + max_x) / 2, max_y)
        elif spec.anchor == "center":
            origin_px = ((min_x + max_x) / 2, (min_y + max_y) / 2)
        elif root in pivots:
            origin_px = (top_left[root][0] + pivots[root][0], top_left[root][1] + pivots[root][1])
    k = scale_px * frame.units_per_pixel

    def local(px: float, py: float) -> tuple[float, float]:
        return ((px - origin_px[0]) * k, -(py - origin_px[1]) * k)

    # --- layers (bottom to top) and groups (inner first) ------------------
    layers: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    rig_parts: dict[str, RigPart] = {}

    def emit(name: str) -> str:
        part = by_name[name]
        kids = sorted(children[name], key=lambda c: z_order[c])
        members: list[str] = []
        for child in (c for c in kids if z_order[c] < 0):
            members.append(emit(child))
        art_id = f"{char}_{name}_img"
        if name in primitive:
            params = dict(part.primitive_params)
            if part.origin is not None:
                params.setdefault(
                    "origin", vector(float(part.origin.get("x", 0)), float(part.origin.get("y", 0)))
                )
            layers.append({"id": art_id, "type": part.primitive_type, "params": params})
            joint = (
                (float(part.origin.get("x", 0.0)), float(part.origin.get("y", 0.0)))
                if part.origin
                else (0.0, 0.0)
            )
        else:
            x0, y0 = top_left[name]
            width, height = sizes[name]
            layers.append(
                {
                    "id": art_id,
                    "type": "import",
                    "params": {
                        "filename": {"type": "string", "value": str(files[name])},
                        "tl": vector(*local(x0, y0)),
                        "br": vector(*local(x0 + width, y0 + height)),
                    },
                }
            )
            joint = local(x0 + pivots[name][0], y0 + pivots[name][1])
        members.append(art_id)
        for child in (c for c in kids if z_order[c] >= 0):
            members.append(emit(child))
        rot_id = f"{char}_{name}_rot"
        layers.append(
            {
                "id": rot_id,
                "type": "rotate",
                "params": {"origin": vector(*joint), "amount": angle(part.rest_angle)},
            }
        )
        members.append(rot_id)
        group_id = f"{char}_{name}"
        groups.append({"id": group_id, "layer_ids": members})
        rig_parts[name] = RigPart(name, roles[name], parents[name], rot_id, part.rest_angle)
        return group_id

    root_part_group = emit(root)
    root_members = [root_part_group]
    if spec.flip:
        flip_id = f"{char}_flip"
        layers.append(
            {
                "id": flip_id,
                "type": "stretch",
                "params": {"amount": vector(-1.0, 1.0), "center": vector(0.0, 0.0)},
            }
        )
        root_members.append(flip_id)

    if spec.position is not None:
        position = frame.point(float(spec.position.get("x", 0)), float(spec.position.get("y", 0)))
    elif frame.coords == "units":
        position = (0.0, frame.bottom + 0.12 * abs(frame.top - frame.bottom))
    else:
        position = frame.point(frame.width / 2, frame.height * 0.88)
    pos_id = f"{char}_pos"
    layers.append({"id": pos_id, "type": "translate", "params": {"origin": vector(*position)}})
    root_members.append(pos_id)
    root_group = f"Character_{char}"
    groups.append({"id": root_group, "layer_ids": root_members})

    return CompiledRig(
        character_id=char,
        root_group=root_group,
        pos_layer=pos_id,
        position=position,
        height_units=height_units,
        parts=rig_parts,
        layers=layers,
        groups=groups,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Motion library
# ---------------------------------------------------------------------------

Curve = list[tuple[float, float]]


@dataclass(frozen=True)
class Motion:
    """Joint angle curves over one cycle (phase 0..1), in degrees from the rest pose.

    Positive angles turn counter-clockwise.  For a limb that hangs down this
    swings it towards +x, which is "forward" for a character facing right; a
    flipped character mirrors the motion automatically.
    """

    description: str
    period: float
    loop: bool
    angles: dict[str, Curve]
    bob: Curve = field(default_factory=list)  # vertical offset, fraction of character height


def _swing(amplitude: float, shift: float = 0.0) -> Curve:
    """A cosine-like swing sampled at quarter phases."""
    return [
        (p, round(amplitude * math.cos(2 * math.pi * (p + shift)), 3))
        for p in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]


MOTIONS: dict[str, Motion] = {
    "idle": Motion(
        "Gentle breathing and sway; loops.",
        3.0,
        True,
        {
            "torso": [(0, 0), (0.5, 1.5), (1, 0)],
            "head": [(0, 0), (0.5, -2.5), (1, 0)],
            "upper_arm_r": [(0, 0), (0.5, 3), (1, 0)],
            "upper_arm_l": [(0, 0), (0.5, -3), (1, 0)],
        },
        [(0, 0), (0.5, 0.006), (1, 0)],
    ),
    "walk": Motion(
        "Walk cycle, one second per two steps; loops. Combine with move_to.",
        1.0,
        True,
        {
            "torso": [(0, -3), (1, -3)],
            "head": [(0, 2), (0.5, 3), (1, 2)],
            "upper_leg_r": _swing(26),
            "upper_leg_l": _swing(26, 0.5),
            "lower_leg_r": [(0, 0), (0.25, -6), (0.5, -12), (0.75, -48), (1, 0)],
            "lower_leg_l": [(0, -12), (0.25, -48), (0.5, 0), (0.75, -6), (1, -12)],
            "foot_r": [(0, 12), (0.25, 0), (0.5, -14), (0.75, 4), (1, 12)],
            "foot_l": [(0, -14), (0.25, 4), (0.5, 12), (0.75, 0), (1, -14)],
            "upper_arm_r": _swing(22, 0.5),
            "upper_arm_l": _swing(22),
            "forearm_r": [(0, 12), (0.5, 26), (1, 12)],
            "forearm_l": [(0, 26), (0.5, 12), (1, 26)],
        },
        [(0, -0.012), (0.25, 0.012), (0.5, -0.012), (0.75, 0.012), (1, -0.012)],
    ),
    "run": Motion(
        "Run cycle; loops. Combine with move_to.",
        0.6,
        True,
        {
            "torso": [(0, -10), (1, -10)],
            "head": [(0, 6), (1, 6)],
            "upper_leg_r": _swing(42),
            "upper_leg_l": _swing(42, 0.5),
            "lower_leg_r": [(0, -10), (0.25, -25), (0.5, -40), (0.75, -85), (1, -10)],
            "lower_leg_l": [(0, -40), (0.25, -85), (0.5, -10), (0.75, -25), (1, -40)],
            "upper_arm_r": _swing(48, 0.5),
            "upper_arm_l": _swing(48),
            "forearm_r": [(0, 70), (0.5, 85), (1, 70)],
            "forearm_l": [(0, 85), (0.5, 70), (1, 85)],
        },
        [(0, -0.02), (0.25, 0.03), (0.5, -0.02), (0.75, 0.03), (1, -0.02)],
    ),
    "wave": Motion(
        "Raise the right arm and wave; plays once.",
        2.0,
        False,
        {
            "upper_arm_r": [(0, 0), (0.2, 150), (0.8, 150), (1, 0)],
            "forearm_r": [
                (0, 0),
                (0.2, 20),
                (0.35, -25),
                (0.5, 20),
                (0.65, -25),
                (0.8, 20),
                (1, 0),
            ],
            "head": [(0, 0), (0.2, 5), (0.8, 5), (1, 0)],
        },
    ),
    "jump": Motion(
        "Crouch, jump and land; plays once.",
        1.2,
        False,
        {
            "torso": [(0, 0), (0.2, -8), (0.45, 4), (0.85, -4), (1, 0)],
            "upper_leg_r": [(0, 0), (0.2, 38), (0.45, -5), (0.85, 20), (1, 0)],
            "upper_leg_l": [(0, 0), (0.2, 38), (0.45, -5), (0.85, 20), (1, 0)],
            "lower_leg_r": [(0, 0), (0.2, -75), (0.45, 0), (0.85, -40), (1, 0)],
            "lower_leg_l": [(0, 0), (0.2, -75), (0.45, 0), (0.85, -40), (1, 0)],
            "upper_arm_r": [(0, 0), (0.2, -35), (0.45, 150), (0.85, 30), (1, 0)],
            "upper_arm_l": [(0, 0), (0.2, 35), (0.45, -150), (0.85, -30), (1, 0)],
        },
        [(0, 0), (0.2, -0.07), (0.5, 0.35), (0.8, 0), (0.88, -0.04), (1, 0)],
    ),
    "nod": Motion(
        "Nod the head twice; plays once.",
        1.0,
        False,
        {"head": [(0, 0), (0.25, -9), (0.5, 0), (0.75, -9), (1, 0)]},
    ),
    "talk": Motion(
        "Small head and body movement while speaking; loops.",
        0.6,
        True,
        {
            "head": [(0, 0), (0.3, 3), (0.6, -2), (1, 0)],
            "torso": [(0, 0), (0.5, 1), (1, 0)],
            "upper_arm_r": [(0, 0), (0.5, 6), (1, 0)],
        },
    ),
}

#: Motions that are handled without a curve table.
SPECIAL_MOTIONS = {
    "rest": "Return every joint to the rest pose at 'start'.",
    "pose": "Set the joint angles given in 'angles' at 'start'.",
    "move": "Only move to 'move_to' between 'start' and 'end'.",
}

#: How long a looping motion takes to ease back to the rest pose.
SETTLE_SECONDS = 0.3

#: Single-piece limbs take the motion of the upper segment.
_ROLE_ALIASES = {"upper_arm": "arm", "upper_leg": "leg"}


def motion_catalog() -> dict[str, str]:
    """Name -> description of every motion."""
    catalog = {name: motion.description for name, motion in MOTIONS.items()}
    catalog.update(SPECIAL_MOTIONS)
    return catalog


def _sample(curve: Curve, phase: float) -> float:
    """Linear sample of a curve at ``phase``."""
    if phase <= curve[0][0]:
        return curve[0][1]
    for (p0, v0), (p1, v1) in zip(curve, curve[1:], strict=False):
        if p0 <= phase <= p1:
            if p1 == p0:
                return v1
            return v0 + (v1 - v0) * (phase - p0) / (p1 - p0)
    return curve[-1][1]


def _curve_times(
    curve: Curve, start: float, end: float, period: float, loop: bool
) -> list[tuple[float, float]]:
    """Expand a phase curve into (time, value) keys between ``start`` and ``end``."""
    keys: dict[float, float] = {}
    span = end - start
    if span <= 0:
        return [(round(start, 4), curve[0][1])]
    if not loop:
        for phase, value in curve:
            keys[round(start + phase * span, 4)] = value
        return sorted(keys.items())
    cycle = 0
    while start + cycle * period < end - 1e-6:
        for phase, value in curve:
            t = start + (cycle + phase) * period
            if t <= end + 1e-6:
                keys[round(t, 4)] = value
        cycle += 1
    final_phase = (span / period) % 1.0
    if final_phase > 1e-6:
        keys[round(end, 4)] = _sample(curve, final_phase)
    return sorted(keys.items())


def resolve_part(rig: CompiledRig, key: str) -> RigPart | None:
    """Find a part by name or by role."""
    if key in rig.parts:
        return rig.parts[key]
    roles = rig.by_role()
    if key in roles:
        return roles[key]
    base, side = split_role(key)
    alias = _ROLE_ALIASES.get(base or "")
    if alias:
        return roles.get(f"{alias}_{side}" if side else alias)
    if side is None:  # "head" style keys never need a side; limbs without one match either
        return roles.get(f"{key}_r") or roles.get(f"{key}_l")
    return None


@dataclass
class MotionPlan:
    """Waypoints to write: layer id -> parameter -> list of waypoint dicts."""

    tracks: dict[str, dict[str, dict[float, dict[str, Any]]]] = field(default_factory=dict)
    applied: list[str] = field(default_factory=list)
    skipped_roles: list[str] = field(default_factory=list)
    end_time: float = 0.0
    settles: list[tuple[str, float, float]] = field(default_factory=list)  # layer, end, rest

    def add(self, layer: str, param: str, time: float, value: dict[str, Any], interp: str) -> None:
        slot = self.tracks.setdefault(layer, {}).setdefault(param, {})
        slot[round(time, 4)] = {"time": round(time, 4), "value": value, "interpolation": interp}
        self.end_time = max(self.end_time, time)

    def waypoints(self, layer: str, param: str) -> list[dict[str, Any]]:
        return [wp for _t, wp in sorted(self.tracks.get(layer, {}).get(param, {}).items())]

    def count(self) -> int:
        return sum(len(keys) for params in self.tracks.values() for keys in params.values())


def plan_action(
    rig: CompiledRig,
    action: MotionAction,
    frame: CanvasFrame | None,
    plan: MotionPlan,
    default_end: float,
    position: tuple[float, float],
) -> tuple[float, float]:
    """Add the waypoints of one action to ``plan``; returns the position afterwards."""
    name = action.motion.lower().strip()
    if name not in MOTIONS and name not in SPECIAL_MOTIONS:
        raise SpecError(
            f"Unknown motion '{action.motion}'. Available: {', '.join(sorted(motion_catalog()))}."
        )
    start = action.start
    motion = MOTIONS.get(name)

    if action.end is not None:
        end = action.end
    elif motion is not None and not motion.loop:
        end = start + motion.period / action.speed
    elif name in ("rest", "pose"):
        end = start
    else:
        end = default_end
    if end < start:
        raise SpecError(f"Action '{name}' of '{rig.character_id}' ends ({end}) before it starts.")

    if name == "rest":
        for part in rig.parts.values():
            plan.add(part.rot_layer, "amount", start, angle(part.rest_angle), "clamped")
        plan.applied.append(name)
    elif name == "pose":
        if not action.angles:
            raise SpecError("Motion 'pose' needs 'angles': {part or role: degrees}.")
        for key, degrees in action.angles.items():
            joint = resolve_part(rig, key)
            if joint is None:
                raise SpecError(
                    f"Pose refers to '{key}', which is neither a part nor a role of "
                    f"'{rig.character_id}'. Parts: {sorted(rig.parts)}."
                )
            plan.add(
                joint.rot_layer,
                "amount",
                start,
                angle(joint.rest_angle + float(degrees)),
                "clamped",
            )
        plan.applied.append(name)
    elif motion is not None:
        period = motion.period / action.speed
        matched = 0
        for role, curve in motion.angles.items():
            joint = resolve_part(rig, role)
            if joint is None:
                plan.skipped_roles.append(role)
                continue
            matched += 1
            for t, value in _curve_times(curve, start, end, period, motion.loop):
                plan.add(joint.rot_layer, "amount", t, angle(joint.rest_angle + value), "clamped")
            if motion.loop and action.settle and end > start:
                plan.settles.append((joint.rot_layer, end, joint.rest_angle))
        if matched == 0 and action.move_to is None:
            raise SpecError(
                f"Motion '{name}' moves {sorted(motion.angles)}, but '{rig.character_id}' has none "
                f"of these parts (roles found: {sorted(rig.by_role())}). Name the parts by body "
                "role or set 'role' on them."
            )
        plan.applied.append(name)

    # --- position track ---------------------------------------------------
    target = position
    if action.move_to is not None:
        if frame is None:
            target = (float(action.move_to.get("x", 0)), float(action.move_to.get("y", 0)))
        else:
            target = frame.point(
                float(action.move_to.get("x", 0)), float(action.move_to.get("y", 0))
            )
        if name == "move":
            plan.applied.append(name)
    elif name == "move":
        raise SpecError("Motion 'move' needs 'move_to': {x, y}.")

    bob = motion.bob if motion is not None else []
    moving = action.move_to is not None and end > start
    if bob or moving:
        times = {round(start, 4), round(end, 4)}
        bob_keys: dict[float, float] = {}
        if bob and motion is not None:
            period = motion.period / action.speed
            bob_keys = dict(_curve_times(bob, start, end, period, motion.loop))
            times |= set(bob_keys)
        span = max(end - start, 1e-9)
        for t in sorted(times):
            ratio = min(1.0, max(0.0, (t - start) / span)) if moving else 0.0
            x = position[0] + (target[0] - position[0]) * ratio
            y = position[1] + (target[1] - position[1]) * ratio
            lift = bob_keys.get(t)
            if lift is None and bob and motion is not None:
                lift = 0.0
            y += (lift or 0.0) * rig.height_units
            plan.add(rig.pos_layer, "origin", t, vector(x, y), "linear" if moving else "clamped")
    elif action.move_to is not None:
        plan.add(rig.pos_layer, "origin", start, vector(*target), "clamped")
    plan.end_time = max(plan.end_time, end)
    return target


def plan_actions(
    rig: CompiledRig,
    actions: list[MotionAction],
    frame: CanvasFrame | None,
    default_end: float,
) -> MotionPlan:
    """Plan every action of a character in timeline order."""
    plan = MotionPlan()
    position = rig.position
    for action in sorted(actions, key=lambda a: a.start):
        position = plan_action(rig, action, frame, plan, default_end, position)
    # A walk that stops mid-stride eases back to the rest pose, unless the joint
    # is keyed again right away or the scene ends there.
    for layer, end, rest in plan.settles:
        settle_at = round(end + SETTLE_SECONDS, 4)
        keys = plan.tracks.get(layer, {}).get("amount", {})
        if settle_at <= default_end + 1e-6 and not any(end < t <= settle_at for t in keys):
            keys[settle_at] = {"time": settle_at, "value": angle(rest), "interpolation": "clamped"}
    plan.skipped_roles = sorted(set(plan.skipped_roles))
    return plan


def attach_waypoints(rig: CompiledRig, plan: MotionPlan) -> None:
    """Write the planned waypoints into the layer specs of a rig that is not built yet."""
    by_id = {layer["id"]: layer for layer in rig.layers}
    for layer_id, params in plan.tracks.items():
        layer = by_id[layer_id]
        waypoints = layer.setdefault("waypoints", [])
        for param in params:
            for wp in plan.waypoints(layer_id, param):
                waypoints.append(
                    {
                        "param": param,
                        "time": wp["time"],
                        "value": wp["value"],
                        "interpolation": wp["interpolation"],
                    }
                )
