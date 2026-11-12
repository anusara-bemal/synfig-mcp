"""Unit tests for the strict SIF value serialisers and ValueNode handling.

These tests pin the XML *shape* the Synfig loader expects (see
``synfig-core/src/synfig/loadcanvas.cpp`` and ``savecanvas.cpp``) and the
failure mode for values that cannot be represented.  Shape regressions here
produce documents the engine silently rejects, so every writer is covered.
"""

from __future__ import annotations

import math

import pytest
from lxml import etree

from synfig_mcp.errors import UnsupportedValueTypeError, ValidationError
from synfig_mcp.sif.parser import SifDocument, synfig_value_to_xml
from synfig_mcp.sif.valuenodes import build_valuenode_element


def _sif(layer_params: str = "") -> str:
    return (
        '<canvas version="1.2" width="480" height="270" fps="24.000">'
        "<name>Values</name>"
        '<layer type="circle" active="true" version="0.1" desc="c1">'
        f"{layer_params}"
        "</layer></canvas>"
    )


def _doc(layer_params: str = "") -> SifDocument:
    return SifDocument.from_string(_sif(layer_params))


def _find(elem: etree._Element, path: str) -> etree._Element:
    """Return a required descendant element, failing loudly when it is absent."""
    found = elem.find(path)
    assert found is not None, f"missing element: {path}"
    return found


def _attr(elem: etree._Element, name: str) -> str:
    """Return a required attribute value, failing loudly when it is absent."""
    value = elem.get(name)
    assert value is not None, f"missing attribute: {name}"
    return value


# ---------------------------------------------------------------------------
# synfig_value_to_xml
# ---------------------------------------------------------------------------


def test_real_round_trips_with_full_precision() -> None:
    """A real must parse back to the exact same double."""
    elem = synfig_value_to_xml({"type": "real", "value": 0.1 + 0.2})
    assert elem.tag == "real"
    assert float(_attr(elem, "value")) == 0.1 + 0.2


def test_integral_reals_have_no_trailing_zero() -> None:
    elem = synfig_value_to_xml({"type": "real", "value": 2.0})
    assert elem.get("value") == "2"


def test_non_finite_real_is_rejected() -> None:
    with pytest.raises(UnsupportedValueTypeError):
        synfig_value_to_xml({"type": "real", "value": math.inf})


def test_vector_uses_x_and_y_children() -> None:
    elem = synfig_value_to_xml({"type": "vector", "x": 1.25, "y": -3.5})
    assert elem.tag == "vector"
    assert elem.findtext("x") == "1.25"
    assert elem.findtext("y") == "-3.5"


def test_gradient_colour_stops() -> None:
    elem = synfig_value_to_xml(
        {
            "type": "gradient",
            "cpoints": [
                {"pos": 0.0, "color": {"r": 1.0, "g": 0.5, "b": 0.0, "a": 1.0}},
                {"pos": 1.0, "color": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}},
            ],
        }
    )
    assert elem.tag == "gradient"
    stops = elem.findall("color")
    assert [stop.get("pos") for stop in stops] == ["0", "1"]
    assert stops[0].findtext("g") == "0.5"


def test_bline_point_writes_t2_only_when_split() -> None:
    point = {
        "type": "bline_point",
        "vertex": (1.0, 2.0),
        "t1": (0.1, 0.2),
        "t2": (0.3, 0.4),
        "width": 0.75,
        "origin": 0.25,
    }
    unsplit = synfig_value_to_xml({**point, "split": False})
    assert unsplit.find("t2") is None, "t2 implies split tangents and must be conditional"
    assert _attr(_find(unsplit, "width/real"), "value") == "0.75"

    split = synfig_value_to_xml({**point, "split": True})
    assert _find(split, "t2/vector/x").text == "0.3"


def test_bline_point_list_is_a_dynamic_list_of_entries() -> None:
    elem = synfig_value_to_xml(
        {
            "type": "bline_point_list",
            "points": [
                {"vertex": (0.0, 0.0), "t1": (0.0, 0.0)},
                {"vertex": (1.0, 0.0), "t1": (0.0, 0.0)},
            ],
        }
    )
    assert elem.tag == "bline"
    assert elem.get("type") == "bline_point"
    assert len(elem.findall("entry")) == 2
    assert elem.findall("entry")[0].find("bline_point") is not None


