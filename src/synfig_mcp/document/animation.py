# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Waypoint management: create/replace/remove waypoints and interpolate."""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import ParameterError, WaypointError
from .io import serialize
from .params import encode_value, qn
from .timeutil import format_time, parse_time

# File-format interpolation keywords mapped from friendly names.
INTERPOLATIONS = {
    "constant": "constant",
    "linear": "linear",
    "clamped": "clamped",
    "tcb": "auto",
    "auto": "auto",
    "ease": "auto",
    "halt": "halt",
    "manual": "manual",
}
# The two single-step behaviours synfig applies between waypoints.
EASE_TCB_TENSION = -0.5


def interpolation_keyword(name: str) -> str:
    key = name.strip().lower().replace("-", "_")
    if key not in INTERPOLATIONS:
        valid = ", ".join(sorted(INTERPOLATIONS))
        raise ParameterError(f"Unknown interpolation {name!r}. Use one of: {valid}.")
    return INTERPOLATIONS[key]


def get_animated(param: etree._Element) -> etree._Element | None:
    for child in param:
        if child.tag == "animated":
            return child
    return None


def ensure_animated(param: etree._Element, type_name: str | None = None) -> etree._Element:
    existing = get_animated(param)
    if existing is not None:
        return existing
    if len(param) == 0:
        raise WaypointError(
            f"Parameter {param.get('name')!r} is a reference (use=...); convert it first."
        )
    child = param[0]
    inferred = type_name or child.tag
    if inferred not in {
        "real",
        "integer",
        "angle",
        "time",
        "bool",
        "string",
        "color",
        "vector",
        "gradient",
    }:
        raise WaypointError(f"Cannot animate parameter {param.get('name')!r} of type {inferred!r}.")
    waypoints_parent = etree.Element(qn("animated"), attrib={"type": inferred})
    # Keep the current constant as a waypoint at t=0.
    waypoint = etree.SubElement(waypoints_parent, qn("waypoint"), attrib={"time": "0f"})
    waypoint.append(child)  # re-parents child into the waypoint (removes it from param)
    param.append(waypoints_parent)
    return waypoints_parent


def waypoints(animated: etree._Element) -> list[etree._Element]:
    return [child for child in animated if child.tag == "waypoint"]


def find_waypoint(animated: etree._Element, time_text: str, *, fps: float) -> etree._Element | None:
    target = parse_time(time_text, fps=fps)
    for wp in waypoints(animated):
        try:
            if parse_time(wp.get("time"), fps=fps) == target:
                return wp
        except ParameterError:
            continue
    return None


def set_waypoint(
    param: etree._Element,
    time_text: str,
    value: Any,
    *,
    interpolation: str | None = None,
    fps: float = 24.0,
    unit_px: float = 60.0,
    unit_system: str = "units",
) -> etree._Element:
    keyword = interpolation_keyword(interpolation) if interpolation else None
    animated = ensure_animated(param)
    type_name = animated.get("type") or "real"
    seconds = parse_time(time_text, fps=fps)
    time_attr = format_time(seconds, fps=fps)
    existing = find_waypoint(animated, time_attr, fps=fps)
    payload = encode_value(
        value,
        expected=type_name,
        unit_px=unit_px,
        unit_system=unit_system,
        fps=fps,
    )
    if existing is not None:
        for child in list(existing):
            if child.tag not in {"value_node"}:
                existing.remove(child)
        existing.append(payload)
        wp = existing
    else:
        wp = etree.Element(qn("waypoint"), attrib={"time": time_attr})
        wp.append(payload)
        insert_index = len(list(animated))
        for index, child in enumerate(animated):
            if child.tag != "waypoint":
                continue
            try:
                other = parse_time(child.get("time"), fps=fps)
            except ParameterError:
                continue
            if other > seconds:
                insert_index = index
                break
        animated.insert(insert_index, wp)
    if keyword:
        wp.set("before", keyword)
        wp.set("after", keyword)
    return wp


def remove_waypoint(param: etree._Element, time_text: str, *, fps: float) -> bool:
    animated = get_animated(param)
    if animated is None:
        return False
    wp = find_waypoint(animated, time_text, fps=fps)
    if wp is None:
        return False
    animated.remove(wp)
    return True


def set_interpolation(
    param: etree._Element,
    interpolation: str,
    *,
    time_text: str | None = None,
    fps: float = 24.0,
) -> int:
    keyword = interpolation_keyword(interpolation)
    animated = get_animated(param)
    if animated is None:
        raise WaypointError(f"Parameter {param.get('name')!r} is not animated.")
    count = 0
    targets = waypoints(animated)
    if time_text is not None:
        seconds = parse_time(time_text, fps=fps)
        targets = [wp for wp in targets if parse_time(wp.get("time"), fps=fps) == seconds]
        if not targets:
            raise WaypointError(f"No waypoint at {time_text!r}.")
    is_ease = interpolation.strip().lower() == "ease"
    for wp in targets:
        wp.set("before", keyword)
        wp.set("after", keyword)
        if keyword == "auto" and is_ease:
            wp.set("tension", f"{EASE_TCB_TENSION:.6f}")
        count += 1
    return count


def animate_param(
    param: etree._Element,
    waypoints_spec: list[dict[str, Any]],
    *,
    interpolation: str | None = None,
    fps: float = 24.0,
    unit_px: float = 60.0,
    unit_system: str = "units",
) -> int:
    if not waypoints_spec:
        raise ParameterError("waypoints must be a non-empty list of {time, value}.")
    keyword = interpolation_keyword(interpolation) if interpolation else None
    animated = ensure_animated(param)
    type_name = animated.get("type") or "real"
    for item in waypoints_spec:
        if not isinstance(item, dict) or "time" not in item or "value" not in item:
            raise ParameterError("Each waypoint needs 'time' and 'value'.")
        seconds = parse_time(item["time"], fps=fps)
        time_attr = format_time(seconds, fps=fps)
        existing = find_waypoint(animated, time_attr, fps=fps)
        payload = encode_value(
            item["value"],
            expected=type_name,
            unit_px=unit_px,
            unit_system=unit_system,
            fps=fps,
        )
        if existing is not None:
            for child in list(existing):
                existing.remove(child)
            existing.append(payload)
            wp = existing
        else:
            wp = etree.SubElement(animated, qn("waypoint"), attrib={"time": time_attr})
            wp.append(payload)
        item_before = item.get("before") or item.get("interpolation") or keyword
        if item_before:
            wp.set("before", interpolation_keyword(str(item_before)))
        item_after = item.get("after") or item.get("interpolation") or keyword
        if item_after:
            wp.set("after", interpolation_keyword(str(item_after)))
    # Keep waypoints ordered by time.
    ordered = sorted(
        waypoints(animated),
        key=lambda wp: parse_time(wp.get("time"), fps=fps) if wp.get("time") else 0.0,
    )
    for wp in list(animated):
        if wp.tag == "waypoint":
            animated.remove(wp)
    for wp in ordered:
        animated.append(wp)
    return len(waypoints_spec)


def export_animated_xml(param: etree._Element) -> str:
    return serialize(etree.ElementTree(param)).decode("utf-8", errors="replace")


__all__ = [
    "INTERPOLATIONS",
    "animate_param",
    "ensure_animated",
    "find_waypoint",
    "get_animated",
    "interpolation_keyword",
    "remove_waypoint",
    "set_interpolation",
    "set_waypoint",
    "waypoints",
]
