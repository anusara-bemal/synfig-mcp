"""
Lossless SIF/SIFZ/SFG XML parser and document DOM model using lxml.

Provides complete round-trip preservation of unknown XML nodes, comments,
CDATA, namespaces, and attribute ordering, while exposing typed methods
for layer manipulation, canvas properties, parameter get/set, and keyframes.
"""

import gzip
import re
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any

from lxml import etree

from synfig_mcp.errors import SynfigError
from synfig_mcp.protocol.models import (
    AngleValue,
    BLinePoint,
    BLinePointListValue,
    BoolValue,
    CanvasRefValue,
    ColorStop,
    ColorValue,
    GradientValue,
    IntegerValue,
    RealValue,
    StringValue,
    SynfigValue,
    TimeValue,
    ValueNodeLinkValue,
    VectorValue,
)
from synfig_mcp.sif.valuenodes import (
    build_valuenode_element,
    normalize_interpolation,
    value_type_of,
)


def is_element_tag(elem: etree._Element, tag_name: str) -> bool:
    """Check if an element is a real XML tag with matching local name (ignoring comments/PI)."""
    return isinstance(elem.tag, str) and etree.QName(elem.tag).localname == tag_name


def parse_synfig_time(time_str: str, fps: float = 24.0) -> float:
    """Parse Synfig time string (e.g. '0f', '1s 12f', '2.5s', '1m 30s') into seconds."""
    time_str = time_str.strip()
    if not time_str:
        return 0.0

    # Handle single signed float or int without units
    try:
        return float(time_str)
    except ValueError:
        pass

    total_seconds = 0.0
    # Match patterns like "1h", "2m", "3s", "12f"
    matches = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*([hmsf])?", time_str)
    if not matches:
        return 0.0

    for value_str, unit in matches:
        val = float(value_str)
        if unit == "h":
            total_seconds += val * 3600.0
        elif unit == "m":
            total_seconds += val * 60.0
        elif unit == "s":
            total_seconds += val
        elif unit == "f":
            total_seconds += val / fps if fps > 0 else 0.0
        else:
            total_seconds += val

    return total_seconds


def format_synfig_time(seconds: float, fps: float = 24.0) -> str:
    """Format seconds into Synfig canonical time string (e.g. '1s 12f' or '0s')."""
    if abs(seconds) < 1e-6:
        return "0s"
    # Round to frames
    total_frames = int(round(seconds * fps))
    s = total_frames // int(fps)
    f = total_frames % int(fps)
    if f == 0:
        return f"{s}s"
    if s == 0:
        return f"{f}f"
    return f"{s}s {f}f"


def _param_value_type(param: etree._Element) -> str | None:
    """Determine the value type of a ``<param>`` element."""
    for child in param:
        tag = etree.QName(str(child.tag)).localname if isinstance(child.tag, str) else ""
        if tag == "animated":
            return child.get("type")
        return value_type_of(child)
    return None


def _coerce_value(value: Any, current_type: str | None) -> Any:
    """Coerce loosely typed values into the type the parameter expects.

    The MCP accepts plain JSON scalars, so ``[0.0, 0.0]`` may be used where a
    vector is expected and ``2.0`` where a real/angle/time is expected.  The
    current value of the parameter decides the concrete type, which keeps the
    written document consistent with the parameter it belongs to.

    The nested spelling ``{"type": "vector", "value": {"x": 0, "y": 0}}`` is
    accepted as well and flattened, because it is the form used by several
    Synfig examples and by older versions of the MCP guides.
    """
    if isinstance(value, dict):
        inner = value.get("value")
        if isinstance(inner, dict):
            return {"type": value.get("type"), **inner}
        return value

    if isinstance(value, (list, tuple)):
        if (
            len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)
            and current_type in (None, "vector", "unknown")
        ):
            return VectorValue(x=float(value[0]), y=float(value[1]))
        raise SynfigError(
            f"Cannot convert the sequence {value!r} into a Synfig parameter value. "
            "Use a typed value such as {'type': 'vector', 'x': 0.0, 'y': 0.0}."
        )

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if current_type == "angle":
            return AngleValue(degrees=float(value))
        if current_type == "time":
            return TimeValue(seconds=float(value))
        if current_type == "integer":
            return IntegerValue(value=int(value))
        return value
    return value


