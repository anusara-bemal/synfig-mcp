# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Typed codec for Synfig parameter values.

Synfig stores every parameter value as typed XML children of ``<param>``:

* scalars: ``<real value=".."/>``, ``<integer value=".."/>``,
  ``<angle value=".."/>``, ``<time value=".."/>``, ``<bool value="true"/>``
* text: ``<string>...</string>``
* color: ``<color><r/><g/><b/><a/></color>``
* vector: ``<vector><x/><y/></vector>``
* bline: ``<bline loop="true"><entry>...</entry></bline>`` (or ``use="id"``)
* gradient: ``<gradient><color pos="..">...</color></gradient>`` (or ``use="id"``)
* canvas: ``<canvas use="id"/>`` or inline ``<canvas>...</canvas>``
* animated: ``<animated type="vector"><waypoint .../>...</animated>``
* linkable: e.g. ``<scale type="vector">...</scale>`` or ``use=":export"``

Friendly input accepted by tools:

* vector: ``[x, y]`` / ``{"x":..,"y":..}`` — units by default, pixels with
  ``SYNFIG_MCP_UNIT_SYSTEM=pixels`` (configurable px-per-unit)
* color: ``#rgb``, ``#rrggbb``, ``#rrggbbaa``, ``[r, g, b(, a)]`` floats 0..1,
  or ``{"r":..,"g":..,"b":..,"a":..}``
* angle: degrees (float)
* time: float seconds, or synfig strings (``"2s 12f"``, ``"30f"``)
* bool: real bool, "true"/"false", 0/1
* gradient: list of ``{"pos":0..1, "color": "#ff8800"}``
* bline: ``{"loop": true, "vertices": [[x, y], ...], "width":..,
  "origin":.., "t1": [[x, y], ...], "t2": [...]}`` or a compact list of points
