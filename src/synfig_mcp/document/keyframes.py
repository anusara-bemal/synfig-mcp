# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Keyframe management on the canvas root element."""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import KeyframeNotFoundError
from ..security.paths import sanitize_text
from .timeutil import format_time, parse_time


def list_keyframes(root: etree._Element, *, fps: float = 24.0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, kf in enumerate(root.findall("keyframe")):
        time_attr = kf.get("time", "0f") or "0f"
        out.append(
            {
                "index": index,
                "time": time_attr,
                "seconds": parse_time(time_attr, fps=fps),
                "active": (kf.get("active", "true") or "true").lower() != "false",
                "label": (kf.text or "").strip(),
            }
        )
    return out


def add_keyframe(
    root: etree._Element, time_text: str, label: str = "", *, fps: float = 24.0
) -> dict[str, Any]:
    seconds = parse_time(time_text, fps=fps)
    time_attr = format_time(seconds, fps=fps)
    for kf in root.findall("keyframe"):
        if parse_time(kf.get("time"), fps=fps) == seconds:
            kf.set("time", time_attr)
            kf.text = sanitize_text(label, max_length=256)
            kf.set("active", "true")
            return {"time": time_attr, "label": label, "updated": True}
    kf = etree.Element("keyframe", attrib={"time": time_attr, "active": "true"})
    kf.text = sanitize_text(label, max_length=256)
    _insert_keyframe(root, kf, fps=fps)
    return {"time": time_attr, "label": label, "updated": False}


def remove_keyframe(root: etree._Element, time_text: str, *, fps: float = 24.0) -> bool:
    seconds = parse_time(time_text, fps=fps)
    for kf in root.findall("keyframe"):
        if parse_time(kf.get("time"), fps=fps) == seconds:
            root.remove(kf)
            return True
    return False


def move_keyframe(root: etree._Element, from_time: str, to_time: str, *, fps: float = 24.0) -> dict[str, Any]:
    src = parse_time(from_time, fps=fps)
    dst = parse_time(to_time, fps=fps)
    target = None
    for kf in root.findall("keyframe"):
        if parse_time(kf.get("time"), fps=fps) == src:
            target = kf
            break
    if target is None:
        raise KeyframeNotFoundError(f"No keyframe at {from_time!r}.")
    target.set("time", format_time(dst, fps=fps))
    _reorder(root, fps=fps)
    return {
        "from": format_time(src, fps=fps),
        "to": format_time(dst, fps=fps),
        "label": (target.text or "").strip(),
    }


def set_keyframe_active(
    root: etree._Element, time_text: str, active: bool, *, fps: float = 24.0
) -> dict[str, Any]:
    seconds = parse_time(time_text, fps=fps)
    for kf in root.findall("keyframe"):
        if parse_time(kf.get("time"), fps=fps) == seconds:
            kf.set("active", "true" if active else "false")
            return {"time": kf.get("time"), "active": active}
    raise KeyframeNotFoundError(f"No keyframe at {time_text!r}.")


def _insert_keyframe(root: etree._Element, kf: etree._Element, *, fps: float) -> None:
    keyframes = root.findall("keyframe")
    seconds = parse_time(kf.get("time"), fps=fps)
    for existing in keyframes:
        if parse_time(existing.get("time"), fps=fps) > seconds:
            existing.addprevious(kf)
            return
    # Insert before bones/defs/layers if present, else append.
    anchor = None
    for child in root:
        if child.tag in {"bones", "defs", "layer"}:
            anchor = child
            break
    if anchor is not None:
        anchor.addprevious(kf)
    else:
        root.append(kf)


def _reorder(root: etree._Element, *, fps: float) -> None:
    keyframes = root.findall("keyframe")
    keyframes.sort(key=lambda kf: parse_time(kf.get("time"), fps=fps))
    for kf in keyframes:
        root.remove(kf)
    anchor = None
    for child in root:
        if child.tag in {"bones", "defs", "layer"}:
            anchor = child
            break
    for kf in keyframes:
        if anchor is not None:
            anchor.addprevious(kf)
        else:
            root.append(kf)