def test_bone_writes_linkable_fields() -> None:
    elem = synfig_value_to_xml(
        {
            "type": "bone",
            "name": "upper_arm",
            "origin": (1.0, 2.0),
            "angle": 45.0,
            "scalelx": 2.0,
            "width": 0.5,
            "tipwidth": 0.25,
        }
    )
    assert elem.tag == "bone"
    assert elem.get("type") == "bone_object"
    assert elem.findtext("name/string") == "upper_arm"
    assert _find(elem, "origin/vector/x").text == "1"
    assert _attr(_find(elem, "angle/angle"), "value") == "45"
    assert _attr(_find(elem, "scalelx/real"), "value") == "2"


def test_plain_list_uses_value_children() -> None:
    elem = synfig_value_to_xml({"type": "list", "entries": [{"type": "real", "value": 1.0}]})
    assert elem.tag == "list"
    assert _attr(_find(elem, "value/real"), "value") == "1"


def test_static_list_requires_an_element_type() -> None:
    with pytest.raises(UnsupportedValueTypeError):
        synfig_value_to_xml({"type": "static_list", "entries": []})

    elem = synfig_value_to_xml({"type": "static_list", "value_type": "real", "entries": [1.0, 2.0]})
    assert elem.tag == "static_list"
    assert elem.get("type") == "real"
    assert len(elem.findall("entry")) == 2


def test_width_point_list_is_a_dynamic_list() -> None:
    elem = synfig_value_to_xml(
        {
            "type": "wplist",
            "entries": [
                {
                    "position": 0.5,
                    "width": 2.0,
                    "side_before": 1,
                    "side_after": 2,
                }
            ],
        }
    )
    assert elem.tag == "wplist"
    assert elem.get("type") == "width_point"
    width_point = _find(elem, "entry/width_point")
    assert _attr(_find(width_point, "position/real"), "value") == "0.5"
    assert _attr(_find(width_point, "side_before/integer"), "value") == "1"


def test_dash_item_list_is_a_dynamic_list() -> None:
    elem = synfig_value_to_xml(
        {
            "type": "dilist",
            "entries": [{"offset": 0.0, "length": 0.25, "side_before": 3}],
        }
    )
    assert elem.tag == "dilist"
    assert elem.get("type") == "dash_item"
    assert _attr(_find(elem, "entry/dash_item/length/real"), "value") == "0.25"


def test_unknown_value_type_raises_instead_of_stringifying() -> None:
    with pytest.raises(UnsupportedValueTypeError) as excinfo:
        synfig_value_to_xml({"type": "mystery", "value": 1})
    assert "mystery" in str(excinfo.value)
    assert excinfo.value.code == 1204


def test_valuenode_link_is_not_a_value_element() -> None:
    with pytest.raises(UnsupportedValueTypeError):
        synfig_value_to_xml({"type": "valuenode_link", "link_id": "shared"})


# ---------------------------------------------------------------------------
# ValueNode factories
# ---------------------------------------------------------------------------


def _value(tag: str, value: str) -> etree._Element:
    elem = etree.Element(tag)
    elem.set("value", value)
    return elem


def test_linear_matches_the_upstream_link_layout() -> None:
    node = build_valuenode_element("linear", "real", _value("real", "2.5"))
    assert node.tag == "linear"
    assert node.get("type") == "real"
    assert _attr(_find(node, "slope/real"), "value") == "0"
    assert _attr(_find(node, "offset/real"), "value") == "2.5"


def test_composite_of_color_uses_colour_channels() -> None:
    source = etree.Element("color")
    for channel, value in (("r", "0.5"), ("g", "0.25"), ("b", "0"), ("a", "1")):
        child = etree.SubElement(source, channel)
        child.text = value

    node = build_valuenode_element("composite", "color", source)
    assert node.tag == "composite"
    assert node.get("type") == "color"
    assert _attr(_find(node, "red/real"), "value") == "0.5"
    assert _attr(_find(node, "green/real"), "value") == "0.25"
    assert _attr(_find(node, "alpha/real"), "value") == "1"


def test_composite_of_real_is_rejected() -> None:
    with pytest.raises(UnsupportedValueTypeError):
        build_valuenode_element("composite", "real", _value("real", "1"))


