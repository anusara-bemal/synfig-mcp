# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for the typed parameter codec."""

from __future__ import annotations

import pytest
from lxml import etree

from synfig_mcp.document.params import (
    _fmt,
    _stringify,
    decode_animated,
    decode_bline,
    decode_color,
    decode_gradient,
    decode_param,
    decode_value,
    decode_vector,
    encode_bline,
    encode_color,
    encode_gradient,
    encode_param,
    encode_value,
    encode_vector,
    encode_vector_list,
    format_color_hex,
    make_element,
    param_value_type,
    parse_color_text,
    qn,
)
from synfig_mcp.errors import ParameterError


class TestColor:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("#f00", (1.0, 0.0, 0.0, 1.0)),
            ("#00ff00", (0.0, 1.0, 0.0, 1.0)),
            ("#0000ff80", (0.0, 0.0, 1.0, 128 / 255)),
            ("#abcd", (0xAA / 255, 0xBB / 255, 0xCC / 255, 0xDD / 255)),
        ],
    )
    def test_parse(self, text: str, expected: tuple[float, ...]) -> None:
        assert parse_color_text(text) == pytest.approx(expected)

    @pytest.mark.parametrize("text", ["#12", "#12345", "#gggggg", "red"])
    def test_parse_invalid(self, text: str) -> None:
        with pytest.raises(ParameterError):
            parse_color_text(text)

    def test_format(self) -> None:
        assert format_color_hex(1.0, 0.5, 0.0, 1.0) == "#FF8000FF"
        assert format_color_hex(-1.0, 2.0, 0.0, 1.0) == "#00FF00FF"

    def test_encode_dict(self) -> None:
        el = encode_color({"r": 1.0, "g": 0.0, "b": 0.5, "a": 0.25})
        assert el.tag == "color"
        assert [c.tag for c in el] == ["r", "g", "b", "a"]
        assert float(el.findtext("b")) == pytest.approx(0.5)

    def test_encode_sequence_and_clamp(self) -> None:
        el = encode_color([2.0, -1.0, 0.5])
        assert float(el.findtext("r")) == 1.0
        assert float(el.findtext("g")) == 0.0
        assert float(el.findtext("a")) == 1.0

    def test_encode_invalid(self) -> None:
        with pytest.raises(ParameterError):
            encode_color(42)
        with pytest.raises(ParameterError):
            encode_color({"r": "nope"})
        with pytest.raises(ParameterError):
            encode_color([1, 2])

    def test_decode(self) -> None:
        el = encode_color("#336699")
        decoded = decode_color(el)
        assert decoded["hex"] == "#336699FF"
        assert decoded["a"] == pytest.approx(1.0)

    def test_decode_missing_channels(self) -> None:
        el = etree.fromstring("<color><r>x</r></color>")
        decoded = decode_color(el)
        assert decoded["r"] == 0.0
        assert decoded["g"] == 0.0
        assert decoded["a"] == 0.0


class TestVector:
    def test_encode_units(self) -> None:
        el = encode_vector([1.0, -0.5])
        assert float(el.findtext("x")) == 1.0
        assert float(el.findtext("y")) == -0.5

    def test_encode_pixels(self) -> None:
        el = encode_vector([60.0, -120.0], unit_px=60.0, unit_system="pixels")
        assert float(el.findtext("x")) == 1.0
        assert float(el.findtext("y")) == -2.0

    def test_encode_dict(self) -> None:
        el = encode_vector({"x": 0.25, "y": 0.75})
        assert decode_vector(el) == {"x": 0.25, "y": 0.75}

    def test_encode_invalid(self) -> None:
        with pytest.raises(ParameterError):
            encode_vector([1])
        with pytest.raises(ParameterError):
            encode_vector({"x": "bad", "y": 0})
        with pytest.raises(ParameterError):
            encode_vector("nope")

    def test_decode_pixels(self) -> None:
        el = encode_vector([1.0, 2.0])
        assert decode_vector(el, unit_px=10.0, unit_system="pixels") == {"x": 10.0, "y": 20.0}

    def test_decode_missing(self) -> None:
        el = etree.fromstring("<vector><x>nope</x></vector>")
        assert decode_vector(el) == {"x": 0.0, "y": 0.0}