def _read_real_child(element: etree._Element | None, default: float) -> float:
    """Read a ``<real value="..."/>`` child element."""
    if element is None:
        return default
    real_el = element.find("real")
    if real_el is None:
        return default
    value = real_el.get("value")
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def xml_to_synfig_value(elem: etree._Element) -> SynfigValue | None:
    """Convert an XML element inside <param> into a typed SynfigValue."""
    if not isinstance(elem.tag, str):
        return None
    tag = etree.QName(elem.tag).localname

    if tag == "real":
        return RealValue(value=float(elem.get("value", "0.0")))
    if tag == "integer":
        return IntegerValue(value=int(elem.get("value", "0")))
    if tag == "bool":
        val_str = elem.get("value", "false").strip().lower()
        return BoolValue(value=val_str in ("true", "1"))
    if tag == "string":
        s_val = elem.text if elem.text is not None else elem.get("value", "")
        return StringValue(value=s_val or "")
    if tag == "angle":
        deg = float(elem.get("value", "0.0"))
        return AngleValue(degrees=deg)
    if tag == "time":
        time_str = elem.get("value", "0s")
        sec = parse_synfig_time(time_str)
        return TimeValue(seconds=sec, time_string=time_str)
    if tag == "color":
        r_elem = elem.find("r")
        g_elem = elem.find("g")
        b_elem = elem.find("b")
        a_elem = elem.find("a")
        r = float(r_elem.text) if r_elem is not None and r_elem.text else 0.0
        g = float(g_elem.text) if g_elem is not None and g_elem.text else 0.0
        b = float(b_elem.text) if b_elem is not None and b_elem.text else 0.0
        a = float(a_elem.text) if a_elem is not None and a_elem.text else 1.0
        return ColorValue(r=r, g=g, b=b, a=a)
    if tag == "vector":
        x_elem = elem.find("x")
        y_elem = elem.find("y")
        x = float(x_elem.text) if x_elem is not None and x_elem.text else 0.0
        y = float(y_elem.text) if y_elem is not None and y_elem.text else 0.0
        return VectorValue(x=x, y=y, unit="synfig")
    if tag == "gradient":
        cpoints: list[ColorStop] = []
        for child in elem:
            if not is_element_tag(child, "color"):
                continue
            pos = float(child.get("pos", "0.0"))
            r_e = child.find("r")
            g_e = child.find("g")
            b_e = child.find("b")
            a_e = child.find("a")
            c_val = ColorValue(
                r=float(r_e.text) if r_e is not None and r_e.text else 0.0,
                g=float(g_e.text) if g_e is not None and g_e.text else 0.0,
                b=float(b_e.text) if b_e is not None and b_e.text else 0.0,
                a=float(a_e.text) if a_e is not None and a_e.text else 1.0,
            )
            cpoints.append(ColorStop(pos=pos, color=c_val))
        return GradientValue(cpoints=cpoints)
    if tag == "canvas":
        canvas_id = elem.get("id", "")
        return CanvasRefValue(canvas_id=canvas_id)
    if tag == "bline":
        points: list[BLinePoint] = []
        for pt_elem in elem.findall("entry"):
            # entry can contain bline_point
            bp = pt_elem.find("bline_point")
            if bp is not None:
                v_el = bp.find("vertex")
                vx, vy = 0.0, 0.0
                if v_el is not None:
                    ve = v_el.find("vector")
                    if ve is not None:
                        vx = float(ve.findtext("x", "0.0"))
                        vy = float(ve.findtext("y", "0.0"))
                t1_el = bp.find("t1")
                t1x, t1y = 0.0, 0.0
                if t1_el is not None:
                    te = t1_el.find("vector")
                    if te is not None:
                        t1x = float(te.findtext("x", "0.0"))
                        t1y = float(te.findtext("y", "0.0"))
                t2_el = bp.find("t2")
                t2x, t2y = 0.0, 0.0
                if t2_el is not None:
                    te = t2_el.find("vector")
                    if te is not None:
                        t2x = float(te.findtext("x", "0.0"))
                        t2y = float(te.findtext("y", "0.0"))
                w_el = bp.find("width")
                w = _read_real_child(w_el, 1.0)
                o_el = bp.find("origin")
                o = _read_real_child(o_el, 0.5)
                points.append(
                    BLinePoint(
                        vertex=(vx, vy),
                        t1=(t1x, t1y),
                        t2=(t2x, t2y),
                        width=w,
                        origin=o,
                    )
                )
        return BLinePointListValue(points=points)
    if tag == "animated":
        for wp in elem:
            if is_element_tag(wp, "waypoint"):
                for wp_child in wp:
                    val = xml_to_synfig_value(wp_child)
                    if val is not None:
                        return val
    if tag == "waypoint":
        for wp_child in elem:
            val = xml_to_synfig_value(wp_child)
            if val is not None:
                return val

    return None


def _gradient_to_xml(cpoints: list[Any]) -> etree._Element:
    """Serialise a gradient into the Synfig ``<gradient>`` element."""
    elem = etree.Element("gradient")
    for cpoint in cpoints:
        data = cpoint.model_dump() if hasattr(cpoint, "model_dump") else dict(cpoint)
        color = data.get("color") or {}
        if hasattr(color, "model_dump"):
            color = color.model_dump()
        c_el = etree.SubElement(elem, "color")
        c_el.set("pos", f"{float(data.get('pos', 0.0)):.6f}")
        for channel in ("r", "g", "b", "a"):
            ch_el = etree.SubElement(c_el, channel)
            default = 1.0 if channel == "a" else 0.0
            ch_el.text = f"{float(color.get(channel, default)):.6f}"
    return elem


def _bline_to_xml(points: list[Any]) -> etree._Element:
    """Serialise spline points into the Synfig ``<bline>`` element."""
    elem = etree.Element("bline")
    elem.set("type", "bline_point")
    for point in points:
        data = point.model_dump() if hasattr(point, "model_dump") else dict(point)
        entry = etree.SubElement(elem, "entry")
        bp = etree.SubElement(entry, "bline_point")
        for name in ("vertex", "t1", "t2"):
            vector = data.get(name) or (0.0, 0.0)
            v_el = etree.SubElement(bp, name)
            vec_el = etree.SubElement(v_el, "vector")
            x_el = etree.SubElement(vec_el, "x")
            x_el.text = f"{float(vector[0]):.10f}"
            y_el = etree.SubElement(vec_el, "y")
            y_el.text = f"{float(vector[1]):.10f}"
        width_el = etree.SubElement(bp, "width")
        width_real = etree.SubElement(width_el, "real")
        width_real.set("value", f"{float(data.get('width', 1.0)):.10f}")
        origin_el = etree.SubElement(bp, "origin")
        origin_real = etree.SubElement(origin_el, "real")
        origin_real.set("value", f"{float(data.get('origin', 0.5)):.10f}")
    return elem


