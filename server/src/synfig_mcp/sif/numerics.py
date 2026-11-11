"""
Numeric and primitive-element serialisation shared by the SIF writers.

Synfig parses every number in a document with ``strtod`` and stores the result
as an IEEE-754 double.  Formatting a value with a fixed amount of decimals
therefore loses information: a value written as ``0.500000`` is not the same
double as ``0.1 + 0.4``, and animation keys drift after a round-trip.  The
helpers in this module always emit the shortest representation that parses
back to the identical double (``repr``), which keeps documents lossless and
matches what ``savecanvas.cpp`` produces closely enough that Synfig accepts
either form.

This module deliberately has no dependency on the parser, the protocol models
or the ValueNode registry so both ``parser`` and ``valuenodes`` can import it
without creating a cycle.
"""

from __future__ import annotations

import math

from lxml import etree

from synfig_mcp.errors import UnsupportedValueTypeError


def format_real(value: float) -> str:
    """Serialise a real number with full double precision.

    ``repr`` is the shortest string that round-trips to the same IEEE-754
    double, so no precision is lost.  Integral values are written without a
    trailing ``.0`` (Synfig accepts both, and the shorter form keeps files
    compact).  Non-finite values are rejected: ``inf`` and ``nan`` cannot be
    represented in a SIF document and would silently corrupt the canvas.
    """
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise UnsupportedValueTypeError(
            f"Cannot serialise {value!r} as a Synfig real value.",
            details={"value": repr(value)},
        ) from exc

    if not math.isfinite(number):
        raise UnsupportedValueTypeError(
            "Cannot serialise a non-finite real value into a SIF document.",
            details={"value": str(number)},
        )
    if number == 0.0:
        return "0"
    if number.is_integer() and abs(number) < 1e16:
        return str(int(number))
    return repr(number)


def format_time(seconds: float) -> str:
    """Serialise a time in seconds using Synfig's ``<number>s`` syntax."""
    return f"{format_real(seconds)}s"


def real_element(value: float, tag: str = "real") -> etree._Element:
    """Build ``<real value="…"/>`` (or an ``<angle value="…"/>``) losslessly."""
    elem = etree.Element(tag)
    elem.set("value", format_real(value))
    return elem


def integer_element(value: int) -> etree._Element:
    """Build ``<integer value="…"/>``."""
    elem = etree.Element("integer")
    elem.set("value", str(int(value)))
    return elem


def bool_element(value: bool) -> etree._Element:
    """Build ``<bool value="true|false"/>``."""
    elem = etree.Element("bool")
    elem.set("value", "true" if value else "false")
    return elem


def string_element(value: str) -> etree._Element:
    """Build ``<string>…</string>``."""
    elem = etree.Element("string")
    elem.text = value
    return elem


def vector_element(x: float, y: float, tag: str = "vector") -> etree._Element:
    """Build ``<vector><x/><y/></vector>`` with lossless precision."""
    elem = etree.Element(tag)
    x_el = etree.SubElement(elem, "x")
    x_el.text = format_real(x)
    y_el = etree.SubElement(elem, "y")
    y_el.text = format_real(y)
    return elem


def color_element(r: float, g: float, b: float, a: float) -> etree._Element:
    """Build ``<color><r/><g/><b/><a/></color>`` with lossless precision."""
    elem = etree.Element("color")
    for channel, channel_value in (("r", r), ("g", g), ("b", b), ("a", a)):
        channel_el = etree.SubElement(elem, channel)
        channel_el.text = format_real(channel_value)
    return elem
