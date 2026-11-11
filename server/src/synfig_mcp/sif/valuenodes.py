"""
Synfig ValueNode and interpolation helpers.

This module encodes the *exact* XML shapes that the Synfig engine accepts for
linkable ValueNodes (the ``<linear>``, ``<add>``, ``<composite>`` ... family)
and the legal waypoint interpolation names.

The shapes were derived from the Synfig sources (``synfig-core/src/synfig/
loadcanvas.cpp`` for the loader, ``savecanvas.cpp`` for the writer and
``valuenodes/valuenode_*.cpp`` for the individual link names) and are verified
by the round-trip contract gate in
``server/tests/contract/test_sif_synfig_validity.py`` which loads every
generated document with the real ``synfig`` binary.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from lxml import etree

from synfig_mcp.errors import SynfigError, UnsupportedValueTypeError
from synfig_mcp.sif.numerics import (
    bool_element,
    color_element,
    format_time,
    integer_element,
    real_element,
    string_element,
    vector_element,
)

# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

#: Interpolation modes accepted by ``CanvasParser::parse_interpolation``.
VALID_INTERPOLATIONS: frozenset[str] = frozenset(
    {"linear", "constant", "halt", "clamped", "auto", "manual"}
)

#: Historic names that are still accepted by the MCP for compatibility.
LEGACY_INTERPOLATION_ALIASES: dict[str, str] = {"tcb": "auto"}


def normalize_interpolation(value: str | None, *, default: str = "linear") -> str:
    """
    Validate and normalise a waypoint interpolation mode.

    Raises:
        SynfigError: if the mode is not one Synfig understands.  Writing an
            unknown mode produces a document the engine refuses to load, so it
            must never reach the writer.
    """
    if value is None or not str(value).strip():
        value = default
    normalized = str(value).strip().lower()
    normalized = LEGACY_INTERPOLATION_ALIASES.get(normalized, normalized)
    if normalized not in VALID_INTERPOLATIONS:
        raise SynfigError(
            f"Invalid interpolation '{value}'. Valid modes: "
            f"{', '.join(sorted(VALID_INTERPOLATIONS))}."
        )
    return normalized


# ---------------------------------------------------------------------------
# Value element helpers
# ---------------------------------------------------------------------------

#: Mapping of Synfig value element names to their canonical value type name.
VALUE_ELEMENT_TYPES: dict[str, str] = {
    "real": "real",
    "integer": "integer",
    "bool": "bool",
    "string": "string",
    "angle": "angle",
    "time": "time",
    "vector": "vector",
    "color": "color",
    "gradient": "gradient",
    "bline": "bline_point_list",
    "wplist": "width_point_list",
    "dilist": "dash_item_list",
    "bones": "bone_list",
    "list": "list",
}


def value_type_of(element: etree._Element) -> str:
    """Return the canonical value type name of a ``<param>`` child element."""
    tag = etree.QName(element.tag).localname if isinstance(element.tag, str) else ""
    return VALUE_ELEMENT_TYPES.get(tag, tag or "unknown")


def _real(value: float) -> etree._Element:
    return real_element(value)


def _integer(value: int) -> etree._Element:
    return integer_element(value)


def _bool(value: bool) -> etree._Element:
    return bool_element(value)


def _string(value: str) -> etree._Element:
    return string_element(value)


def _angle(degrees: float) -> etree._Element:
    return real_element(degrees, tag="angle")


def _time(seconds: float) -> etree._Element:
    elem = etree.Element("time")
    elem.set("value", format_time(seconds))
    return elem


def _vector(x: float, y: float) -> etree._Element:
    return vector_element(x, y)


def _color(r: float, g: float, b: float, a: float) -> etree._Element:
    return color_element(r, g, b, a)


def _default_value(type_name: str, value: float | int | bool) -> etree._Element:
    """Build a link element with an explicit default value."""
    if type_name == "integer":
        return _integer(int(value))
    if type_name == "bool":
        return _bool(bool(value))
    if type_name == "angle":
        return _angle(float(value))
    if type_name == "time":
        return _time(float(value))
    if type_name == "string":
        return _string(str(value))
    return _real(float(value))


def _default_for(type_name: str, value_type: str) -> etree._Element:
    """Build a neutral default value element for ``type_name``."""
    if type_name == "real":
        return _real(0.0)
    if type_name == "angle":
        return _angle(0.0)
    if type_name == "time":
        return _time(0.0)
    if type_name == "integer":
        return _integer(0)
    if type_name == "bool":
        return _bool(False)
    if type_name == "string":
        return _string("")
    if type_name == "vector":
        return _vector(0.0, 0.0)
    if type_name == "color":
        return _color(0.0, 0.0, 0.0, 1.0)
    if type_name == "gradient":
        elem = etree.Element("gradient")
        return elem
    if value_type == "real":
        return _real(0.0)
    if value_type == "angle":
        return _angle(0.0)
    if value_type == "time":
        return _time(0.0)
    if value_type == "integer":
        return _integer(0)
    if value_type == "bool":
        return _bool(False)
    if value_type == "string":
        return _string("")
    if value_type == "vector":
        return _vector(0.0, 0.0)
    if value_type == "color":
        return _color(0.0, 0.0, 0.0, 1.0)
    return _real(0.0)


# ---------------------------------------------------------------------------
# Linkable ValueNode definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LinkSpec:
    """Description of one link (child element) of a linkable ValueNode."""

    name: str
    #: ``same`` means the link has the same value type as the ValueNode.
    type: str
    #: Optional seed value used when the converted parameter already has a value.
    carries_value: bool = False
    #: Optional component of the source value feeding this link
    #: (``x``/``y`` for vectors, ``r``/``g``/``b``/``a`` for colors).
    component: str | None = None
    #: Default value of the link.  Zero is not always valid - a modulo node
    #: with a zero divisor crashes the Synfig loader.
    default: float | int | bool | None = None


@dataclass(frozen=True, slots=True)
class ValueNodeSpec:
    """A linkable ValueNode the headless backend can create."""

    name: str
    links: tuple[LinkSpec, ...]
    #: Value types the Synfig engine accepts for this ValueNode.
    value_types: frozenset[str]

    def supports(self, value_type: str) -> bool:
        return value_type.lower() in self.value_types


#: Value types of the Synfig engine, as used by the value nodes.
_REAL = "real"
_ANGLE = "angle"
_COLOR = "color"
_INTEGER = "integer"
_TIME = "time"
_VECTOR = "vector"
_GRADIENT = "gradient"
_STRING = "string"
_BOOL = "bool"

_NUMERIC = frozenset({_REAL, _ANGLE, _INTEGER, _TIME})
_MIXED = frozenset({_REAL, _ANGLE, _COLOR, _INTEGER, _TIME, _VECTOR})

#: Link layout of every linkable ValueNode the headless backend can create.
#:
#: The names, the links and the accepted value types mirror the upstream
#: implementation (``valuenodes/valuenode_*.cpp``).  The engine rejects
#: unknown ValueNode names and unsupported value types, so both are checked
#: before anything is written.
VALUENODE_SPECS: dict[str, ValueNodeSpec] = {
    "linear": ValueNodeSpec(
        "linear",
        (LinkSpec("slope", "same"), LinkSpec("offset", "same", True)),
        _MIXED,
    ),
    "add": ValueNodeSpec(
        "add",
        (
            LinkSpec("lhs", "same", True),
            LinkSpec("rhs", "same"),
            LinkSpec("scalar", _REAL),
        ),
        frozenset({_REAL, _ANGLE, _COLOR, _INTEGER, _TIME, _VECTOR, _GRADIENT}),
    ),
    "subtract": ValueNodeSpec(
        "subtract",
        (
            LinkSpec("lhs", "same", True),
            LinkSpec("rhs", "same"),
            LinkSpec("scalar", _REAL),
        ),
        frozenset({_REAL, _ANGLE, _COLOR, _INTEGER, _TIME, _VECTOR, _GRADIENT}),
    ),
    "scale": ValueNodeSpec(
        "scale",
        (LinkSpec("link", "same", True), LinkSpec("scalar", _REAL)),
        _MIXED,
    ),
    "absolute": ValueNodeSpec(
        "absolute",
        (LinkSpec("link", "same", True),),
        frozenset({_REAL, _ANGLE, _INTEGER}),
    ),
    "duplicate": ValueNodeSpec(
        "duplicate",
        (
            LinkSpec("from", _REAL),
            LinkSpec("to", _REAL, True),
            LinkSpec("step", _REAL),
        ),
        frozenset({_REAL}),
    ),
    "step": ValueNodeSpec(
        "step",
        (
            LinkSpec("link", "same", True),
            LinkSpec("duration", _TIME),
            LinkSpec("start_time", _TIME),
            LinkSpec("intersection", _REAL),
        ),
        _MIXED,
    ),
    "range": ValueNodeSpec(
        "range",
        (
            LinkSpec("min", "same"),
            LinkSpec("max", "same"),
            LinkSpec("link", "same", True),
        ),
        _NUMERIC,
    ),
    "sine": ValueNodeSpec(
        "sine",
        (LinkSpec("angle", _ANGLE), LinkSpec("amp", _REAL, True)),
        frozenset({_REAL}),
    ),
    "cos": ValueNodeSpec(
        "cos",
        (LinkSpec("angle", _ANGLE), LinkSpec("amp", _REAL, True)),
        frozenset({_REAL}),
    ),
    "timeloop": ValueNodeSpec(
        "timeloop",
        (
            LinkSpec("link", "same", True),
            LinkSpec("link_time", _TIME),
            LinkSpec("local_time", _TIME),
            LinkSpec("duration", _TIME),
        ),
        _MIXED,
    ),
    "timed_swap": ValueNodeSpec(
        "timed_swap",
        (
            LinkSpec("before", "same", True),
            LinkSpec("after", "same"),
            LinkSpec("time", _TIME),
            LinkSpec("length", _TIME),
        ),
        _MIXED,
    ),
    "reciprocal": ValueNodeSpec(
        "reciprocal",
        (
            LinkSpec("link", _REAL, True),
            LinkSpec("epsilon", _REAL, default=0.000001),
            LinkSpec("infinite", _REAL, default=1000000000.0),
        ),
        frozenset({_REAL}),
    ),
    "derivative": ValueNodeSpec(
        "derivative",
        (
            LinkSpec("link", "same", True),
            LinkSpec("order", _INTEGER, default=1),
            LinkSpec("accuracy", _INTEGER, default=1),
            LinkSpec("interval", _REAL, default=1.0),
        ),
        frozenset({_REAL, _ANGLE, _TIME, _VECTOR}),
    ),
    "reverse": ValueNodeSpec(
        "reverse",
        (LinkSpec("link", "same", True),),
        frozenset({_STRING, _GRADIENT}),
    ),
    "vectorlength": ValueNodeSpec(
        "vectorlength",
        (LinkSpec("vector", _VECTOR),),
        frozenset({_REAL}),
    ),
    "vectorangle": ValueNodeSpec(
        "vectorangle",
        (LinkSpec("vector", _VECTOR),),
        frozenset({_ANGLE}),
    ),
    "vectorx": ValueNodeSpec(
        "vectorx",
        (LinkSpec("vector", _VECTOR),),
        frozenset({_REAL}),
    ),
    "vectory": ValueNodeSpec(
        "vectory",
        (LinkSpec("vector", _VECTOR),),
        frozenset({_REAL}),
    ),
    "exp": ValueNodeSpec(
        "exp",
        (LinkSpec("exp", _REAL, True), LinkSpec("scale", _REAL)),
        frozenset({_REAL}),
    ),
    "logarithm": ValueNodeSpec(
        "logarithm",
        (
            LinkSpec("link", _REAL, True),
            LinkSpec("epsilon", _REAL, default=0.000001),
            LinkSpec("infinite", _REAL, default=1000000000.0),
        ),
        frozenset({_REAL}),
    ),
    "modulo": ValueNodeSpec(
        "modulo",
        (
            LinkSpec("link", "same", True),
            LinkSpec("divisor", _INTEGER, default=2),
            LinkSpec("scalar", _REAL, default=1.0),
        ),
        frozenset({_REAL, _ANGLE, _INTEGER, _TIME}),
    ),
    "atan2": ValueNodeSpec(
        "atan2",
        (LinkSpec("y", _REAL, True), LinkSpec("x", _REAL)),
        frozenset({_ANGLE}),
    ),
    "gradient_rotate": ValueNodeSpec(
        "gradient_rotate",
        (LinkSpec("gradient", _GRADIENT, True), LinkSpec("offset", _REAL)),
        frozenset({_GRADIENT}),
    ),
    "map_range": ValueNodeSpec(
        "map_range",
        (
            LinkSpec("link", "same", True),
            LinkSpec("from_min", _REAL),
            LinkSpec("from_max", _REAL),
            LinkSpec("to_min", _REAL),
            LinkSpec("to_max", _REAL),
            LinkSpec("clamp", _BOOL),
            LinkSpec("interpolation", _INTEGER),
        ),
        _NUMERIC,
    ),
    "stripes": ValueNodeSpec(
        "stripes",
        (
            LinkSpec("color1", _COLOR),
            LinkSpec("color2", _COLOR),
            LinkSpec("stripes", _INTEGER),
            LinkSpec("width", _REAL),
        ),
        frozenset({_GRADIENT}),
    ),
    "twotone": ValueNodeSpec(
        "twotone",
        (LinkSpec("color1", _COLOR), LinkSpec("color2", _COLOR)),
        frozenset({_GRADIENT}),
    ),
}

#: Composite ValueNodes use a different link layout per value type.
#: The Synfig engine only accepts composite for the structured types listed by
#: ``ValueNode_Composite::check_type`` (``valuenodes/valuenode_composite.cpp``);
#: numeric parameters use ``add``/``subtract``/``scale`` instead.  Vector and
#: colour composites are built from the *components* of the source value (real
#: numbers), the others from component value elements.
COMPOSITE_LINK_SPECS: dict[str, tuple[LinkSpec, ...]] = {
    "vector": (
        LinkSpec("x", _REAL, True, "x"),
        LinkSpec("y", _REAL, True, "y"),
    ),
    "color": (
        LinkSpec("red", _REAL, True, "r"),
        LinkSpec("green", _REAL, True, "g"),
        LinkSpec("blue", _REAL, True, "b"),
        LinkSpec("alpha", _REAL, True, "a"),
    ),
    "segment": (
        LinkSpec("p1", _VECTOR, True, "p1"),
        LinkSpec("t1", _VECTOR, True, "t1"),
        LinkSpec("p2", _VECTOR, True, "p2"),
        LinkSpec("t2", _VECTOR, True, "t2"),
    ),
    "bline_point": (
        LinkSpec("point", _VECTOR, True, "vertex"),
        LinkSpec("width", _REAL, True, "width"),
        LinkSpec("origin", _REAL, True, "origin"),
        LinkSpec("split", _BOOL, True, "split"),
        LinkSpec("split_radius", _BOOL, True, "split_radius"),
        LinkSpec("split_angle", _BOOL, True, "split_angle"),
        LinkSpec("t1", _VECTOR, True, "t1"),
        LinkSpec("t2", _VECTOR, True, "t2"),
    ),
    "width_point": (
        LinkSpec("position", _REAL, True, "position"),
        LinkSpec("width", _REAL, True, "width"),
        LinkSpec("side_before", _INTEGER, True, "side_before"),
        LinkSpec("side_after", _INTEGER, True, "side_after"),
        LinkSpec("lower_bound", _REAL, True, "lower_bound", default=0.0),
        LinkSpec("upper_bound", _REAL, True, "upper_bound", default=1.0),
    ),
    "dash_item": (
        LinkSpec("offset", _REAL, True, "offset"),
        LinkSpec("length", _REAL, True, "length"),
        LinkSpec("side_before", _INTEGER, True, "side_before"),
        LinkSpec("side_after", _INTEGER, True, "side_after"),
    ),
    "transformation": (
        LinkSpec("offset", _VECTOR, True, "offset"),
        LinkSpec("angle", _ANGLE, True, "angle"),
        LinkSpec("skew_angle", _ANGLE, True, "skew_angle"),
        LinkSpec("scale", _VECTOR, True, "scale"),
    ),
}


def supported_conversions() -> list[str]:
    """Return the ValueNode types the headless backend can convert to."""
    return sorted({*VALUENODE_SPECS.keys(), "composite"})


def build_valuenode_element(
    valuenode_type: str,
    value_type: str,
    value_element: etree._Element | None = None,
) -> etree._Element:
    """
    Build a Synfig-valid linkable ValueNode element.

    Args:
        valuenode_type: ValueNode name, e.g. ``linear`` or ``composite``.
        value_type: canonical value type of the parameter being converted.
        value_element: the current value element, used to seed the primary
            link so the converted parameter keeps its value.

    Raises:
        SynfigError: when the conversion is not supported, or when Synfig does
            not accept the value type for that ValueNode.
    """
    name = valuenode_type.strip().lower()
    if name == "composite":
        specs = COMPOSITE_LINK_SPECS.get(value_type)
        if specs is None:
            raise UnsupportedValueTypeError(
                f"The Composite ValueNode does not accept '{value_type}' parameters in "
                f"Synfig. Use 'add', 'subtract' or 'scale' for numeric parameters "
                f"(composite supports: {', '.join(sorted(COMPOSITE_LINK_SPECS))}).",
                details={"valuenode": name, "value_type": value_type},
            )
    else:
        node_spec = VALUENODE_SPECS.get(name)
        if node_spec is None:
            raise UnsupportedValueTypeError(
                f"Unsupported ValueNode conversion type '{valuenode_type}'. "
                f"Supported types: {', '.join(supported_conversions())}.",
                details={"valuenode": valuenode_type},
            )
        if not node_spec.supports(value_type):
            raise UnsupportedValueTypeError(
                f"The '{name}' ValueNode does not accept '{value_type}' parameters in "
                f"Synfig (accepted: {', '.join(sorted(node_spec.value_types))}).",
                details={
                    "valuenode": name,
                    "value_type": value_type,
                    "accepted": sorted(node_spec.value_types),
                },
            )
        specs = node_spec.links

    element = etree.Element(name)
    element.set("type", value_type)

    seed: etree._Element | None = None
    if value_element is not None and value_type_of(value_element) == value_type:
        seed = value_element

    for link in specs:
        child = etree.SubElement(element, link.name)
        link_type = value_type if link.type == "same" else link.type
        if link.carries_value and seed is not None:
            child.append(_seed_element(seed, link, link_type))
        elif link.default is not None:
            child.append(_default_value(link_type, link.default))
        else:
            child.append(_default_for(link_type, value_type))

    return element


def _seed_element(source: etree._Element, spec: LinkSpec, link_type: str) -> etree._Element:
    """Build the seed value for one link of a converted ValueNode."""
    if spec.component is not None:
        component = source.find(spec.component)
        if component is not None and isinstance(component.tag, str):
            return _component_element(component, link_type)
        if spec.default is not None:
            return _default_value(link_type, spec.default)
        return _default_for(link_type, link_type)
    source_tag = etree.QName(str(source.tag)).localname if isinstance(source.tag, str) else ""
    if source_tag == "animated":
        # An animated parameter keeps its animation when it is converted: the
        # <animated> element is a valid value node on its own.
        if source.get("type") == link_type:
            return deepcopy(source)
        return _default_for(link_type, link_type)
    if value_type_of(source) == link_type:
        return deepcopy(source)
    return _default_for(link_type, link_type)


def _component_element(component: etree._Element, link_type: str) -> etree._Element:
    """Seed a composite link from a component of the source value element.

    Components are either nested value elements (``<vertex><vector>…</vector>
    </vertex>``) or bare numbers (``<x>1.0</x>``).  The correct element is
    produced for both shapes; a component that does not match the link type
    falls back to the neutral default instead of emitting a mistyped link.
    """
    nested = next((child for child in component if isinstance(child.tag, str)), None)
    if nested is not None:
        if value_type_of(nested) == link_type:
            return deepcopy(nested)
        if link_type == "bline_point_list" and value_type_of(nested) == "bline":
            return deepcopy(nested)
        return _default_for(link_type, link_type)

    text = (component.text or "").strip()
    if not text:
        return _default_for(link_type, link_type)
    if link_type == "integer":
        return _integer(int(float(text)))
    if link_type == "bool":
        return _bool(text.lower() in ("true", "1"))
    if link_type == "string":
        return _string(component.text or "")
    if link_type == "angle":
        return _angle(float(text))
    if link_type == "time":
        return _time(float(text))
    if link_type == "real":
        return _real(float(text))
    return _default_for(link_type, link_type)
