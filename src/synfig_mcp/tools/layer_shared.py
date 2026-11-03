# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Shared internals for tools that create/modify layers."""

from __future__ import annotations

import copy
import secrets
from typing import Any

from lxml import etree

from ..document import layers as lay
from ..document.canvas import parse_blend_method
from ..errors import ParameterError

V02_TYPES = {"group", "switch", "timeloop", "text"}

BLEND_NAMES = {
    0: "composite",
    1: "straight",
    2: "brighten",
    3: "darken",
    4: "add",
    5: "subtract",
    6: "multiply",
    7: "divide",
    8: "color",
    9: "hue",
    10: "saturation",
    11: "luminance",
    12: "behind",
    13: "onto",
    14: "alpha_brighten",
    15: "alpha_darken",
    16: "screen",
    17: "hard_light",
    18: "difference",
    19: "alpha_over",
    20: "overlay",
    21: "straight_onto",
    22: "add_composite",
    23: "alpha",
    24: "alpha_intersection",
}


def blend_name(value: int) -> str:
    return BLEND_NAMES.get(value, f"unknown({value})")


def default_version(layer_type: str) -> str:
    return "0.2" if layer_type in V02_TYPES else "0.1"


def ensure_z_depth(layer: etree._Element) -> None:
    if lay.get_param_or_none(layer, "z_depth") is None:
        lay.set_or_create_param(layer, "z_depth", 0.0, tag="real")


def ensure_amount(layer: etree._Element) -> None:
    if lay.get_param_or_none(layer, "amount") is None:
        lay.set_or_create_param(layer, "amount", 1.0, tag="real")


def ensure_blend(layer: etree._Element) -> None:
    if lay.get_param_or_none(layer, "blend_method") is None:
        lay.set_or_create_param(layer, "blend_method", 0, tag="integer")


def set_param(
    layer: etree._Element,
    name: str,
    value: Any,
    *,
    fps: float,
    unit_px: float,
    unit_system: str,
    forced_type: str | None = None,
    vocab: frozenset[str] | None = None,
) -> etree._Element:
    name = name.strip()
    if not name:
        raise ParameterError("Parameter name must not be empty.")
    if vocab is not None and name not in vocab:
        hint = f"Valid params for this layer: {', '.join(sorted(vocab))}"
        raise ParameterError(
            f"Layer type {layer.get('type')!r} has no parameter {name!r}.",
            hint=hint,
        )
    if name.lower() == "blend_method":
        value = parse_blend_method(value)
        forced_type = "integer"
    elif name in {"amount", "z_depth"} and not (
        isinstance(value, (list, tuple)) and len(value) == 2
    ):
        # `stretch` uses a vector `amount`; every other layer's amount is a
        # scalar opacity, so only scalar-looking values are forced to real.
        forced_type = "real"
    elif name.lower() == "gradient":
        forced_type = "gradient"
    elif name.lower() == "bline":
        forced_type = "bline"
    elif name.lower() == "vector_list":
        forced_type = "vector_list"
    elif name == "canvas":
        raise ParameterError("Use set_canvas_inline or apply_template for canvas params.")
    existing = lay.get_param_or_none(layer, name)
    existing_type = None
    if existing is not None and len(existing):
        child = existing[0]
        existing_type = child.tag if isinstance(child.tag, str) else None
    tag = forced_type or existing_type or infer_friendly_type(value)
    if tag == "vector_list":
        from ..document.params import encode_vector_list

        encoded = encode_vector_list(value, unit_px=unit_px, unit_system=unit_system)
        existing = lay.get_param_or_none(layer, name)
        if existing is not None:
            layer.remove(existing)
        param = etree.Element("param", attrib={"name": name})
        param.append(encoded)
        layer.append(param)
        return param
    return lay.set_or_create_param(
        layer,
        name,
        value,
        tag=tag,
        unit_px=unit_px,
        unit_system=unit_system,
        fps=fps,
    )


def infer_friendly_type(value: Any) -> str | None:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "real"
    if isinstance(value, str):
        return "color" if value.strip().startswith("#") else "string"
    if isinstance(value, (list, tuple)):
        if len(value) == 2:
            return "vector"
        if len(value) in (3, 4):
            return "color"
        return "bline"
    if isinstance(value, dict):
        if "pos" in value and "color" in value:
            return "gradient"
        if "vertices" in value:
            return "bline"
        if "x" in value and "y" in value:
            return "vector"
        if "r" in value:
            return "color"
    return None


def clone_with_fresh_guids(element: etree._Element) -> etree._Element:
    clone = copy.deepcopy(element)

    def walk(node: etree._Element) -> None:
        if node.get("guid"):
            node.set("guid", secrets.token_hex(16).upper())
        for child in node:
            if isinstance(child.tag, str):
                walk(child)

    walk(clone)
    return clone
