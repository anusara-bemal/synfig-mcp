# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Gradient defs and layer gradient params."""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import ParameterError
from .guids import new_guid
from .model import ProjectSession
from .params import decode_gradient, encode_gradient

GRADIENT_TYPES = {
    "linear_gradient",
    "radial_gradient",
    "conical_gradient",
    "curve_gradient",
    "spiral_gradient",
    "noise",
    "noise_distort",
    "gradient_rotate",
    "twotone",
}


def list_gradients(root: etree._Element) -> list[dict[str, Any]]:
    defs = root.find("defs")
    out: list[dict[str, Any]] = []
    if defs is None:
        return out
    for child in defs:
        if not isinstance(child.tag, str):
            continue
        if child.tag == "gradient" and child.get("id"):
            out.append(
                {
                    "id": child.get("id"),
                    "kind": "gradient",
                    "stops": decode_gradient(child),
                }
            )
        elif child.tag in {"stripes", "twotone"} and child.get("id"):
            out.append({"id": child.get("id"), "kind": child.tag, "stops": []})
    return out


def create_gradient_def(
    session: ProjectSession,
    gradient_id: str,
    stops: list[dict[str, Any]],
) -> dict[str, Any]:
    return upsert_gradient(session, gradient_id, stops, replace=False)


def upsert_gradient(
    session: ProjectSession,
    gradient_id: str,
    stops: list[dict[str, Any]],
    *,
    replace: bool,
) -> dict[str, Any]:
    session.record_history()
    clean = gradient_id.strip()
    if not clean or any(ch in clean for ch in " :#@$^&()*\t\n\r"):
        raise ParameterError(f"Invalid gradient id {gradient_id!r}.")
    defs = session.defs(create=True)
    assert defs is not None
    existing = _find_def(defs, clean)
    if existing is not None and not replace:
        raise ParameterError(
            f"Gradient {clean!r} already exists.",
            hint="Pass replace=true to overwrite it.",
        )
    new_element = encode_gradient(stops)
    new_element.set("id", clean)
    if existing is not None:
        existing.getparent().replace(existing, new_element)
    else:
        defs.append(new_element)
    session.touch()
    return {
        "id": clean,
        "kind": "gradient",
        "stops": decode_gradient(new_element),
        "replaced": existing is not None,
    }


def delete_gradient_def(session: ProjectSession, gradient_id: str) -> bool:
    session.record_history()
    root = session.root
    defs = root.find("defs")
    if defs is None:
        return False
    existing = _find_def(defs, gradient_id.strip())
    if existing is None:
        return False
    defs.remove(existing)
    session.touch()
    return True


def _find_def(defs: etree._Element, gradient_id: str) -> etree._Element | None:
    for child in defs:
        if (
            isinstance(child.tag, str)
            and child.tag == "gradient"
            and child.get("id") == gradient_id
        ):
            return child
    return None


def assign_gradient(session: ProjectSession, layer_index: int, gradient_id: str) -> dict[str, Any]:
    """Set a layer's `gradient` param to reference an existing gradient def."""
    from .layers import set_or_create_param

    session.record_history()
    _, layer = session.resolve_layer(layer_index)
    defs = session.root.find("defs")
    if defs is None or _find_def(defs, gradient_id) is None:
        raise ParameterError(f"No gradient defs entry named {gradient_id!r}.")
    set_or_create_param(layer, "gradient", None, reference=gradient_id)
    session.touch()
    return {"layer_index": layer_index, "gradient": gradient_id}


def new_inline_gradient(stops: list[dict[str, Any]]) -> etree._Element:
    element = encode_gradient(stops)
    element.set("guid", new_guid())
    return element