def synfig_value_to_xml(value: SynfigValue | dict[str, Any] | Any) -> etree._Element:
    """Convert a SynfigValue, dict, or primitive into an lxml element suitable for <param>."""
    if isinstance(value, dict):
        val_type = value.get("type")
        if val_type == "real":
            elem = etree.Element("real")
            elem.set("value", f"{float(value.get('value', 0.0)):.10f}")
            return elem
        if val_type == "integer":
            elem = etree.Element("integer")
            elem.set("value", str(int(value.get("value", 0))))
            return elem
        if val_type == "bool":
            elem = etree.Element("bool")
            elem.set("value", "true" if value.get("value") else "false")
            return elem
        if val_type == "string":
            elem = etree.Element("string")
            elem.text = str(value.get("value", ""))
            return elem
        if val_type == "angle":
            elem = etree.Element("angle")
            deg = float(value.get("degrees", 0.0))
            elem.set("value", f"{deg:.6f}")
            return elem
        if val_type == "time":
            elem = etree.Element("time")
            sec = float(value.get("seconds", 0.0))
            elem.set("value", f"{sec:.4f}s")
            return elem
        if val_type == "color":
            elem = etree.Element("color")
            for channel in ("r", "g", "b", "a"):
                ch_el = etree.SubElement(elem, channel)
                ch_val = float(value.get(channel, 1.0 if channel == "a" else 0.0))
                ch_el.text = f"{ch_val:.6f}"
            return elem
        if val_type == "vector":
            elem = etree.Element("vector")
            x_el = etree.SubElement(elem, "x")
            x_el.text = f"{float(value.get('x', 0.0)):.10f}"
            y_el = etree.SubElement(elem, "y")
            y_el.text = f"{float(value.get('y', 0.0)):.10f}"
            return elem
        if val_type == "gradient":
            return _gradient_to_xml(value.get("cpoints") or [])
        if val_type == "bline_point_list":
            return _bline_to_xml(value.get("points") or [])
        if val_type == "bline":
            return _bline_to_xml(value.get("points") or [])
        if val_type == "canvas_ref":
            elem = etree.Element("canvas")
            elem.set("id", str(value.get("canvas_id", "")))
            return elem
        if val_type == "valuenode_link":
            elem = etree.Element("valuenode")
            elem.set("id", str(value.get("link_id", "")))
            return elem
        raise SynfigError(
            f"Unsupported parameter value type '{val_type}'. "
            "Supported types: real, integer, bool, string, angle, time, color, "
            "vector, gradient, bline_point_list, canvas_ref, valuenode_link."
        )

    if isinstance(value, RealValue):
        elem = etree.Element("real")
        elem.set("value", f"{value.value:.10f}")
        return elem
    if isinstance(value, IntegerValue):
        elem = etree.Element("integer")
        elem.set("value", str(value.value))
        return elem
    if isinstance(value, BoolValue):
        elem = etree.Element("bool")
        elem.set("value", "true" if value.value else "false")
        return elem
    if isinstance(value, StringValue):
        elem = etree.Element("string")
        elem.text = value.value
        return elem
    if isinstance(value, AngleValue):
        elem = etree.Element("angle")
        elem.set("value", f"{value.degrees:.6f}")
        return elem
    if isinstance(value, TimeValue):
        elem = etree.Element("time")
        elem.set("value", f"{value.seconds:.4f}s")
        return elem
    if isinstance(value, ColorValue):
        elem = etree.Element("color")
        for channel, ch_val in (
            ("r", value.r),
            ("g", value.g),
            ("b", value.b),
            ("a", value.a),
        ):
            ch_el = etree.SubElement(elem, channel)
            ch_el.text = f"{ch_val:.6f}"
        return elem
    if isinstance(value, VectorValue):
        elem = etree.Element("vector")
        x_el = etree.SubElement(elem, "x")
        x_el.text = f"{value.x:.10f}"
        y_el = etree.SubElement(elem, "y")
        y_el.text = f"{value.y:.10f}"
        return elem
    if isinstance(value, GradientValue):
        elem = etree.Element("gradient")
        for cp in value.cpoints:
            c_el = etree.SubElement(elem, "color")
            c_el.set("pos", f"{cp.pos:.6f}")
            for channel, ch_val in (
                ("r", cp.color.r),
                ("g", cp.color.g),
                ("b", cp.color.b),
                ("a", cp.color.a),
            ):
                ch_e = etree.SubElement(c_el, channel)
                ch_e.text = f"{ch_val:.6f}"
        return elem
    if isinstance(value, CanvasRefValue):
        elem = etree.Element("canvas")
        elem.set("id", value.canvas_id)
        return elem
    if isinstance(value, BLinePointListValue):
        return _bline_to_xml([p.model_dump() for p in value.points])
    if isinstance(value, ValueNodeLinkValue):
        elem = etree.Element("valuenode")
        elem.set("id", value.link_id)
        return elem

    # Primitive python fallbacks
    if isinstance(value, bool):
        elem = etree.Element("bool")
        elem.set("value", "true" if value else "false")
        return elem
    if isinstance(value, int):
        elem = etree.Element("integer")
        elem.set("value", str(value))
        return elem
    if isinstance(value, float):
        elem = etree.Element("real")
        elem.set("value", f"{value:.10f}")
        return elem
    if isinstance(value, str):
        elem = etree.Element("string")
        elem.text = value
        return elem

    raise SynfigError(
        f"Unsupported parameter value of type '{type(value).__name__}'. "
        "Pass a typed value such as {'type': 'real', 'value': 1.0}."
    )