class TestGradient:
    def test_roundtrip(self) -> None:
        el = encode_gradient([{"pos": -1, "color": "#000000"}, {"pos": 2, "color": "#ffffff"}])
        stops = decode_gradient(el)
        assert [s["pos"] for s in stops] == [0.0, 1.0]
        assert stops[0]["hex"] == "#000000FF"

    def test_encode_invalid(self) -> None:
        with pytest.raises(ParameterError):
            encode_gradient([])
        with pytest.raises(ParameterError):
            encode_gradient("nope")
        with pytest.raises(ParameterError):
            encode_gradient([{"pos": 0.5}])
        with pytest.raises(ParameterError):
            encode_gradient([{"pos": "bad", "color": "#fff"}])

    def test_decode_invalid_pos(self) -> None:
        el = etree.fromstring('<gradient><color pos="bad"><r>0</r></color></gradient>')
        assert decode_gradient(el)[0]["pos"] == 0.0


class TestScalars:
    def test_infer(self) -> None:
        assert encode_value(True).tag == "bool"
        assert encode_value(3).tag == "integer"
        assert encode_value(3.5).tag == "real"
        assert encode_value("hi").tag == "string"
        assert encode_value([1, 2]).tag == "vector"
        assert encode_value([1, 2, 3]).tag == "color"
        assert encode_value([{"pos": 0, "color": "#fff"}]).tag == "gradient"
        assert encode_value({"r": 0, "g": 0, "b": 0}).tag == "color"
        assert encode_value({"x": 0, "y": 0}).tag == "vector"

    def test_expected(self) -> None:
        assert encode_value(1, expected="real").tag == "real"
        assert encode_value(1, expected="integer").tag == "integer"
        assert encode_value(90, expected="angle").tag == "angle"
        assert encode_value("2s", expected="time").get("value") == "2s"
        assert encode_value("yes", expected="bool").get("value") == "true"
        assert encode_value(None, expected="string").text == ""

    def test_invalid(self) -> None:
        with pytest.raises(ParameterError):
            encode_value("x", expected="real")
        with pytest.raises(ParameterError):
            encode_value("maybe", expected="bool")
        with pytest.raises(ParameterError):
            encode_value([1, 2], expected="canvas")
        with pytest.raises(ParameterError):
            encode_value(1, expected="mystery")

    def test_decode_scalars(self) -> None:
        assert decode_value(encode_value(1.5)) == {"type": "real", "value": 1.5}
        assert decode_value(encode_value(2)) == {"type": "integer", "value": 2}
        assert decode_value(encode_value(45, expected="angle"))["unit"] == "degrees"
        assert decode_value(encode_value("1s", expected="time"))["seconds"] == 1.0
        assert decode_value(encode_value(True))["value"] is True
        assert decode_value(encode_value("text"))["value"] == "text"

    def test_decode_unknown(self) -> None:
        el = etree.fromstring('<thing a="1">hello</thing>')
        decoded = decode_value(el)
        assert decoded["type"] == "thing"
        assert decoded["value"]["attributes"] == {"a": "1"}

    def test_decode_composite_lists(self) -> None:
        composite = etree.fromstring(
            "<composite type='x'><real value='1.0'/><integer value='2'/></composite>"
        )
        decoded = decode_value(composite)
        assert decoded["type"] == "composite"
        assert decoded["value"]["real"]["value"] == 1.0

        static = etree.fromstring(
            "<static_list type='real'><entry><real value='1'/></entry></static_list>"
        )
        assert decode_value(static)["value"][0]["value"]["value"] == 1.0

        dynamic = etree.fromstring(
            "<dynamic_list type='vector' loop='true'><entry use='x'/></dynamic_list>"
        )
        assert decode_value(dynamic)["loop"] is True

        for tag in ("wplist", "dilist", "list"):
            el = etree.fromstring(f"<{tag}><entry><real value='1'/></entry></{tag}>")
            assert decode_value(el)["type"] == tag

        guid = etree.fromstring('<guid value="ABC"/>')
        assert decode_value(guid)["value"] == "ABC"

        transformation = etree.fromstring(
            "<transformation><offset><vector><x>1</x><y>2</y></vector></offset></transformation>"
        )
        assert decode_value(transformation)["value"]["offset"] == {"x": 1.0, "y": 2.0}

        width_point = etree.fromstring(
            "<width_point><position><real>1.5</real></position></width_point>"
        )
        assert decode_value(width_point)["value"]["position"] == 1.5

        for tag in (
            "bone",
            "bone_root",
            "bone_valuenode",
            "bone_link",
            "bone_weight_pair",
            "boneinfluence",
        ):
            assert decode_value(etree.Element(tag))["type"] == tag


