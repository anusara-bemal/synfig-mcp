# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Layer operations on the canvas tree (order == paint order: 0 painted first)."""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import LayerNotFoundError
from .canvas import blend_method_name
from .params import decode_param, encode_param


def layer_index(root: etree._Element, layer: etree._Element) -> int:
    return [child for child in root if child.tag == "layer"].index(layer)


def list_layers(
    root: etree._Element, *, include_hidden_params: bool = False
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def describe(layer: etree._Element, depth: int, path: tuple[int, ...]) -> None:
        entry: dict[str, Any] = {
            "index": path[-1],
            "path": list(path),
            "depth": depth,
            "type": layer.get("type"),
            "name": _layer_name(layer),
            "desc": layer.get("desc"),
            "version": layer.get("version"),
            "active": (layer.get("active", "true") or "true").lower() != "false",
            "exclude_from_rendering": (
                layer.get("exclude_from_rendering", "false") or "false"
            ).lower()
            == "true",
            "amount": _find_real(layer, "amount"),
            "blend_method": _find_int(layer, "blend_method"),
            "blend_method_name": blend_method_name(_find_int(layer, "blend_method") or 0),
            "z_depth": _find_real(layer, "z_depth"),
            "hit_locked": (layer.get("hit_locked") or "false").lower() == "true",
            "group": layer.get("group"),
            "param_count": len(layer.findall("param")),
        }
        if include_hidden_params:
            entry["params"] = [decode_param(p) for p in layer.findall("param")]
        out.append(entry)
        for canvas in layer.findall("param/canvas"):
            for index, child in enumerate([c for c in canvas if c.tag == "layer"]):
                describe(child, depth + 1, (*path, index))

    for index, layer in enumerate([c for c in root if c.tag == "layer"]):
        describe(layer, 0, (index,))
    return out


def get_param(layer: etree._Element, name: str) -> etree._Element:
    for param in layer.findall("param"):
        if param.get("name") == name:
            return param
    raise LayerNotFoundError(
        name,
        suggestions=[p.get("name", "") for p in layer.findall("param")][:10],
    )


def get_param_or_none(layer: etree._Element, name: str) -> etree._Element | None:
    for param in layer.findall("param"):
        if param.get("name") == name:
            return param
    return None


def set_or_create_param(
    layer: etree._Element,
    name: str,
    value: Any,
    *,
    tag: str | None = None,
    reference: str | None = None,
    unit_px: float = 60.0,
    unit_system: str = "units",
    fps: float = 24.0,
) -> etree._Element:
    existing = get_param_or_none(layer, name)
    if existing is not None:
        new_tag = tag or (existing[0].tag if len(existing) else None)
        keep_attrs = dict(existing.attrib)
        layer.remove(existing)
        param = encode_param(
            name,
            value,
            tag=new_tag if isinstance(new_tag, str) else None,
            reference=reference,
            unit_px=unit_px,
            unit_system=unit_system,
            fps=fps,
        )
        # Preserve any attributes we do not manage (e.g. static, interpolation on values).
        for key, val in keep_attrs.items():
            if key not in ("name", "use"):
                param.set(key, val)
    else:
        param = encode_param(
            name,
            value,
            tag=tag,
            reference=reference,
            unit_px=unit_px,
            unit_system=unit_system,
            fps=fps,
        )
    layer.append(param)
    return param


def clone_layer(layer: etree._Element) -> etree._Element:
    import copy

    return copy.deepcopy(layer)


def remove_layer(root: etree._Element, layer: etree._Element) -> None:
    root.remove(layer)


def insert_layer(root: etree._Element, layer: etree._Element, index: int | None = None) -> int:
    layers = [child for child in root if child.tag == "layer"]
    if index is None:
        root.append(layer)
        return len(layers)
    if index < 0 or index > len(layers):
        raise LayerNotFoundError(index, suggestions=[f"index {i}" for i in range(len(layers) + 1)])
    if index == len(layers):
        root.append(layer)
        return index
    target = layers[index]
    target.addprevious(layer)
    return index


def move_layer(root: etree._Element, layer: etree._Element, new_index: int) -> int:
    layers = [child for child in root if child.tag == "layer"]
    if new_index < 0 or new_index >= len(layers):
        raise LayerNotFoundError(new_index)
    root.remove(layer)
    return insert_layer(root, layer, new_index)


def set_amount(layer: etree._Element, amount: float) -> None:
    amount = max(0.0, min(1.0, float(amount)))
    set_or_create_param(layer, "amount", amount, tag="real")


def set_blend_method(layer: etree._Element, blend: int) -> None:
    set_or_create_param(layer, "blend_method", int(blend), tag="integer")


def set_z_depth(layer: etree._Element, z_depth: float) -> None:
    set_or_create_param(layer, "z_depth", float(z_depth), tag="real")


def set_active(layer: etree._Element, active: bool) -> None:
    layer.set("active", "true" if active else "false")


def set_exclude_from_rendering(layer: etree._Element, exclude: bool) -> None:
    layer.set("exclude_from_rendering", "true" if exclude else "false")


def set_hit_locked(layer: etree._Element, hit_locked: bool) -> None:
    if hit_locked:
        layer.set("hit_locked", "true")
    elif layer.get("hit_locked") is not None:
        del layer.attrib["hit_locked"]


def layer_summary(layer: etree._Element) -> dict[str, Any]:
    return {
        "type": layer.get("type"),
        "name": _layer_name(layer),
        "desc": layer.get("desc"),
        "version": layer.get("version"),
        "active": (layer.get("active", "true") or "true").lower() != "false",
        "amount": _find_real(layer, "amount"),
        "blend_method": _find_int(layer, "blend_method"),
        "z_depth": _find_real(layer, "z_depth"),
        "exclude_from_rendering": (layer.get("exclude_from_rendering", "false") or "false").lower()
        == "true",
        "group": layer.get("group"),
    }


def _layer_name(layer: etree._Element) -> str:
    desc = layer.get("desc")
    if desc:
        return str(desc)
    for param in layer.findall("param"):
        if param.get("name") == "name" and len(param):
            text = (param[0].text or "").strip()
            if text:
                return text
    return str(layer.get("type") or "layer")


def _find_real(layer: etree._Element, name: str) -> float | None:
    for param in layer.findall("param"):
        if param.get("name") != name:
            continue
        if len(param):
            child = param[0]
            if child.tag == "real":
                try:
                    return float(child.get("value", "0") or 0)
                except ValueError:
                    return None
    return None


def _find_int(layer: etree._Element, name: str) -> int | None:
    for param in layer.findall("param"):
        if param.get("name") != name:
            continue
        if len(param):
            child = param[0]
            if child.tag == "integer":
                try:
                    return int(float(child.get("value", "0") or 0))
                except ValueError:
                    return None
    return None
