# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Skeleton bones: create, list, edit and bind, using the verified .sif format.

The bones live in the canvas ``<bones>`` section (parsed before ``<defs>``):

* ``<bone_root type="bone_object" guid="X"/>`` marks the implicit root bone
* bone entries carry full children and ``guid``/``id`` attributes
* references use ``<bone_valuenode type="bone_object" guid="X"/>``

Synfig 1.5.x cannot round-trip a skeleton layer's ``<bones>`` *parameter*
(it serialises as ``<nil/>``), so bones created here are stored as proper
value nodes; Studio reads and re-saves them correctly.
"""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import ExportError, ParameterError
from .guids import is_guid, new_guid
from .layers import get_param_or_none
from .model import ProjectSession
from .params import decode_vector, encode_vector


def bones_section(root: etree._Element, *, create: bool = False) -> etree._Element | None:
    section = root.find("bones")
    if section is None and create:
        section = etree.Element("bones")
        anchor = None
        for child in root:
            if child.tag in {"defs", "layer"}:
                anchor = child
                break
        if anchor is not None:
            anchor.addprevious(section)
        else:
            root.append(section)
    return section


def ensure_root_bone(root: etree._Element) -> str:
    """Return the guid of the (single) bone_root, creating it if needed."""
    section = bones_section(root, create=True)
    assert section is not None
    existing = section.find("bone_root")
    if existing is not None:
        guid = existing.get("guid") or new_guid()
        existing.set("type", "bone_object")
        existing.set("guid", guid)
        return guid
    root_bone = etree.Element("bone_root", attrib={"type": "bone_object", "guid": new_guid()})
    section.insert(0, root_bone)
    return root_bone.get("guid") or ""


def list_bones(root: etree._Element) -> list[dict[str, Any]]:
    section = root.find("bones")
    if section is None:
        return []
    out: list[dict[str, Any]] = []
    for child in section:
        if child.tag != "bone":
            continue
        out.append(_bone_info(child))
    return out


def _bone_info(bone: etree._Element) -> dict[str, Any]:
    name_el = bone.find("name/string")
    origin_el = bone.find("origin/vector")
    angle_el = bone.find("angle/angle")
    scalelx_el = bone.find("scalelx/real")
    scalex_el = bone.find("scalex/real")
    width_el = bone.find("width/real")
    tipwidth_el = bone.find("tipwidth/real")
    depth_el = bone.find("bone_depth/real")
    length_el = bone.find("length/real")
    parent_el = bone.find("parent/bone_valuenode")
    return {
        "id": bone.get("id"),
        "guid": bone.get("guid"),
        "name": (name_el.text or "").strip() if name_el is not None else None,
        "parent_guid": parent_el.get("guid") if parent_el is not None else None,
        "origin": decode_vector(origin_el) if origin_el is not None else None,
        "angle": _float(angle_el.get("value")) if angle_el is not None else 0.0,
        "scalelx": _float(scalelx_el.get("value")) if scalelx_el is not None else 1.0,
        "scalex": _float(scalex_el.get("value")) if scalex_el is not None else 1.0,
        "width": _float(width_el.get("value")) if width_el is not None else 0.3,
        "tipwidth": _float(tipwidth_el.get("value")) if tipwidth_el is not None else 0.3,
        "bone_depth": _float(depth_el.get("value")) if depth_el is not None else 0.0,
        "length": _float(length_el.get("value")) if length_el is not None else 1.0,
    }


def _float(text: str | None, default: float = 0.0) -> float:
    try:
        return float(text) if text is not None else default
    except ValueError:
        return default


def _find_bone(root: etree._Element, ref: str) -> etree._Element | None:
    section = root.find("bones")
    if section is None:
        return None
    lowered = ref.strip().lower()
    for bone in section.findall("bone"):
        if (bone.get("id") or "").lower() == lowered:
            return bone
        if (bone.get("guid") or "").lower() == lowered:
            return bone
        name_el = bone.find("name/string")
        if name_el is not None and (name_el.text or "").strip().lower() == lowered:
            return bone
    return None


def create_bone(
    session: ProjectSession,
    name: str,
    *,
    origin: tuple[float, float] | list[float] | dict[str, float] | None = None,
    angle: float = 0.0,
    length: float = 1.0,
    width: float = 0.3,
    tipwidth: float = 0.15,
    scalelx: float = 1.0,
    scalex: float = 1.0,
    bone_depth: float = 0.0,
    parent: str | None = None,
    export: bool = True,
) -> dict[str, Any]:
    session.record_history()
    root = session.root
    clean = (name or "").strip()
    if not clean or any(ch in clean for ch in " :#@$^&()*\t\n\r"):
        raise ParameterError(
            f"Invalid bone name {name!r}.",
            hint="Use letters, digits, '-' and '_' (Synfig ID rules).",
        )
    if _find_bone(root, clean) is not None:
        raise ParameterError(f"A bone named {clean!r} already exists.")
    root_guid = ensure_root_bone(root)
    section = bones_section(root, create=True)
    assert section is not None

    if parent:
        parent_bone = _find_bone(root, parent)
        if parent_bone is None:
            raise ParameterError(f"Parent bone {parent!r} not found.")
        parent_guid = parent_bone.get("guid") or ""
    else:
        parent_guid = root_guid

    origin_vec = origin if origin is not None else (0.0, 0.0)
    vector_el = encode_vector(origin_vec)
    guid = new_guid()
    bone = etree.Element("bone", attrib={"type": "bone_object", "guid": guid})
    if export:
        bone.set("id", clean)

    def sub(tag: str, payload: etree._Element | str) -> None:
        child = etree.SubElement(bone, tag)
        if isinstance(payload, str):
            child.text = payload
        else:
            child.append(payload)

    name_el = etree.Element("string")
    name_el.text = clean
    sub("name", name_el)
    parent_el = etree.SubElement(bone, "parent")
    etree.SubElement(
        parent_el,
        "bone_valuenode",
        attrib={"type": "bone_object", "guid": parent_guid},
    )
    sub("origin", vector_el)

    def scalar(tag: str, value: float) -> None:
        node = etree.SubElement(bone, tag)
        etree.SubElement(node, "real", attrib={"value": f"{value:.10f}"})

    def angle_scalar(value: float) -> None:
        node = etree.SubElement(bone, "angle")
        etree.SubElement(node, "angle", attrib={"value": f"{value:.6f}"})

    angle_scalar(angle)
    scalar("scalelx", scalelx)
    scalar("width", width)
    scalar("scalex", scalex)
    scalar("tipwidth", tipwidth)
    scalar("bone_depth", bone_depth)
    scalar("length", length)
    section.append(bone)
    session.touch()
    return {"name": clean, "guid": guid, "parent_guid": parent_guid, "export": export}


def set_bone_param(
    session: ProjectSession,
    ref: str,
    param: str,
    value: Any,
    *,
    unit_px: float = 60.0,
    unit_system: str = "units",
) -> dict[str, Any]:
    session.record_history()
    root = session.root
    bone = _find_bone(root, ref)
    if bone is None:
        raise ParameterError(
            f"Bone {ref!r} not found.",
            hint="Run list_bones to see available bones.",
        )
    key = param.strip().lower().replace("-", "_")
    if key == "name":
        clean = str(value).strip()
        if not clean or any(ch in clean for ch in " :#@$^&()*\t\n\r"):
            raise ParameterError(f"Invalid bone name {value!r}.")
        node = bone.find("name/string")
        assert node is not None
        node.text = clean
    elif key == "origin":
        node = bone.find("origin")
        if node is None:
            node = etree.SubElement(bone, "origin")
        for child in list(node):
            node.remove(child)
        node.append(encode_vector(value, unit_px=unit_px, unit_system=unit_system))
    elif key == "angle":
        node = bone.find("angle")
        if node is None:
            node = etree.SubElement(bone, "angle")
        angle_el = node.find("angle")
        if angle_el is None:
            angle_el = etree.SubElement(node, "angle")
        angle_el.set("value", f"{float(value):.6f}")
    elif key in {"scalelx", "scalex", "width", "tipwidth", "bone_depth", "length"}:
        node = bone.find(key)
        if node is None:
            node = etree.SubElement(bone, key)
        real_el = node.find("real")
        if real_el is None:
            real_el = etree.SubElement(node, "real")
        real_el.set("value", f"{float(value):.10f}")
    elif key == "parent":
        parent_bone = _find_bone(root, str(value))
        if parent_bone is None:
            raise ParameterError(f"Parent bone {value!r} not found.")
        node = bone.find("parent")
        if node is None:
            node = etree.SubElement(bone, "parent")
        for child in list(node):
            node.remove(child)
        etree.SubElement(
            node,
            "bone_valuenode",
            attrib={"type": "bone_object", "guid": parent_bone.get("guid") or ""},
        )
    else:
        raise ParameterError(
            f"Unknown bone parameter {param!r}.",
            hint="Use one of: name, origin, angle, scalelx, scalex, width, tipwidth, bone_depth, length, parent.",
        )
    session.touch()
    return {"bone": ref, "param": key, "value": value}


def bind_skeleton(
    session: ProjectSession,
    layer_ref: str | int,
    param_name: str,
    bone_refs: list[str],
    *,
    weights: list[float] | None = None,
) -> dict[str, Any]:
    """Convert a vector/bline_point param to <boneinfluence> with weight pairs."""
    if not bone_refs:
        raise ParameterError("bone_refs must name at least one bone.")
    session.record_history()
    root = session.root
    index, layer = session.resolve_layer(layer_ref)
    param = get_param_or_none(layer, param_name)
    if param is None:
        raise ExportError(f"Parameter {param_name!r} not found on layer {index}.")
    if len(param) == 0:
        if param.get("use"):
            raise ParameterError(f"Parameter {param_name!r} is a reference; unlink it first.")
        raise ParameterError(f"Parameter {param_name!r} has no value to bind.")
    current_type = param[0].tag
    if current_type not in {"vector", "bline_point"}:
        raise ParameterError(
            f"bind_skeleton supports vector or bline_point params, got {current_type!r}.",
            hint="For composite blines use Synfig Studio's bone tools, or bind the 'origin' vector instead.",
        )
    original = param[0]

    if weights is None:
        weights = [1.0 for _ in bone_refs]
    if len(weights) != len(bone_refs):
        raise ParameterError("weights must have the same length as bone_refs.")

    bone_weight_list = etree.Element("static_list", attrib={"type": "bone_weight_pair"})
    for bone_ref, weight in zip(bone_refs, weights, strict=True):
        bone = _find_bone(root, bone_ref)
        if bone is None:
            raise ParameterError(f"Bone {bone_ref!r} not found.")
        entry = etree.SubElement(bone_weight_list, "entry")
        pair = etree.SubElement(entry, "boneweightpair", attrib={"type": "bone_weight_pair"})
        bone_el = etree.SubElement(pair, "bone")
        etree.SubElement(
            bone_el,
            "bone_valuenode",
            attrib={"type": "bone_object", "guid": bone.get("guid") or ""},
        )
        weight_el = etree.SubElement(pair, "weight")
        etree.SubElement(weight_el, "real", attrib={"value": f"{float(weight):.10f}"})

    influence = etree.Element("boneinfluence", attrib={"type": current_type})
    link_el = etree.SubElement(influence, "link")
    param.remove(original)
    link_el.append(original)
    param.append(influence)
    # bone_weight_list must be the FIRST child of <boneinfluence>
    influence.insert(0, _wrap("bone_weight_list", bone_weight_list))
    session.touch()
    return {
        "layer_index": index,
        "param": param_name,
        "bones": [
            {"ref": ref, "weight": float(w)} for ref, w in zip(bone_refs, weights, strict=True)
        ],
        "type": current_type,
    }


def _wrap(tag: str, child: etree._Element) -> etree._Element:
    wrapper = etree.Element(tag)
    wrapper.append(child)
    return wrapper


__all__ = [
    "bind_skeleton",
    "bones_section",
    "create_bone",
    "ensure_root_bone",
    "is_guid",
    "list_bones",
    "set_bone_param",
]