def test_unknown_valuenode_is_rejected() -> None:
    with pytest.raises(UnsupportedValueTypeError):
        build_valuenode_element("not_a_valuenode", "real", _value("real", "1"))


# ---------------------------------------------------------------------------
# export_param / link_param / convert_param
# ---------------------------------------------------------------------------


def test_export_param_writes_defs_and_use_reference() -> None:
    doc = _doc('<param name="radius"><real value="1.5"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None

    layer.export_param("radius", "sharedRadius", layer.parent_canvas)

    defs = _find(doc.root, "defs")
    exported = _find(defs, "real")
    assert _attr(exported, "id") == "sharedRadius"
    assert _attr(exported, "value") == "1.5"

    param = _find(layer.element, "param[@name='radius']")
    assert _attr(param, "use") == "sharedRadius"
    assert len(param) == 0, "an exported parameter must not keep an inline value"

    # <defs> must precede the layers for the loader to resolve the reference.
    children = [etree.QName(child).localname for child in doc.root]
    assert children.index("defs") < children.index("layer")


def test_export_param_rejects_duplicate_ids() -> None:
    doc = _doc('<param name="radius"><real value="1.5"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    layer.export_param("radius", "shared", layer.parent_canvas)

    other = _doc('<param name="radius"><real value="2.5"/></param>')
    other_layer = other.get_layer("c1")
    assert other_layer is not None
    other_layer.export_param("radius", "shared", other_layer.parent_canvas)

    with pytest.raises(ValidationError):
        other_layer.export_param("radius", "shared", other_layer.parent_canvas)


def test_export_param_rejects_empty_or_illegal_names() -> None:
    doc = _doc('<param name="radius"><real value="1"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    for bad in ("", "   ", "bad<name>", " leading"):
        with pytest.raises(ValidationError):
            layer.export_param("radius", bad, layer.parent_canvas)


def test_link_param_requires_an_exported_node() -> None:
    doc = _doc('<param name="radius"><real value="1"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    with pytest.raises(ValidationError):
        layer.link_param("radius", "missing")


def test_set_param_detaches_an_exported_link() -> None:
    doc = _doc('<param name="radius"><real value="1"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    layer.export_param("radius", "shared", layer.parent_canvas)
    layer.set_param("radius", {"type": "real", "value": 3.0})

    param = _find(layer.element, "param[@name='radius']")
    assert param.get("use") is None
    assert _attr(_find(param, "real"), "value") == "3"


def test_convert_param_linear_keeps_the_value() -> None:
    doc = _doc('<param name="radius"><real value="1.25"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    layer.convert_param("radius", "linear")

    node = _find(layer.element, "param[@name='radius']/linear")
    assert node.get("type") == "real"
    assert _attr(_find(node, "offset/real"), "value") == "1.25"


def test_convert_param_composite_color() -> None:
    doc = _doc('<param name="color"><color><r>0.5</r><g>0.25</g><b>0</b><a>1</a></color></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    layer.convert_param("color", "composite")

    node = _find(layer.element, "param[@name='color']/composite")
    assert _attr(_find(node, "red/real"), "value") == "0.5"


def test_convert_param_rejects_unknown_valuenode() -> None:
    doc = _doc('<param name="radius"><real value="1"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    with pytest.raises(UnsupportedValueTypeError):
        layer.convert_param("radius", "not_a_valuenode")


def test_convert_param_rejects_an_exported_parameter() -> None:
    doc = _doc('<param name="radius"><real value="1"/></param>')
    layer = doc.get_layer("c1")
    assert layer is not None
    layer.export_param("radius", "shared", layer.parent_canvas)
    with pytest.raises(ValidationError):
        layer.convert_param("radius", "linear")


def test_complex_values_are_not_silently_downgraded() -> None:
    doc = _doc(
        '<param name="bline"><bline type="bline_point">'
        "<entry><bline_point><vertex><vector><x>0</x><y>0</y></vector></vertex>"
        "<t1><vector><x>0</x><y>0</y></vector></t1></bline_point></entry>"
        "</bline></param>"
    )
    layer = doc.get_layer("c1")
    assert layer is not None
    with pytest.raises(UnsupportedValueTypeError):
        layer.convert_param("bline", "linear")