"""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import ParameterError
from .guids import new_guid
from .timeutil import format_time, parse_time

# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

NS = None  # Synfig files use no namespaces.


def qn(tag: str) -> str:
    return tag


def make_element(tag: str, **attrs: object) -> etree._Element:
    el = etree.Element(qn(tag))
    for key, value in attrs.items():
        if value is not None:
            el.set(key, _stringify(value))
    return el


def _stringify(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.10f}".rstrip("0").rstrip(".") if value != int(value) else str(int(value))
    return str(value)


def _fmt(value: float, decimals: int = 10) -> str:
    text = f"{value:.{decimals}f}"
    # Synfig writes -0.0000000000 sometimes; normalise negative zero.
    if set(text.replace("-", "").replace(".", "")) == {"0"}:
        return "0." + "0" * decimals
    return text


def parse_color_text(text: str) -> tuple[float, float, float, float]:
    """Parse '#rgb', '#rrggbb', '#rrggbbaa' into linear 0..1 floats."""
    cleaned = text.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned) + "ff"
    elif len(cleaned) == 4:
        cleaned = "".join(c * 2 for c in cleaned)
    elif len(cleaned) == 6:
        cleaned += "ff"
    elif len(cleaned) != 8:
        raise ParameterError(
            f"Unsupported color literal: {text!r}. Use #rgb, #rrggbb or #rrggbbaa."
        )
    try:
        r, g, b, a = (int(cleaned[i : i + 2], 16) / 255.0 for i in (0, 2, 4, 6))
    except ValueError as exc:
        raise ParameterError(f"Unsupported color literal: {text!r}.") from exc
    return r, g, b, a


def format_color_hex(r: float, g: float, b: float, a: float) -> str:
    def hx(v: float) -> str:
        return f"{max(0, min(255, round(v * 255))):02X}"

    return f"#{hx(r)}{hx(g)}{hx(b)}{hx(a)}"


def encode_color(value: Any) -> etree._Element:
    if isinstance(value, str):
        r, g, b, a = parse_color_text(value)
    elif isinstance(value, dict):
        try:
            r = float(value.get("r", 0.0))
            g = float(value.get("g", 0.0))
            b = float(value.get("b", 0.0))
            a = float(value.get("a", 1.0))
        except (TypeError, ValueError) as exc:
            raise ParameterError("Color dict must have numeric r, g, b, (a).") from exc
    elif isinstance(value, (list, tuple)) and len(value) in (3, 4):
        try:
            r, g, b = (float(v) for v in value[:3])
            a = float(value[3]) if len(value) == 4 else 1.0
        except (TypeError, ValueError) as exc:
            raise ParameterError("Color sequence must be [r, g, b(, a)] floats 0..1.") from exc
    else:
        raise ParameterError(f"Unsupported color value: {value!r}.")
    r, g, b, a = (max(0.0, min(1.0, v)) for v in (r, g, b, a))
    color = make_element("color")
    for name, channel in (("r", r), ("g", g), ("b", b), ("a", a)):
        child = make_element(name)
        child.text = f"{channel:.6f}"
        color.append(child)
    return color


def decode_color(el: etree._Element) -> dict[str, Any]:
    channels: dict[str, float] = {}
    for name in ("r", "g", "b", "a"):
        child = el.find(name)
        try:
            channels[name] = float(child.text or "0")
        except (TypeError, ValueError, AttributeError):
            channels[name] = 0.0
    channels.setdefault("a", 1.0)
    out: dict[str, Any] = dict(channels)
    out["hex"] = format_color_hex(channels["r"], channels["g"], channels["b"], channels["a"])
    return out


def encode_vector(
    value: Any, *, unit_px: float = 60.0, unit_system: str = "units"
) -> etree._Element:
    if isinstance(value, dict):
        try:
            x = float(value.get("x", 0.0))
            y = float(value.get("y", 0.0))
        except (TypeError, ValueError) as exc:
            raise ParameterError("Vector dict must have numeric x and y.") from exc
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            x, y = (float(v) for v in value)
        except (TypeError, ValueError) as exc:
            raise ParameterError("Vector must be [x, y] numbers.") from exc
    else:
        raise ParameterError(
            f"Unsupported vector value: {value!r}. Use [x, y] or {{'x':..,'y':..}}."
        )
    if unit_system == "pixels":
        x /= unit_px
        y /= unit_px
    vector = make_element("vector")
    x_el, y_el = make_element("x"), make_element("y")
    x_el.text, y_el.text = _fmt(x), _fmt(y)
    vector.append(x_el)
    vector.append(y_el)
    return vector


def decode_vector(
    el: etree._Element, *, unit_px: float = 60.0, unit_system: str = "units"
) -> dict[str, float]:
    x = _child_float(el, "x") or 0.0
    y = _child_float(el, "y") or 0.0
    out = {"x": x, "y": y}
    if unit_system == "pixels":
        out = {"x": x * unit_px, "y": y * unit_px}
    return out


def _child_float(el: etree._Element, name: str) -> float | None:
    child = el.find(name)
    if child is None or not (child.text or "").strip():
        return None
    try:
        return float(child.text or "0")
    except ValueError:
        return None


def encode_gradient(stops: Any) -> etree._Element:
    if not isinstance(stops, (list, tuple)) or not stops:
        raise ParameterError(
            "Gradient must be a non-empty list of {'pos': 0..1, 'color': '#rrggbb'}."
        )
    gradient = make_element("gradient")
    for stop in stops:
        if not isinstance(stop, dict) or "pos" not in stop or "color" not in stop:
            raise ParameterError("Each gradient stop needs 'pos' (0..1) and 'color'.")
        try:
            pos = float(stop["pos"])
        except (TypeError, ValueError) as exc:
            raise ParameterError("Gradient stop 'pos' must be a number 0..1.") from exc
        pos = max(0.0, min(1.0, pos))
        child = encode_color(stop["color"])
        child.tag = "color"
        child.set("pos", f"{pos:.6f}")
        gradient.append(child)
    return gradient


def decode_gradient(el: etree._Element) -> list[dict[str, Any]]:
    stops: list[dict[str, Any]] = []
    for child in el.iter("color"):
        if child.getparent() is el or child.getparent() is None:
            pos_attr = child.get("pos")
            try:
                pos = float(pos_attr) if pos_attr is not None else 0.0
            except ValueError:
                pos = 0.0
            stops.append({"pos": pos, **decode_color(child)})
    return stops


# ---------------------------------------------------------------------------
# Value (encode/decode)
# ---------------------------------------------------------------------------

SCALAR_TAGS = {"real", "integer", "angle", "time", "bool", "string"}


def encode_value(
    value: Any,
    *,
    expected: str | None = None,
    unit_px: float = 60.0,
    unit_system: str = "units",
    fps: float = 24.0,
) -> etree._Element:
    """Encode a friendly python value into a synfig value element."""
    tag = expected or _infer_scalar_tag(value)
    if tag == "real":
        return _scalar("real", _as_float(value))
    if tag == "integer":
        if isinstance(value, bool):
            value = int(value)
        return _scalar("integer", int(_as_float(value)))
    if tag == "angle":
        return _scalar("angle", _as_float(value))
    if tag == "time":
        seconds = parse_time(value, fps=fps)
        return _scalar("time", format_time(seconds, fps=fps))
    if tag == "bool":
        return _scalar("bool", _as_bool(value))
    if tag == "string":
        text = "" if value is None else str(value)
        el = make_element("string")
        el.text = text
        return el
    if tag == "color":
        return encode_color(value)
    if tag == "vector":
        return encode_vector(value, unit_px=unit_px, unit_system=unit_system)
    if tag == "gradient":
        return encode_gradient(value)
    if tag == "bline":
        return encode_bline(value)
    if tag in {"canvas", "bone_valuenode"}:
        # References are written with use="..." on the param/entry element;
        # callers handle those paths explicitly.
        raise ParameterError(f"{tag} values must be passed as references (use=...), not inline.")
    raise ParameterError(f"Unsupported value type for parameter: {tag!r}.")


def _infer_scalar_tag(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "real"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            return "vector"
        if len(value) in (3, 4) and all(isinstance(v, (int, float)) for v in value):
            return "color"
        if value and all(isinstance(v, dict) for v in value):
            # Gradient stops carry "pos"/"color"; bline vertices carry
            # x/y or point/t1/t2/width.
            if any("pos" in v or "color" in v for v in value):
                return "gradient"
            return "bline"
        return "gradient"
    if isinstance(value, dict):
        if "r" in value or "hex" in value:
            return "color"
        if "x" in value and "y" in value:
            return "vector"
        return "bline"
    return "string"


def decode_value(
    el: etree._Element, *, unit_px: float = 60.0, unit_system: str = "units", fps: float = 24.0
) -> dict[str, Any]:
    """Decode a synfig value element into {'type': ..., 'value': ...}."""
    tag = el.tag
    if tag == "real":
        return {"type": "real", "value": _attr_float(el, "value", 0.0)}
    if tag == "integer":
        return {"type": "integer", "value": int(_attr_float(el, "value", 0.0))}
    if tag == "angle":
        return {"type": "angle", "value": _attr_float(el, "value", 0.0), "unit": "degrees"}
    if tag == "time":
        raw = el.get("value", "0f") or "0f"
        return {"type": "time", "value": raw, "seconds": parse_time(raw, fps=fps)}
    if tag == "bool":
        return {
            "type": "bool",
            "value": (el.get("value", "false") or "false").lower() in {"true", "1"},
        }
    if tag == "string":
        return {"type": "string", "value": el.text or ""}
    if tag == "color":
        return {"type": "color", "value": decode_color(el)}
    if tag == "vector":
        return {
            "type": "vector",
            "value": decode_vector(el, unit_px=unit_px, unit_system=unit_system),
        }
    if tag == "gradient":
        return {"type": "gradient", "value": decode_gradient(el)}
    if tag == "bline":
        return {"type": "bline", "value": decode_bline(el)}
    if tag == "canvas":
        return {"type": "canvas", "value": {"reference": el.get("use")}}
    if tag == "composite":
        return {"type": "composite", "value": _decode_composite(el), "composite": el.get("type")}
    if tag == "animated":
        return {"type": "animated", "value": decode_animated(el), "animated_type": el.get("type")}
    if tag == "static_list":
        return {"type": "static_list", "value": decode_list(el), "list_type": el.get("type")}
    if tag == "dynamic_list":
        return {
            "type": "dynamic_list",
            "value": decode_list(el),
            "list_type": el.get("type"),
            "loop": el.get("loop") == "true",
        }
    if tag == "wplist":
        return {"type": "wplist", "value": decode_list(el), "loop": el.get("loop") == "true"}
    if tag == "dilist":
        return {"type": "dilist", "value": decode_list(el), "loop": el.get("loop") == "true"}
    if tag == "list":
        return {"type": "list", "value": decode_list(el)}
    if tag == "transformation":
        return {"type": "transformation", "value": _decode_transformation(el)}
    if tag == "width_point":
        return {"type": "width_point", "value": _decode_width_point(el)}
    if tag == "guid":
        return {"type": "guid", "value": el.get("value", "")}
    if tag == "keyframe":  # not a value, defensive
        return {"type": "keyframe", "value": el.text or ""}
    if tag in {"bone", "bone_root", "bone_valuenode", "bone_link", "bone_weight_pair"}:
        return {"type": tag, "value": _shallow_dict(el)}
    if tag == "boneinfluence":
        return {
            "type": "boneinfluence",
            "value": decode_animated(el) if False else _shallow_dict(el),
        }
    return {"type": tag, "value": _shallow_dict(el)}


def _attr_float(el: etree._Element, name: str, default: float) -> float:
    try:
        return float(el.get(name, default))
    except (TypeError, ValueError):
        return default


def _shallow_dict(el: etree._Element) -> dict[str, Any]:
    """Best-effort dict of a value element for opaque/complex types."""
    out: dict[str, Any] = {"tag": el.tag, "attributes": dict(el.attrib)}
    children = []
    for child in el:
        if isinstance(child.tag, str):
            children.append(
                {
                    "tag": child.tag,
                    "attributes": dict(child.attrib),
                    "text": (child.text or "").strip() or None,
                }
            )
    if children:
        out["children"] = children
    elif el.text and el.text.strip():
        out["text"] = el.text.strip()
    return out


def _decode_composite(el: etree._Element) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for child in el:
        if isinstance(child.tag, str):
            out[child.tag] = decode_value(child)
    return out


def _decode_transformation(el: etree._Element) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("offset", "angle", "skew_angle", "scale"):
        child = el.find(key)
        if child is not None:
            first = child[0] if len(child) else None
            if first is not None:
                out[key] = decode_value(first)["value"]
    return out


def _decode_width_point(el: etree._Element) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for child in el:
        if isinstance(child.tag, str):
            grand = child[0] if len(child) else None
            if grand is not None:
                try:
                    out[child.tag] = float(grand.text or "0")
                except ValueError:
                    out[child.tag] = None
    return out


def decode_animated(el: etree._Element) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": el.get("type"),
        "interpolation": el.get("interpolation"),
        "waypoints": [],
    }
    for child in el.findall("waypoint"):
        wp: dict[str, Any] = {
            "time": child.get("time"),
            "before": child.get("before"),
            "after": child.get("after"),
        }
        for attr in ("tension", "temporal-tension", "continuity", "bias"):
            if child.get(attr) is not None:
                wp[attr] = _attr_float(child, attr, 0.0)
        payload = child.find("value_node")
        if payload is not None and len(payload):
            wp["value"] = decode_value(payload[0])
        elif child.get("use"):
            wp["use"] = child.get("use")
        else:
            # Synfig writes waypoint values as direct typed children
            # (e.g. <real value=".."/>), without a value_node wrapper.
            for value_el in child:
                if isinstance(value_el.tag, str) and value_el.tag != "value_node":
                    wp["value"] = decode_value(value_el)
                    break
        out["waypoints"].append(wp)
    return out


def decode_list(el: etree._Element) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in el.findall("entry"):
        item: dict[str, Any] = {}
        if entry.get("use"):
            item["use"] = entry.get("use")
        for attr in ("on", "off"):
            if entry.get(attr):
                item[attr] = entry.get(attr)
        payload = entry.find("value_node")
        if payload is not None and len(payload):
            item["value"] = decode_value(payload[0])
        else:
            for child in entry:
                if isinstance(child.tag, str) and child.tag != "value_node":
                    item["value"] = decode_value(child)
                    break
        entries.append(item)
    return entries


# ---------------------------------------------------------------------------
# BLine encode/decode
# ---------------------------------------------------------------------------


def encode_bline(
    value: Any, *, unit_px: float = 60.0, unit_system: str = "units"
) -> etree._Element:
    if isinstance(value, list):  # compact [x, y] pairs
        value = {"loop": False, "vertices": value}
    if not isinstance(value, dict):
        raise ParameterError("Bline value must be a dict or a list of [x, y] vertices.")
    vertices = value.get("vertices") or value.get("points")
    if not vertices:
        raise ParameterError("Bline needs 'vertices': a list of [x, y] points.")
    loop = bool(value.get("loop", False))
    bline = make_element(
        "bline", type="bline_point", loop="true" if loop else None, guid=new_guid()
    )
    tangents1 = value.get("t1") or []
    tangents2 = value.get("t2") or []
    widths = value.get("widths") or []
    origins = value.get("origins") or []
    defaults = {"width": float(value.get("width", 1.0)), "origin": float(value.get("origin", 0.5))}
    for i, vertex in enumerate(vertices):
        point = _coerce_point(vertex, unit_px=unit_px, unit_system=unit_system)
        width = float(widths[i]) if i < len(widths) else defaults["width"]
        origin = float(origins[i]) if i < len(origins) else defaults["origin"]
        t1 = (
            _coerce_point(tangents1[i], unit_px=unit_px, unit_system=unit_system)
            if i < len(tangents1)
            else (0.0, 0.0)
        )
        composite = make_element("composite", type="bline_point")
        p1 = make_element("point")
        p1.append(_point_scalar(point))
        w = make_element("width")
        w.append(_scalar("real", width))
        o = make_element("origin")
        o.append(_scalar("real", origin))
        sp = make_element("split")
        sp.append(_scalar("bool", False))
        c1 = make_element("t1")
        c1.append(_point_scalar(t1))
        c2 = make_element("t2")
        t2 = (
            _coerce_point(tangents2[i], unit_px=unit_px, unit_system=unit_system)
            if i < len(tangents2)
            else t1
        )
        c2.append(_point_scalar(t2))
        sr = make_element("split_radius")
        sr.append(_scalar("bool", False))
        sa = make_element("split_angle")
        sa.append(_scalar("bool", False))
        for child in (p1, w, o, sp, c1, c2, sr, sa):
            composite.append(child)
        entry = make_element("entry")
        entry.append(composite)
        bline.append(entry)
    return bline


def decode_bline(
    el: etree._Element, *, unit_px: float = 60.0, unit_system: str = "units"
) -> dict[str, Any]:
    vertices: list[dict[str, Any]] = []
    for entry in el.findall("entry"):
        composite = entry.find("composite")
        if composite is None:
            continue
        point_el = composite.find("point")
        vec = point_el.find("vector") if point_el is not None else None
        if vec is not None:
            vertex = decode_vector(vec, unit_px=unit_px, unit_system=unit_system)
        else:
            vertex = {"x": 0.0, "y": 0.0}
        width_el = composite.find("width/real")
        origin_el = composite.find("origin/real")
        t1_el = composite.find("t1/vector")
        t2_el = composite.find("t2/vector")
        vertices.append(
            {
                "point": vertex,
                "width": _attr_float(width_el, "value", 1.0) if width_el is not None else 1.0,
                "origin": _attr_float(origin_el, "value", 0.5) if origin_el is not None else 0.5,
                "t1": decode_vector(t1_el, unit_px=unit_px, unit_system=unit_system)
                if t1_el is not None
                else None,
                "t2": decode_vector(t2_el, unit_px=unit_px, unit_system=unit_system)
                if t2_el is not None
                else None,
            }
        )
    return {"loop": el.get("loop") == "true", "vertices": vertices}


# ---------------------------------------------------------------------------
# vector_list (polygon/DynamicList of vectors)
# ---------------------------------------------------------------------------


def encode_vector_list(
    value: Any, *, unit_px: float = 60.0, unit_system: str = "units"
) -> etree._Element:
    vertices: Any = value
    if isinstance(value, dict):
        vertices = value.get("vertices") or value.get("points")
    if not isinstance(vertices, (list, tuple)) or len(vertices) < 1:
        raise ParameterError(
            "vector_list must be a list of [x, y] vertices (or {'vertices': [...]})."
        )
    lst = make_element("dynamic_list", type="vector")
    for vertex in vertices:
        point = _coerce_point(vertex, unit_px=unit_px, unit_system=unit_system)
        entry = make_element("entry")
        entry.append(_point_scalar(point))
        lst.append(entry)
    return lst


def _coerce_point(value: Any, *, unit_px: float, unit_system: str) -> tuple[float, float]:
    if isinstance(value, dict) and "x" in value and "y" in value:
        x, y = float(value["x"]), float(value["y"])
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        x, y = float(value[0]), float(value[1])
    else:
        raise ParameterError(f"Point must be [x, y] or {{'x':..,'y':..}}, got {value!r}.")
    if unit_system == "pixels":
        x, y = x / unit_px, y / unit_px
    return x, y


def _point_scalar(point: tuple[float, float]) -> etree._Element:
    vector = make_element("vector")
    x_el, y_el = make_element("x"), make_element("y")
    x_el.text, y_el.text = _fmt(point[0]), _fmt(point[1])
    vector.append(x_el)
    vector.append(y_el)
    return vector


def _scalar(tag: str, value: Any) -> etree._Element:
    el = make_element(tag)
    if tag == "bool":
        el.set("value", "true" if value else "false")
    elif tag == "integer":
        el.set("value", str(int(value)))
    elif tag == "time":
        el.set("value", str(value))
    else:
        el.set("value", _fmt(float(value)))
    return el


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ParameterError(f"Expected a number, got {value!r}.") from exc


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    raise ParameterError(f"Expected a boolean, got {value!r}.")


# ---------------------------------------------------------------------------
# Whole <param> encode/decode
# ---------------------------------------------------------------------------


def encode_param(
    name: str,
    value: Any,
    *,
    tag: str | None = None,
    reference: str | None = None,
    force_inline: bool = False,
    unit_px: float = 60.0,
    unit_system: str = "units",
    fps: float = 24.0,
) -> etree._Element:
    """Build a full ``<param>`` element from friendly input.

    ``tag`` forces the value type (e.g. "color", "vector"). ``reference``
    writes ``use=":export-name"`` (for exported values) or ``use="id"``.
    """
    param = make_element("param", name=name)
    if reference is not None:
        param.set("use", reference)
        return param
    expected = tag or _infer_scalar_tag(value)
    child = encode_value(
        value,
        expected=expected,
        unit_px=unit_px,
        unit_system=unit_system,
        fps=fps,
    )
    param.append(child)
    return param


def param_value_type(param: etree._Element) -> str | None:
    if len(param):
        child = param[0]
        return child.tag if isinstance(child.tag, str) else None
    if param.get("use"):
        return "reference"
    return None


def decode_param(
    param: etree._Element, *, unit_px: float = 60.0, unit_system: str = "units", fps: float = 24.0
) -> dict[str, Any]:
    name = param.get("name", "")
    if param.get("use"):
        return {"name": name, "type": "reference", "use": param.get("use")}
    if len(param) == 0:
        return {"name": name, "type": "empty", "value": None}
    child = param[0]
    decoded = decode_value(child, unit_px=unit_px, unit_system=unit_system, fps=fps)
    decoded = {"name": name, **decoded}
    return decoded
