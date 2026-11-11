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

from dataclasses import dataclass

from lxml import etree

from synfig_mcp.errors import SynfigError

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
    elem = etree.Element("real")
    elem.set("value", f"{float(value):.10f}")
    return elem


def _integer(value: int) -> etree._Element:
    elem = etree.Element("integer")
    elem.set("value", str(int(value)))
    return elem


def _bool(value: bool) -> etree._Element:
    elem = etree.Element("bool")
    elem.set("value", "true" if value else "false")
    return elem


def _string(value: str) -> etree._Element:
    elem = etree.Element("string")
    elem.text = str(value)
    return elem


def _angle(degrees: float) -> etree._Element:
    elem = etree.Element("angle")
    elem.set("value", f"{float(degrees):.6f}")
    return elem


def _time(seconds: float) -> etree._Element:
    elem = etree.Element("time")
    elem.set("value", f"{float(seconds):.4f}s")
    return elem


def _vector(x: float, y: float) -> etree._Element:
    elem = etree.Element("vector")
    x_el = etree.SubElement(elem, "x")
    x_el.text = f"{float(x):.10f}"
    y_el = etree.SubElement(elem, "y")
    y_el.text = f"{float(y):.10f}"
    return elem


def _color(r: float, g: float, b: float, a: float) -> etree._Element:
    elem = etree.Element("color")
    for channel, value in (("r", r), ("g", g), ("b", b), ("a", a)):
        ch = etree.SubElement(elem, channel)
        ch.text = f"{float(value):.6f}"
    return elem


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
}

#: Composite ValueNodes use a different link layout per value type.
#: The Synfig engine only accepts composite for these value types
#: (``ValueNode_Composite::check_type``); numeric parameters use the
#: ``add``/``subtract``/``scale`` nodes instead.  Vector and color composites
#: are built from the *components* of the source value (real numbers).
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
            raise SynfigError(
                f"The Composite ValueNode does not accept '{value_type}' parameters in "
                f"Synfig. Use 'add', 'subtract' or 'scale' for numeric parameters "
                f"(composite supports: {', '.join(sorted(COMPOSITE_LINK_SPECS))})."
            )
    else:
        node_spec = VALUENODE_SPECS.get(name)
        if node_spec is None:
            raise SynfigError(
                f"Unsupported ValueNode conversion type '{valuenode_type}'. "
                f"Supported types: {', '.join(supported_conversions())}."
            )
        if not node_spec.supports(value_type):
            raise SynfigError(
                f"The '{name}' ValueNode does not accept '{value_type}' parameters in "
                f"Synfig (accepted: {', '.join(sorted(node_spec.value_types))})."
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
        else:
            child.append(_default_for(link_type, value_type))

    return element


def _seed_element(source: etree._Element, spec: LinkSpec, link_type: str) -> etree._Element:
    """Build the seed value for one link of a converted ValueNode."""
    if spec.component is not None:
        component = source.find(spec.component)
        if component is not None and component.text:
            return _real(float(component.text))
        return _real(0.0)
    source_tag = etree.QName(str(source.tag)).localname if isinstance(source.tag, str) else ""
    if source_tag == "animated":
        # An animated parameter keeps its animation when it is converted: the
        # <animated> element is a valid value node on its own.
        if source.get("type") == link_type:
            return etree.fromstring(etree.tostring(source))
        return _default_for(link_type, link_type)
    if value_type_of(source) == link_type:
        clone = etree.fromstring(etree.tostring(source))
        return clone
    return _default_for(link_type, link_type)
