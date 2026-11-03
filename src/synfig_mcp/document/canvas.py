# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Canvas (project) properties: get/set with validation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lxml import etree

from ..errors import ParameterError
from .timeutil import format_time, parse_time

BLEND_METHODS: dict[str, int] = {
    "composite": 0,
    "straight": 1,
    "brighten": 2,
    "darken": 3,
    "add": 4,
    "subtract": 5,
    "multiply": 6,
    "divide": 7,
    "color": 8,
    "hue": 9,
    "saturation": 10,
    "luminance": 11,
    "behind": 12,
    "onto": 13,
    "alpha_brighten": 14,
    "alpha_darken": 15,
    "screen": 16,
    "hard_light": 17,
    "difference": 18,
    "alpha_over": 19,
    "overlay": 20,
    "straight_onto": 21,
    "add_composite": 22,
    "alpha": 23,
    "alpha_intersection": 24,
}
BLEND_NAMES: dict[int, str] = {value: key for key, value in BLEND_METHODS.items()}


def parse_blend_method(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        intval = int(value)
        if intval not in BLEND_NAMES:
            raise ParameterError(
                f"Unknown blend method integer {intval}.",
                hint="Valid range 0..24. See BLEND_METHODS in docs/tools-reference.md.",
            )
        return intval
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if text in BLEND_METHODS:
        return BLEND_METHODS[text]
    if text.isdigit():
        return parse_blend_method(int(text))
    import difflib

    close = difflib.get_close_matches(text, list(BLEND_METHODS), n=3, cutoff=0.45)
    hint = f"Did you mean: {', '.join(close)}?" if close else "See blend_method values in the docs."
    raise ParameterError(f"Unknown blend method {value!r}.", hint=hint)


def blend_method_name(value: int) -> str:
    return BLEND_NAMES.get(value, f"unknown({value})")


def get_canvas_props(root: etree._Element) -> dict[str, Any]:
    props: dict[str, Any] = {
        "width": _int_attr(root, "width", 0),
        "height": _int_attr(root, "height", 0),
        "xres": _float_attr(root, "xres", 0.0),
        "yres": _float_attr(root, "yres", 0.0),
        "view_box": root.get("view-box"),
        "antialias": _int_attr(root, "antialias", 1),
        "fps": _float_attr(root, "fps", 24.0),
        "begin_time": root.get("begin-time"),
        "end_time": root.get("end-time"),
        "bgcolor": root.get("bgcolor"),
        "background": _parse_bgcolor(root.get("bgcolor")),
        "version": root.get("version"),
        "gamma": (
            _float_attr(root, "gamma-r", None),
            _float_attr(root, "gamma-g", None),
            _float_attr(root, "gamma-b", None),
        ),
    }
    return props


def set_canvas_props(
    root: etree._Element, updates: dict[str, Any], *, max_resolution: int = 8192
) -> dict[str, Any]:
    fps = _float_attr(root, "fps", 24.0)

    def check_dim(name: str, value: Any) -> int:
        try:
            intval = int(value)
        except (TypeError, ValueError) as exc:
            raise ParameterError(f"{name} must be an integer number of pixels.") from exc
        if intval < 1 or intval > max_resolution:
            raise ParameterError(f"{name} must be between 1 and {max_resolution} pixels.")
        return intval

    mapping: dict[str, tuple[str, Callable[[Any], str]]] = {
        "width": ("width", lambda v: str(check_dim("width", v))),
        "height": ("height", lambda v: str(check_dim("height", v))),
        "xres": ("xres", lambda v: _format_float(_positive("xres", v))),
        "yres": ("yres", lambda v: _format_float(_positive("yres", v))),
        "antialias": ("antialias", lambda v: str(_bounded("antialias", v, 1, 30, integer=True))),
        "fps": ("fps", lambda v: _format_float(_bounded("fps", v, 1.0, 240.0))),
        "begin_time": ("begin-time", lambda v: format_time(parse_time(v, fps=fps), fps=fps)),
        "end_time": ("end-time", lambda v: format_time(parse_time(v, fps=fps), fps=fps)),
    }
    applied: dict[str, Any] = {}
    for key, (attr, encoder) in mapping.items():
        if key in updates and updates[key] is not None:
            root.set(attr, encoder(updates[key]))
            applied[key] = updates[key]

    if "view_box" in updates and updates["view_box"] is not None:
        root.set("view-box", _parse_view_box(updates["view_box"]))
        applied["view_box"] = updates["view_box"]

    if "background" in updates and updates["background"] is not None:
        root.set("bgcolor", _format_bgcolor(updates["background"]))
        applied["background"] = updates["background"]

    if "gamma" in updates and updates["gamma"] is not None:
        gamma = updates["gamma"]
        if isinstance(gamma, (int, float)):
            gamma = (float(gamma), float(gamma), float(gamma))
        if not isinstance(gamma, (list, tuple)) or len(gamma) != 3:
            raise ParameterError("gamma must be a number or [r, g, b].")
        for channel, attr in zip(gamma, ("gamma-r", "gamma-g", "gamma-b"), strict=True):
            value = float(channel)
            if not 0.0 <= value <= 10.0:
                raise ParameterError("gamma channels must be between 0 and 10.")
            root.set(attr, _format_float(value))
        applied["gamma"] = [float(c) for c in gamma]

    return applied


def _int_attr(root: etree._Element, name: str, default: int | None) -> int:
    raw = root.get(name)
    if raw is None:
        return int(default) if default is not None else 0
    try:
        return int(float(raw))
    except ValueError:
        return int(default) if default is not None else 0


def _float_attr(root: etree._Element, name: str, default: float | None) -> float:
    raw = root.get(name)
    if raw is None:
        return float(default) if default is not None else 0.0
    try:
        return float(raw)
    except ValueError:
        return float(default) if default is not None else 0.0


def _positive(name: str, value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ParameterError(f"{name} must be a positive number.") from exc
    if number <= 0:
        raise ParameterError(f"{name} must be a positive number.")
    return number


def _bounded(
    name: str, value: Any, low: float, high: float, *, integer: bool = False
) -> float | int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ParameterError(f"{name} must be a number between {low} and {high}.") from exc
    if not low <= number <= high:
        raise ParameterError(f"{name} must be between {low} and {high}.")
    return int(number) if integer else number


def _format_float(value: float) -> str:
    return f"{value:.6f}"


def _parse_view_box(value: Any) -> str:
    if isinstance(value, str):
        parts = value.split()
        if len(parts) == 4:
            try:
                floats = [float(p) for p in parts]
            except ValueError as exc:
                raise ParameterError("view-box string must be 'minx maxy maxx miny'.") from exc
            return " ".join(f"{v:.6f}" for v in floats)
        raise ParameterError("view-box string must have exactly 4 numbers.")
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            floats = [float(v) for v in value]
        except (TypeError, ValueError) as exc:
            raise ParameterError("view-box must be [minx, maxy, maxx, miny] numbers.") from exc
        return " ".join(f"{v:.6f}" for v in floats)
    raise ParameterError(
        "view-box must be a string 'minx maxy maxx miny' or [minx, maxy, maxx, miny]."
    )


def _format_bgcolor(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("#"):
            from .params import parse_color_text

            r, g, b, a = parse_color_text(text)
            return f"{r:.6f} {g:.6f} {b:.6f} {a:.6f}"
        parts = text.split()
        if len(parts) == 4:
            try:
                return " ".join(f"{float(p):.6f}" for p in parts)
            except ValueError as exc:
                raise ParameterError("bgcolor string must be 'r g b a' or '#rrggbb[aa]'.") from exc
        raise ParameterError("bgcolor string must be 'r g b a' or '#rrggbb[aa]'.")
    if isinstance(value, (list, tuple)) and len(value) in (3, 4):
        try:
            channels = [float(v) for v in value]
        except (TypeError, ValueError) as exc:
            raise ParameterError("bgcolor must be [r, g, b, (a)] floats.") from exc
        if len(channels) == 3:
            channels.append(1.0)
        return " ".join(f"{v:.6f}" for v in channels)
    from .params import encode_color

    encoded = encode_color(value)
    channels = [float((encoded.find(name) or None).text or "0") for name in ("r", "g", "b", "a")]  # type: ignore[union-attr]
    return " ".join(f"{v:.6f}" for v in channels)


def _parse_bgcolor(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    try:
        r, g, b, a = (float(v) for v in raw.split())
    except ValueError:
        return None
    return {"r": r, "g": g, "b": b, "a": a}
