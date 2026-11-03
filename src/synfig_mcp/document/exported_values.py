# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Exported values: defs entries with ``id`` referenced via ``use=":id"``."""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import ExportError
from .model import ProjectSession


def find_defs_entry(root: etree._Element, export_name: str) -> etree._Element | None:
    defs = root.find("defs")
    if defs is None:
        return None
    target = export_name.lstrip(":")
    for child in defs:
        if isinstance(child.tag, str) and child.get("id") == target:
            return child
    return None


def defs_ids(root: etree._Element) -> set[str]:
    defs = root.find("defs")
    ids: set[str] = set()
    if defs is None:
        return ids
    for child in defs:
        if isinstance(child.tag, str) and child.get("id"):
            ids.add(child.get("id", ""))
    return ids


def list_exported(root: etree._Element) -> list[dict[str, Any]]:
    defs = root.find("defs")
    if defs is None:
        return []
    out: list[dict[str, Any]] = []
    for child in defs:
        if not isinstance(child.tag, str) or not child.get("id"):
            continue
        out.append(
            {
                "id": child.get("id"),
                "tag": child.tag,
                "use": f":{child.get('id')}",
            }
        )
    return out


def _unique_name(root: etree._Element, base: str) -> str:
    taken = defs_ids(root)
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def export_value(
    session: ProjectSession, param_ref: str | int, param_name: str, export_name: str
) -> dict[str, Any]:
    """Move a param's value into defs and reference it with ``use=":export_name"``."""
    session.record_history()
    root = session.root
    index, layer = session.resolve_layer(param_ref)
    target = _find_param(layer, param_name)
    if target is None:
        raise ExportError(
            f"Parameter {param_name!r} not found on layer {index} ({layer.get('type')}).",
            hint=f"Available params: {', '.join(p.get('name', '') for p in layer.findall('param'))}",
        )
    if target.get("use") and target.get("use", "").startswith(":"):
        raise ExportError(
            f"Parameter {param_name!r} is already exported as {target.get('use')}.",
            hint="Use it as-is, or unlink_params first to inline a copy.",
        )
    if target.get("use"):
        raise ExportError(
            f"Parameter {param_name!r} references defs entry {target.get('use')!r}.",
            hint="Unlink it first if you want an independent exported copy.",
        )
    if len(target) == 0:
        raise ExportError(f"Parameter {param_name!r} has no value to export.")

    clean_name = export_name.strip()
    if not clean_name or any(ch in clean_name for ch in " :#@$^&()*\t\n\r"):
        raise ExportError(
            f"Invalid export name {export_name!r}.",
            hint="Use letters, digits, '-' and '_' only (Studio rules for canvas IDs).",
        )
    if clean_name in defs_ids(root):
        raise ExportError(
            f"An exported value named {clean_name!r} already exists.",
            hint="Choose another name or delete the existing defs entry.",
        )

    defs = session.defs(create=True)
    assert defs is not None
    payload = target[0]  # single child holds the value
    target.remove(payload)
    payload.set("id", clean_name)
    defs.append(payload)
    target.set("use", f":{clean_name}")
    session.touch()
    return {
        "layer_index": index,
        "param": param_name,
        "export_name": clean_name,
        "use": f":{clean_name}",
        "type": payload.tag if isinstance(payload.tag, str) else "unknown",
    }


def link_params(
    session: ProjectSession,
    src_layer: str | int,
    src_param: str,
    dst_layer: str | int,
    dst_param: str,
    *,
    export_name: str | None = None,
) -> dict[str, Any]:
    """Point dst_param at src_param's value (auto-exporting under a unique name)."""
    session.record_history()
    root = session.root
    src_index, src = session.resolve_layer(src_layer)
    src_el = _find_param(src, src_param)
    if src_el is None:
        raise ExportError(f"Source parameter {src_param!r} not found on layer {src_index}.")
    # Ensure the source is exported.
    if src_el.get("use", "").startswith(":"):
        export_name = src_el.get("use")[1:]
    elif src_el.get("use"):
        export_name = src_el.get("use")
    else:
        if len(src_el) == 0:
            raise ExportError(f"Source parameter {src_param!r} has no value.")
        base = export_name or f"{src_param}_{src_index}"
        export_name = _unique_name(root, base)
        defs = session.defs(create=True)
        assert defs is not None
        payload = src_el[0]
        src_el.remove(payload)
        payload.set("id", export_name)
        defs.append(payload)
        src_el.set("use", f":{export_name}")

    dst_index, dst = session.resolve_layer(dst_layer)
    dst_el = _find_param(dst, dst_param)
    if dst_el is None:
        raise ExportError(
            f"Destination parameter {dst_param!r} not found on layer {dst_index}.",
            hint=f"Available params: {', '.join(p.get('name', '') for p in dst.findall('param'))}",
        )
    for child in list(dst_el):
        dst_el.remove(child)
    if "use" in dst_el.attrib:
        del dst_el.attrib["use"]
    dst_el.set("use", export_name)
    session.touch()
    return {
        "src": {"layer": src_index, "param": src_param},
        "dst": {"layer": dst_index, "param": dst_param},
        "reference": dst_el.get("use"),
    }


def unlink_params(session: ProjectSession, layer_ref: str | int, param_name: str) -> dict[str, Any]:
    """Inline a copy of the referenced value at the param (leaves defs untouched)."""
    session.record_history()
    root = session.root
    index, layer = session.resolve_layer(layer_ref)
    target = _find_param(layer, param_name)
    if target is None:
        raise ExportError(f"Parameter {param_name!r} not found on layer {index}.")
    use = target.get("use")
    if not use:
        raise ExportError(f"Parameter {param_name!r} is not a reference (no use attribute).")
    entry = find_defs_entry(root, use.lstrip(":"))
    if entry is None:
        raise ExportError(
            f"Referenced defs entry {use!r} not found.",
            hint="The file may be corrupt or reference an external document.",
        )
    import copy

    for child in list(target):
        target.remove(child)
    inlined = copy.deepcopy(entry)
    if "id" in inlined.attrib:
        del inlined.attrib["id"]
    target.append(inlined)
    del target.attrib["use"]
    session.touch()
    return {"layer_index": index, "param": param_name, "unlinked_from": use, "type": inlined.tag}


def _find_param(layer: etree._Element, name: str) -> etree._Element | None:
    for param in layer.findall("param"):
        if param.get("name") == name:
            return param
    return None