class SifLayer:
    """Represents a <layer> node within a Synfig SIF document."""

    def __init__(self, element: etree._Element, parent_canvas: etree._Element) -> None:
        self.element = element
        self.parent_canvas = parent_canvas

    @property
    def type(self) -> str:
        return self.element.get("type", "")

    @type.setter
    def type(self, value: str) -> None:
        self.element.set("type", value)

    @property
    def desc(self) -> str:
        return self.element.get("desc", self.type)

    @desc.setter
    def desc(self, value: str) -> None:
        self.element.set("desc", value)

    @property
    def active(self) -> bool:
        return self.element.get("active", "true").lower() == "true"

    @active.setter
    def active(self, value: bool) -> None:
        self.element.set("active", "true" if value else "false")

    @property
    def version(self) -> str:
        return self.element.get("version", "0.1")

    @property
    def depth(self) -> int:
        """Visual depth in Synfig (0 = topmost, N-1 = bottom-most)."""
        layers = [e for e in self.parent_canvas if is_element_tag(e, "layer")]
        try:
            xml_idx = layers.index(self.element)
            return len(layers) - 1 - xml_idx
        except ValueError:
            return 0

    def get_param(self, name: str) -> SynfigValue | None:
        """Get typed value for a parameter."""
        for param in self.element.findall("param"):
            if param.get("name") == name:
                for child in param:
                    val = xml_to_synfig_value(child)
                    if val is not None:
                        return val
        return None

    def set_param(self, name: str, value: SynfigValue | dict[str, Any] | Any) -> None:
        """Set or update a parameter value."""
        target_param: etree._Element | None = None
        current_type: str | None = None
        for param in self.element.findall("param"):
            if param.get("name") == name:
                target_param = param
                current_type = _param_value_type(param)
                break

        if target_param is None:
            target_param = etree.SubElement(self.element, "param")
            target_param.set("name", name)
        else:
            # Clear existing value children
            for child in list(target_param):
                target_param.remove(child)

        new_val_el = synfig_value_to_xml(_coerce_value(value, current_type))
        target_param.append(new_val_el)

    def set_waypoint(
        self,
        name: str,
        time: float,
        value: SynfigValue | dict[str, Any] | Any,
        interpolation: str = "linear",
        interpolation_in: str | None = None,
        interpolation_out: str | None = None,
    ) -> None:
        """Insert or update a waypoint at a specific time on a parameter."""
        target_param = None
        current_type: str | None = None
        for param in self.element.findall("param"):
            if param.get("name") == name:
                target_param = param
                current_type = _param_value_type(param)
                break

        if target_param is None:
            target_param = etree.SubElement(self.element, "param")
            target_param.set("name", name)

        animated_el = target_param.find("animated")
        if animated_el is None:
            old_child = list(target_param)[0] if len(target_param) > 0 else None
            old_type = (
                etree.QName(str(old_child.tag)).localname if old_child is not None else "vector"
            )
            current_type = current_type or old_type
            for child in list(target_param):
                target_param.remove(child)
            animated_el = etree.SubElement(target_param, "animated")
            animated_el.set("type", old_type)

        target_wp = None
        time_f = parse_synfig_time(time) if isinstance(time, str) else float(time)
        time_str = f"{time_f:.4f}s" if time_f != int(time_f) else f"{int(time_f)}s"
        for wp in animated_el.findall("waypoint"):
            t_wp = parse_synfig_time(wp.get("time", "0s"))
            if abs(t_wp - time_f) < 1e-4:
                target_wp = wp
                break

        interp_before = normalize_interpolation(interpolation_in or interpolation)
        interp_after = normalize_interpolation(interpolation_out or interpolation)

        if target_wp is None:
            target_wp = etree.SubElement(animated_el, "waypoint")
            target_wp.set("time", time_str)
            target_wp.set("before", interp_before)
            target_wp.set("after", interp_after)
        else:
            target_wp.set("time", time_str)
            target_wp.set("before", interp_before)
            target_wp.set("after", interp_after)
            for c in list(target_wp):
                target_wp.remove(c)

        val_el = synfig_value_to_xml(_coerce_value(value, current_type))
        target_wp.append(val_el)

    def remove_waypoint(self, name: str, time: float) -> bool:
        """Remove a waypoint at a specific time."""
        for param in self.element.findall("param"):
            if param.get("name") == name:
                animated_el = param.find("animated")
                if animated_el is not None:
                    for wp in animated_el.findall("waypoint"):
                        t_wp = parse_synfig_time(wp.get("time", "0s"))
                        if abs(t_wp - time) < 1e-4:
                            animated_el.remove(wp)
                            return True
        return False

    def get_interpolated_param(self, name: str, time: float) -> SynfigValue | None:
        """Get parameter value evaluated at timeline position."""
        for param in self.element.findall("param"):
            if param.get("name") == name:
                animated_el = param.find("animated")
                if animated_el is not None:
                    wps: list[tuple[float, etree._Element]] = []
                    for wp in animated_el.findall("waypoint"):
                        t = parse_synfig_time(wp.get("time", "0s"))
                        wps.append((t, wp))
                    wps.sort(key=lambda x: x[0])
                    if not wps:
                        return None
                    if time <= wps[0][0]:
                        return xml_to_synfig_value(list(wps[0][1])[0])
                    if time >= wps[-1][0]:
                        return xml_to_synfig_value(list(wps[-1][1])[0])
                    for i in range(len(wps) - 1):
                        t0, wp0 = wps[i]
                        t1, wp1 = wps[i + 1]
                        if t0 <= time <= t1:
                            val0 = xml_to_synfig_value(list(wp0)[0])
                            val1 = xml_to_synfig_value(list(wp1)[0])
                            if val0 is None or val1 is None:
                                return val0 or val1
                            alpha = (time - t0) / (t1 - t0) if t1 > t0 else 0.0
                            if isinstance(val0, VectorValue) and isinstance(val1, VectorValue):
                                return VectorValue(
                                    x=val0.x + alpha * (val1.x - val0.x),
                                    y=val0.y + alpha * (val1.y - val0.y),
                                    unit="synfig",
                                )
                            if isinstance(val0, RealValue) and isinstance(val1, RealValue):
                                return RealValue(
                                    value=val0.value + alpha * (val1.value - val0.value)
                                )
                            if isinstance(val0, ColorValue) and isinstance(val1, ColorValue):
                                return ColorValue(
                                    r=val0.r + alpha * (val1.r - val0.r),
                                    g=val0.g + alpha * (val1.g - val0.g),
                                    b=val0.b + alpha * (val1.b - val0.b),
                                    a=val0.a + alpha * (val1.a - val0.a),
                                )
                            return val0 if alpha < 0.5 else val1
                for child in param:
                    val = xml_to_synfig_value(child)
                    if val is not None:
                        return val
        return None

    def convert_param(self, name: str, valuenode_type: str) -> None:
        """Convert a parameter into a linkable ValueNode of the requested type.

        The generated XML follows the exact shape the Synfig engine expects
        (``<linear type="real"><slope>...</slope><offset>...</offset></linear>``)
        so the resulting document stays loadable.
        """
        for param in self.element.findall("param"):
            if param.get("name") != name:
                continue
            children = list(param)
            if not children:
                raise SynfigError(
                    f"Parameter '{name}' has no value that can be converted to a ValueNode."
                )
            current = children[0]
            value_type = _param_value_type(param) or value_type_of(current)
            if value_type in {"bline_point_list", "width_point_list", "dash_item_list"}:
                raise SynfigError(
                    f"Parameter '{name}' holds a complex '{value_type}' value which cannot "
                    "be converted to a ValueNode."
                )
            new_node = build_valuenode_element(valuenode_type, value_type, current)
            for child in children:
                param.remove(child)
            param.append(new_node)
            return
        raise SynfigError(f"Parameter '{name}' not found on layer.")

    def export_param(self, name: str, export_name: str, canvas_root: etree._Element) -> None:
        """Export a parameter value into the canvas ``<defs>`` value node library.

        Synfig stores exported value nodes as ``<defs><real id="name" .../></defs>``
        and references them with ``<param name="x" use="name"/>``.  The ``<defs>``
        section must appear *before* the layers that reference it, otherwise the
        engine reports "Unknown ID referenced in parameter".
        """
        defs = self._find_or_create_defs(canvas_root)
        for existing in defs.findall("valuenode"):
            if existing.get("id") == export_name:
                raise SynfigError(f"A value node named '{export_name}' already exists.")

        for param in self.element.findall("param"):
            if param.get("name") != name:
                continue
            children = list(param)
            if not children:
                raise SynfigError(f"Parameter '{name}' has no value to export.")
            current = children[0]
            exported = etree.fromstring(etree.tostring(current))
            exported.set("id", export_name)
            defs.append(exported)
            for child in children:
                param.remove(child)
            param.set("use", export_name)
            return
        raise SynfigError(f"Parameter '{name}' not found on layer.")

    @staticmethod
    def _find_or_create_defs(canvas_root: etree._Element) -> etree._Element:
        """Return the ``<defs>`` section of a canvas, creating it before the layers."""
        defs = canvas_root.find("defs")
        if defs is not None:
            return defs
        defs = etree.Element("defs")
        first_layer = None
        for child in canvas_root:
            if is_element_tag(child, "layer"):
                first_layer = child
                break
        if first_layer is not None:
            canvas_root.insert(canvas_root.index(first_layer), defs)
        else:
            canvas_root.append(defs)
        return defs

    def get_params(self) -> dict[str, Any]:
        """Return dictionary of all defined parameters on this layer."""
        result: dict[str, Any] = {}
        for param in self.element.findall("param"):
            p_name = param.get("name")
            if p_name:
                for child in param:
                    val = xml_to_synfig_value(child)
                    if val is not None:
                        result[p_name] = val.model_dump()
                        break
        return result

    def get_subcanvas(self) -> etree._Element | None:
        """If this is a PasteCanvas/group layer, get the child <canvas> element."""
        for param in self.element.findall("param"):
            if param.get("name") == "canvas":
                c = param.find("canvas")
                if c is not None:
                    return c
        return None