class TestBline:
    def test_roundtrip(self) -> None:
        el = encode_bline(
            {
                "vertices": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]],
                "t1": [[0.1, 0.0], [0.0, 0.1], [0.0, 0.0]],
                "t2": [[0.0, 0.0], [0.0, -0.1], [-0.1, 0.0]],
                "widths": [0.5, 1.0, 2.0],
                "loop": True,
            }
        )
        decoded = decode_bline(el)
        assert decoded["loop"] is True
        assert len(decoded["vertices"]) == 3
        assert decoded["vertices"][0]["point"] == {"x": 0.0, "y": 0.0}
        assert decoded["vertices"][1]["width"] == 1.0
        assert decoded["vertices"][0]["t1"] == {"x": 0.1, "y": 0.0}

    def test_compact_list(self) -> None:
        el = encode_bline([[0.0, 0.0], [1.0, 1.0]])
        assert el.get("guid") is not None
        assert decode_bline(el)["loop"] is False

    def test_invalid(self) -> None:
        with pytest.raises(ParameterError):
            encode_bline("nope")
        with pytest.raises(ParameterError):
            encode_bline({"loop": True})
        with pytest.raises(ParameterError):
            encode_bline({"vertices": ["bad"]})

    def test_decode_skips_entries_without_composite(self) -> None:
        el = etree.fromstring("<bline><entry/></bline>")
        assert decode_bline(el)["vertices"] == []


class TestVectorList:
    def test_encode(self) -> None:
        el = encode_vector_list({"vertices": [[0.0, 0.0], [1.0, 2.0]]})
        assert el.tag == "dynamic_list"
        assert el.get("type") == "vector"
        assert len(el.findall("entry")) == 2

    def test_pixels(self) -> None:
        el = encode_vector_list([[60.0, 120.0]], unit_px=60.0, unit_system="pixels")
        vector = el.find("entry/vector")
        assert vector is not None
        assert float(vector.findtext("x")) == 1.0

    def test_invalid(self) -> None:
        with pytest.raises(ParameterError):
            encode_vector_list([])
        with pytest.raises(ParameterError):
            encode_vector_list([1, 2])


class TestParam:
    def test_reference(self) -> None:
        param = encode_param("x", None, reference=":foo")
        assert param.get("use") == ":foo"
        assert param_value_type(param) == "reference"
        assert decode_param(param) == {"name": "x", "type": "reference", "use": ":foo"}

    def test_empty(self) -> None:
        param = etree.fromstring('<param name="x"/>')
        assert param_value_type(param) is None
        assert decode_param(param) == {"name": "x", "type": "empty", "value": None}

    def test_encoded(self) -> None:
        param = encode_param("color", "#ff0000", tag="color")
        decoded = decode_param(param)
        assert decoded["name"] == "color"
        assert decoded["type"] == "color"

    def test_helpers(self) -> None:
        assert qn("x") == "x"
        assert make_element("x", a=1, b=None).attrib == {"a": "1"}
        assert _stringify(True) == "true"
        assert _stringify(1.5) == "1.5"
        assert _stringify(2.0) == "2"
        assert _fmt(0.0) == "0.0000000000"
        assert _fmt(-0.0) == "0.0000000000"
        assert _fmt(1.25) == "1.2500000000"

    def test_animated_decode(self) -> None:
        animated = etree.fromstring(
            '<animated type="real"><waypoint time="0f" before="linear" after="linear" tension="0.5">'
            '<real value="1.0"/></waypoint><waypoint time="1s" use="X"/></animated>'
        )
        decoded = decode_animated(animated)
        assert decoded["type"] == "real"
        assert decoded["waypoints"][0]["tension"] == 0.5
        assert decoded["waypoints"][0]["value"]["value"] == 1.0
        assert decoded["waypoints"][1]["use"] == "X"
