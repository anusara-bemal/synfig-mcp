# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Project validation: structural and semantic checks for .sif documents."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any

from lxml import etree

# Layer types present in Synfig 1.5.x (from `synfig --layers`); unknown types are
# reported as warnings rather than hard errors so newer builds keep working.
KNOWN_LAYER_TYPES = {
    "advanced_outline",
    "bevel",
    "blur",
    "checker_board",
    "chromakey",
    "circle",
    "clamp",
    "colorcorrect",
    "conical_gradient",
    "curve_gradient",
    "curve_warp",
    "duplicate",
    "filter_group",
    "freetime",
    "group",
    "halftone2",
    "halftone3",
    "import",
    "inside_out",
    "julia",
    "linear_gradient",
    "lumakey",
    "mandelbrot",
    "metaballs",
    "motion_blur",
    "noise",
    "noise_distort",
    "outline",
    "plant",
    "polygon",
    "radial_blur",
    "radial_gradient",
    "rectangle",
    "region",
    "rotate",
    "shade",
    "simple_circle",
    "skeleton",
    "skeleton_deformation",
    "solid_color",
    "sound",
    "spherize",
    "spiral_gradient",
    "star",
    "stretch",
    "stroboscope",
    "super_sample",
    "switch",
    "text",
    "timeloop",
    "translate",
    "twirl",
    "warp",
    "xor_pattern",
    "zoom",
}
CANVAS_ATTRS = (
    "width",
    "height",
    "xres",
    "yres",
    "view-box",
    "antialias",
    "fps",
    "begin-time",
    "end-time",
)


def validate_document(
    root: etree._Element,
    *,
    max_resolution: int = 8192,
    max_layers: int = 5000,
    known_layer_types: set[str] | None = None,
) -> dict[str, Any]:
    known = known_layer_types or KNOWN_LAYER_TYPES
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def add(level: str, code: str, message: str, hint: str | None = None) -> None:
        entry = {"level": level, "code": code, "message": message}
        if hint:
            entry["hint"] = hint
        (errors if level == "error" else warnings).append(entry)

    if root.tag != "canvas":
        add("error", "root_tag", f"Root element is <{root.tag}>, expected <canvas>.")
        return {"valid": False, "errors": errors, "warnings": warnings, "summary": {}}

    # Canvas attributes
    for attr in ("width", "height"):
        raw = root.get(attr)
        try:
            value = int(float(raw or ""))
            if value < 1 or value > max_resolution:
                add("error", "resolution_range", f"{attr}={value} outside 1..{max_resolution}.")
        except ValueError:
            add(
                "error",
                "resolution_missing",
                f"Canvas is missing a valid '{attr}' attribute (got {raw!r}).",
            )
    try:
        fps = float(root.get("fps", "24"))
        if fps <= 0:
            add("error", "fps_range", "fps must be > 0.")
    except ValueError:
        add("error", "fps_invalid", f"fps is not numeric: {root.get('fps')!r}")
    for attr in ("xres", "yres"):
        if root.get(attr) is not None:
            try:
                if float(root.get(attr, "0")) <= 0:
                    add("error", "res_range", f"{attr} must be positive.")
            except ValueError:
                add("error", "res_invalid", f"{attr} is not numeric: {root.get(attr)!r}")
    if root.get("view-box"):
        parts = (root.get("view-box") or "").split()
        if len(parts) != 4:
            add("error", "view_box_format", "view-box must have exactly 4 numbers.")
        else:
            try:
                [float(p) for p in parts]
            except ValueError:
                add("error", "view_box_format", "view-box contains non-numeric values.")
    else:
        add(
            "warning",
            "view_box_missing",
            "Canvas has no view-box; Studio will use its own default.",
        )

    # version
    if not root.get("version"):
        add(
            "warning",
            "version_missing",
            "Canvas has no version attribute; older Synfig files may fail to load.",
        )

    # defs ids unique + valid
    defs = root.find("defs")
    seen_ids: dict[str, int] = {}
    if defs is not None:
        for child in defs:
            if not isinstance(child.tag, str) or not child.get("id"):
                continue
            ident = child.get("id", "")
            seen_ids[ident] = seen_ids.get(ident, 0) + 1
            if any(ch in ident for ch in " :#@$^&()*\t\n\r"):
                add("error", "defs_id_invalid", f"defs id {ident!r} contains invalid characters.")
    for ident, count in seen_ids.items():
        if count > 1:
            add("error", "defs_id_duplicate", f"defs id {ident!r} is defined {count} times.")

    # Bones section well-formed
    bones = root.find("bones")
    if bones is not None:
        bone_ids = [b.get("id") for b in bones.findall("bone") if b.get("id")]
        for ident in set(bone_ids):
            if bone_ids.count(ident) > 1:
                add("error", "bone_id_duplicate", f"Bone id {ident!r} defined multiple times.")
        root_bones = bones.findall("bone_root")
        if len(root_bones) > 1:
            add(
                "error",
                "bone_root_duplicate",
                "Multiple <bone_root> entries; expected at most one.",
            )

    # Layers
    layers = list(root.iter("layer"))
    if len(layers) > max_layers:
        add("error", "layer_limit", f"{len(layers)} layers exceed the limit of {max_layers}.")
    descs: dict[str, int] = {}
    for layer in layers:
        ltype = layer.get("type") or ""
        if not ltype:
            add("error", "layer_type_missing", "A <layer> is missing its type attribute.")
        elif ltype not in known:
            close = get_close_matches(ltype, sorted(known), n=3, cutoff=0.45)
            hint = f"Did you mean: {', '.join(close)}?" if close else None
            add(
                "warning",
                "layer_type_unknown",
                f"Layer type {ltype!r} is unknown to this validator (may be from a newer Synfig).",
                hint,
            )
        desc = layer.get("desc")
        if desc:
            descs[desc] = descs.get(desc, 0) + 1
        # every param needs a name
        for param in layer.findall("param"):
            if not param.get("name"):
                add(
                    "error",
                    "param_name_missing",
                    f"Layer type={ltype!r} has a <param> without a name.",
                )
    duplicates = {name: count for name, count in descs.items() if count > 1}
    for name, count in list(duplicates.items())[:10]:
        add(
            "warning",
            "layer_desc_duplicate",
            f"{count} layers share desc {name!r}; selection by name may be ambiguous.",
        )

    # Keyframes parseable
    from .timeutil import parse_time

    for kf in root.findall("keyframe"):
        try:
            parse_time(kf.get("time", ""))
        except Exception:
            add(
                "error",
                "keyframe_time_unparsable",
                f"Keyframe time {kf.get('time')!r} is not parseable.",
            )

    summary = {
        "layers": len(layers),
        "defs_ids": len(seen_ids),
        "keyframes": len(root.findall("keyframe")),
        "bones": len(bones.findall("bone")) if bones is not None else 0,
        "exported_values": len(seen_ids),
    }
    return {"valid": not errors, "errors": errors, "warnings": warnings, "summary": summary}