class SifDocument:
    """Represents a lossless SIF/SIFZ/SFG Synfig document."""

    def __init__(self, tree: etree._ElementTree) -> None:
        self.tree = tree
        self.root: etree._Element = tree.getroot()
        self._container_assets: dict[str, bytes] = {}

    @classmethod
    def from_string(cls, xml_text: str) -> "SifDocument":
        """Parse document from XML text, preserving all whitespace and formatting."""
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, strip_cdata=False)
        root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
        return cls(etree.ElementTree(root))

    @classmethod
    def from_bytes(cls, data: bytes, format_hint: str = "sif") -> "SifDocument":
        """Parse document from raw bytes (.sif, .sifz gzip, or .sfg zip)."""
        hint = format_hint.lower()
        if hint.endswith(".sifz") or (len(data) >= 2 and data[:2] == b"\x1f\x8b"):
            # Gzip compressed
            xml_data = gzip.decompress(data)
            return cls.from_string(xml_data.decode("utf-8", errors="replace"))

        if hint.endswith(".sfg") or (len(data) >= 4 and data[:4] == b"PK\x03\x04"):
            # ZIP container
            with zipfile.ZipFile(BytesIO(data), "r") as zf:
                # Find project.sif or project.sifz
                names = zf.namelist()
                sif_name: str | None = None
                for candidate in (
                    "project.sif",
                    "project.sifz",
                    "canvas.sif",
                    "canvas.sifz",
                ):
                    if candidate in names:
                        sif_name = candidate
                        break
                if sif_name is None:
                    for n in names:
                        if n.endswith(".sif") or n.endswith(".sifz"):
                            sif_name = n
                            break

                if not sif_name:
                    raise ValueError("No SIF document found inside SFG container.")

                sif_bytes = zf.read(sif_name)
                if sif_name.endswith(".sifz") or (
                    len(sif_bytes) >= 2 and sif_bytes[:2] == b"\x1f\x8b"
                ):
                    sif_bytes = gzip.decompress(sif_bytes)

                doc = cls.from_string(sif_bytes.decode("utf-8", errors="replace"))
                # Store all other assets
                for n in names:
                    if n != sif_name:
                        doc._container_assets[n] = zf.read(n)
                return doc

        return cls.from_string(data.decode("utf-8", errors="replace"))

    @classmethod
    def from_file(cls, path: Path) -> "SifDocument":
        """Load document from a .sif, .sifz, or .sfg file."""
        data = path.read_bytes()
        return cls.from_bytes(data, format_hint=path.suffix)

    @classmethod
    def new(
        cls,
        width: int = 1920,
        height: int = 1080,
        fps: float = 24.0,
        duration_seconds: float = 5.0,
        name: str = "Synfig Animation 1",
    ) -> "SifDocument":
        """Create a new pristine Synfig SIF canvas."""
        root = etree.Element(
            "canvas",
            version="1.2",
            width=str(width),
            height=str(height),
            xres="2834.645752",
            yres="2834.645752",
            fps=f"{fps:.3f}",
            antialias="2",
        )
        root.set("begin-time", "0s")
        root.set("end-time", f"{duration_seconds:.2f}s")
        # Aspect ratio view-box
        aspect = width / height if height > 0 else 1.0
        root.set("view-box", f"{-4.0 * aspect:.6f} 4.000000 {4.0 * aspect:.6f} -4.000000")
        root.set("bgcolor", "0.500000 0.500000 0.500000 1.000000")

        name_el = etree.SubElement(root, "name")
        name_el.text = name

        return cls(etree.ElementTree(root))

    def to_xml_bytes(self) -> bytes:
        """Serialize document to UTF-8 XML bytes preserving declaration."""
        return etree.tostring(
            self.tree,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=False,
        )

    def to_xml_string(self) -> str:
        """Serialize document to UTF-8 XML string."""
        return self.to_xml_bytes().decode("utf-8")

    # -----------------------------------------------------------------------
    # Canvas Properties
    # -----------------------------------------------------------------------

    @property
    def width(self) -> int:
        return int(self.root.get("width", "1920"))

    @width.setter
    def width(self, val: int) -> None:
        self.root.set("width", str(val))

    @property
    def height(self) -> int:
        return int(self.root.get("height", "1080"))

    @height.setter
    def height(self, val: int) -> None:
        self.root.set("height", str(val))

    @property
    def fps(self) -> float:
        return float(self.root.get("fps", "24.0"))

    @fps.setter
    def fps(self, val: float) -> None:
        self.root.set("fps", f"{val:.3f}")

    @property
    def start_time(self) -> float:
        return parse_synfig_time(self.root.get("begin-time", "0s"), self.fps)

    @start_time.setter
    def start_time(self, val: float) -> None:
        self.root.set("begin-time", f"{val:.2f}s")

    @property
    def end_time(self) -> float:
        return parse_synfig_time(self.root.get("end-time", "5s"), self.fps)

    @end_time.setter
    def end_time(self, val: float) -> None:
        self.root.set("end-time", f"{val:.2f}s")

    def unexport_valuenode(self, export_name: str) -> bool:
        """Remove an exported valuenode from ``<defs>``.

        Any parameter that referenced the exported node is rewritten with an
        inline copy of the exported value so the document keeps its values and
        stays loadable in Synfig.
        """
        defs = self.root.find("defs")
        if defs is None:
            return False
        for vn in list(defs):
            if vn.get("id") != export_name:
                continue
            for param in self.root.iter("param"):
                if param.get("use") != export_name:
                    continue
                inline = etree.fromstring(etree.tostring(vn))
                inline.attrib.pop("id", None)
                for child in list(param):
                    param.remove(child)
                param.append(inline)
                param.attrib.pop("use", None)
            defs.remove(vn)
            return True
        return False

    @property
    def name(self) -> str:
        name_el = self.root.find("name")
        return name_el.text if name_el is not None and name_el.text else "Synfig Animation"

    @name.setter
    def name(self, val: str) -> None:
        name_el = self.root.find("name")
        if name_el is None:
            name_el = etree.Element("name")
            self.root.insert(0, name_el)
        name_el.text = val

    @property
    def desc(self) -> str:
        desc_el = self.root.find("desc")
        return desc_el.text if desc_el is not None and desc_el.text else ""

    @desc.setter
    def desc(self, val: str) -> None:
        desc_el = self.root.find("desc")
        if desc_el is None:
            desc_el = etree.Element("desc")
            self.root.insert(1, desc_el)
        desc_el.text = val

    def set_properties(
        self,
        name: str | None = None,
        desc: str | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> None:
        """Update multiple canvas properties atomically."""
        if name is not None:
            self.name = name
        if desc is not None:
            self.desc = desc
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        if fps is not None:
            self.fps = fps
        if start_time is not None:
            self.start_time = start_time
        if end_time is not None:
            self.end_time = end_time

    # -----------------------------------------------------------------------
    # Canvas Navigation
    # -----------------------------------------------------------------------

    def _resolve_canvas(self, canvas_path: str = "") -> etree._Element:
        """Resolve a canvas path (e.g. '' for root, 'Group1/SubGroup') to its XML element."""
        if not canvas_path or canvas_path in ("/", "root"):
            return self.root

        current = self.root
        parts = [p.strip() for p in canvas_path.strip("/").split("/") if p.strip()]

        for part in parts:
            found = False
            # Look for layer with matching desc or type
            for elem in current:
                if is_element_tag(elem, "layer"):
                    desc = elem.get("desc", elem.get("type", ""))
                    if desc == part:
                        for param in elem.findall("param"):
                            if param.get("name") == "canvas":
                                c = param.find("canvas")
                                if c is not None:
                                    current = c
                                    found = True
                                    break
                    if found:
                        break
            if not found:
                # Also check <defs><canvas id="...">
                defs = self.root.find("defs")
                if defs is not None:
                    for c in defs.findall("canvas"):
                        if c.get("id") == part:
                            current = c
                            found = True
                            break
            if not found:
                raise ValueError(f"Canvas path component '{part}' not found in '{canvas_path}'")

        return current

    def list_canvases(self) -> list[str]:
        """List all canvas paths in the document."""
        paths = ["/"]

        def _traverse(node: etree._Element, current_path: str) -> None:
            for elem in node:
                if is_element_tag(elem, "layer"):
                    desc = elem.get("desc", elem.get("type", ""))
                    for param in elem.findall("param"):
                        if param.get("name") == "canvas":
                            c = param.find("canvas")
                            if c is not None:
                                p = f"{current_path}/{desc}" if current_path != "/" else f"/{desc}"
                                paths.append(p)
                                _traverse(c, p)

        _traverse(self.root, "/")
        defs = self.root.find("defs")
        if defs is not None:
            for c in defs.findall("canvas"):
                c_id = c.get("id")
                if c_id:
                    paths.append(f"defs/{c_id}")
        return paths

    # -----------------------------------------------------------------------
    # Layer Operations
    # -----------------------------------------------------------------------

    def get_layers(self, canvas_path: str = "") -> list[SifLayer]:
        """Get all layers in the given canvas in Synfig depth order (0=topmost)."""
        canvas = self._resolve_canvas(canvas_path)
        xml_layers = [e for e in canvas if is_element_tag(e, "layer")]
        # In XML, bottom layer is first; in Synfig depth 0 is topmost (last in XML)
        return [SifLayer(e, canvas) for e in reversed(xml_layers)]

    def get_layer(self, layer_id_or_desc: str, canvas_path: str = "") -> SifLayer | None:
        """Find a layer by desc or type."""
        for layer in self.get_layers(canvas_path):
            if layer.desc == layer_id_or_desc or layer.type == layer_id_or_desc:
                return layer
        return None

    def add_layer(
        self,
        layer_type: str,
        canvas_path: str = "",
        desc: str | None = None,
        params: dict[str, Any] | None = None,
        depth: int | None = None,
        version: str | None = None,
    ) -> SifLayer:
        """Add a new layer to the specified canvas at the given depth."""
        canvas = self._resolve_canvas(canvas_path)
        elem = etree.Element("layer")
        elem.set("type", layer_type)
        elem.set("active", "true")
        elem.set("version", version or "0.1")
        elem.set("desc", desc or f"{layer_type.capitalize()}001")

        # Set default parameters according to layer type
        layer = SifLayer(elem, canvas)
        if layer_type == "circle":
            layer.set_param("radius", RealValue(value=1.0))
            layer.set_param("origin", VectorValue(x=0.0, y=0.0))
            layer.set_param("color", ColorValue(r=0.2, g=0.5, b=0.9, a=1.0))
            layer.set_param("feather", RealValue(value=0.0))
            layer.set_param("invert", BoolValue(value=False))
        elif layer_type == "rectangle":
            layer.set_param("point1", VectorValue(x=-1.0, y=1.0))
            layer.set_param("point2", VectorValue(x=1.0, y=-1.0))
            layer.set_param("color", ColorValue(r=0.8, g=0.2, b=0.2, a=1.0))
        elif layer_type == "star":
            layer.set_param("radius1", RealValue(value=1.0))
            layer.set_param("radius2", RealValue(value=0.5))
            layer.set_param("points", IntegerValue(value=5))
            layer.set_param("origin", VectorValue(x=0.0, y=0.0))
            layer.set_param("color", ColorValue(r=0.9, g=0.8, b=0.1, a=1.0))
        elif layer_type == "solid_color":
            layer.set_param("color", ColorValue(r=0.1, g=0.1, b=0.1, a=1.0))
        elif layer_type == "text":
            layer.set_param("text", StringValue(value="Text"))
            layer.set_param("color", ColorValue(r=1.0, g=1.0, b=1.0, a=1.0))
            layer.set_param("origin", VectorValue(x=0.0, y=0.0))
            layer.set_param("size", VectorValue(x=0.25, y=0.25))
        elif layer_type in ("group", "PasteCanvas"):
            elem.set("type", "PasteCanvas")
            p_canvas = etree.SubElement(elem, "param")
            p_canvas.set("name", "canvas")
            etree.SubElement(p_canvas, "canvas")

        # Apply custom params
        if params:
            for k, v in params.items():
                layer.set_param(k, v)

        # Insert at requested depth (depth 0 = topmost = end of canvas children)
        xml_layers = [e for e in canvas if is_element_tag(e, "layer")]
        if depth is None or depth <= 0 or not xml_layers:
            # Append at end (topmost)
            canvas.append(elem)
        else:
            # depth d means d positions below the top
            idx_from_end = min(depth, len(xml_layers))
            target_xml_elem = xml_layers[len(xml_layers) - idx_from_end]
            target_idx = canvas.index(target_xml_elem)
            canvas.insert(target_idx, elem)

        return layer

    def remove_layer(self, layer_id_or_desc: str, canvas_path: str = "") -> bool:
        """Remove a layer by desc or type."""
        layer = self.get_layer(layer_id_or_desc, canvas_path)
        if layer is None:
            return False
        canvas = self._resolve_canvas(canvas_path)
        canvas.remove(layer.element)
        return True

    def duplicate_layer(self, layer_id_or_desc: str, canvas_path: str = "") -> SifLayer | None:
        """Duplicate an existing layer, inserting it directly on top of the original."""
        orig = self.get_layer(layer_id_or_desc, canvas_path)
        if orig is None:
            return None

        canvas = self._resolve_canvas(canvas_path)
        new_elem = deepcopy(orig.element)
        orig_desc = orig.desc
        new_elem.set("desc", f"{orig_desc} Duplicate")

        orig_idx = canvas.index(orig.element)
        canvas.insert(orig_idx + 1, new_elem)
        return SifLayer(new_elem, canvas)

    def reorder_layer(self, layer_id_or_desc: str, new_depth: int, canvas_path: str = "") -> bool:
        """Move layer to a new depth (0 = topmost)."""
        layer = self.get_layer(layer_id_or_desc, canvas_path)
        if layer is None:
            return False

        canvas = self._resolve_canvas(canvas_path)
        canvas.remove(layer.element)

        xml_layers = [e for e in canvas if is_element_tag(e, "layer")]
        if new_depth <= 0 or not xml_layers:
            canvas.append(layer.element)
        else:
            idx_from_end = min(new_depth, len(xml_layers))
            target_xml_elem = xml_layers[len(xml_layers) - idx_from_end]
            target_idx = canvas.index(target_xml_elem)
            canvas.insert(target_idx, layer.element)

        return True

    def raise_layer(self, layer_id_or_desc: str, canvas_path: str = "") -> bool:
        """Raise layer by 1 position (closer to top, depth - 1)."""
        layer = self.get_layer(layer_id_or_desc, canvas_path)
        if layer is None:
            return False
        current_depth = layer.depth
        if current_depth <= 0:
            return False  # Already topmost
        return self.reorder_layer(layer_id_or_desc, current_depth - 1, canvas_path)

    def lower_layer(self, layer_id_or_desc: str, canvas_path: str = "") -> bool:
        """Lower layer by 1 position (closer to bottom, depth + 1)."""
        layer = self.get_layer(layer_id_or_desc, canvas_path)
        if layer is None:
            return False
        current_depth = layer.depth
        total = len(self.get_layers(canvas_path))
        if current_depth >= total - 1:
            return False  # Already bottom
        return self.reorder_layer(layer_id_or_desc, current_depth + 1, canvas_path)

    def group_layers(
        self,
        layer_ids: list[str],
        group_desc: str = "Group",
        canvas_path: str = "",
    ) -> SifLayer:
        """Group a set of layers into a PasteCanvas layer."""
        canvas = self._resolve_canvas(canvas_path)
        layers_to_group = [
            lyr
            for lyr in self.get_layers(canvas_path)
            if lyr.desc in layer_ids or lyr.type in layer_ids
        ]
        if not layers_to_group:
            raise ValueError("No matching layers found to group.")

        # Find depth of the topmost layer in the group
        min_depth = min(lyr.depth for lyr in layers_to_group)

        # Create PasteCanvas layer
        group_layer = self.add_layer(
            "PasteCanvas",
            canvas_path=canvas_path,
            desc=group_desc,
            depth=min_depth,
        )
        subcanvas = group_layer.get_subcanvas()
        if subcanvas is None:
            raise RuntimeError("Failed to initialize subcanvas for group layer.")

        # Move elements into subcanvas (preserving their XML relative order)
        for layer in reversed(layers_to_group):
            canvas.remove(layer.element)
            subcanvas.append(layer.element)

        return group_layer

    def ungroup_layer(self, layer_id_or_desc: str, canvas_path: str = "") -> list[str]:
        """Ungroup a PasteCanvas layer, moving its children up to the parent canvas."""
        layer = self.get_layer(layer_id_or_desc, canvas_path)
        if layer is None:
            raise ValueError(f"Layer '{layer_id_or_desc}' not found.")

        subcanvas = layer.get_subcanvas()
        if subcanvas is None:
            raise ValueError(f"Layer '{layer_id_or_desc}' is not a group/PasteCanvas layer.")

        canvas = self._resolve_canvas(canvas_path)
        layer_idx = canvas.index(layer.element)

        released_ids: list[str] = []
        child_layers = [e for e in subcanvas if is_element_tag(e, "layer")]
        for child in child_layers:
            subcanvas.remove(child)
            canvas.insert(layer_idx, child)
            layer_idx += 1
            released_ids.append(child.get("desc", child.get("type", "")))

        canvas.remove(layer.element)
        return released_ids

    def get_scene_tree(self, canvas_path: str = "") -> dict[str, Any]:
        """Build the full hierarchical layer scene tree matching MCP wire schema."""
        target_canvas = self._resolve_canvas(canvas_path)

        def _build_nodes(canvas_elem: etree._Element) -> list[dict[str, Any]]:
            nodes: list[dict[str, Any]] = []
            xml_layers = [e for e in canvas_elem if is_element_tag(e, "layer")]
            for elem in reversed(xml_layers):
                l_type = elem.get("type", "")
                l_desc = elem.get("desc", l_type)
                l_active = elem.get("active", "true").lower() == "true"
                sif_l = SifLayer(elem, canvas_elem)

                node: dict[str, Any] = {
                    "id": l_desc,
                    "type": l_type,
                    "description": l_desc,
                    "active": l_active,
                    "depth": sif_l.depth,
                    "params": sif_l.get_params(),
                }
                sub = sif_l.get_subcanvas()
                if sub is not None:
                    node["children"] = _build_nodes(sub)
                nodes.append(node)
            return nodes

        return {
            "canvas_path": canvas_path or "/",
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration_frames": int(round((self.end_time - self.start_time) * self.fps)),
            "layers": _build_nodes(target_canvas),
        }

    # -----------------------------------------------------------------------
    # Keyframe Operations
    # -----------------------------------------------------------------------

    def list_keyframes(self, canvas_path: str = "") -> list[dict[str, Any]]:
        """List all keyframes defined on the canvas."""
        canvas = self._resolve_canvas(canvas_path)
        keyframes: list[dict[str, Any]] = []
        for kf in canvas.findall("keyframe"):
            t_str = kf.get("time", "0s")
            active = kf.get("active", "true").lower() == "true"
            desc = kf.text or ""
            sec = parse_synfig_time(t_str, self.fps)
            keyframes.append(
                {
                    "time": sec,
                    "time_string": t_str,
                    "active": active,
                    "description": desc,
                }
            )
        return sorted(keyframes, key=lambda k: k["time"])

    def add_keyframe(
        self,
        time: float | str,
        desc: str = "",
        active: bool = True,
        canvas_path: str = "",
    ) -> dict[str, Any]:
        """Add a keyframe to the canvas."""
        canvas = self._resolve_canvas(canvas_path)
        sec = parse_synfig_time(str(time), self.fps) if isinstance(time, str) else float(time)
        t_str = format_synfig_time(sec, self.fps)

        # Check if keyframe at this time already exists
        for kf in canvas.findall("keyframe"):
            if parse_synfig_time(kf.get("time", ""), self.fps) == sec:
                kf.text = desc
                kf.set("active", "true" if active else "false")
                return {"time": sec, "time_string": t_str, "description": desc, "active": active}

        kf_elem = etree.Element("keyframe")
        kf_elem.set("time", t_str)
        kf_elem.set("active", "true" if active else "false")
        if desc:
            kf_elem.text = desc

        # Insert keyframes before any layer element
        layers = [e for e in canvas if is_element_tag(e, "layer")]
        if layers:
            idx = canvas.index(layers[0])
            canvas.insert(idx, kf_elem)
        else:
            canvas.append(kf_elem)

        return {"time": sec, "time_string": t_str, "description": desc, "active": active}

    def remove_keyframe(self, time: float | str, canvas_path: str = "") -> bool:
        """Remove a keyframe at the specified time."""
        canvas = self._resolve_canvas(canvas_path)
        sec = parse_synfig_time(str(time), self.fps) if isinstance(time, str) else float(time)
        for kf in canvas.findall("keyframe"):
            if abs(parse_synfig_time(kf.get("time", ""), self.fps) - sec) < 1e-4:
                canvas.remove(kf)
                return True
        return False
