# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for canvas properties and blend methods."""

from __future__ import annotations

import pytest
from lxml import etree

from synfig_mcp.document.canvas import (
    BLEND_METHODS,
    blend_method_name,
    get_canvas_props,
    parse_blend_method,
    set_canvas_props,
)
from synfig_mcp.errors import ParameterError

ROOT = etree.fromstring(
    """<canvas version="1.0" width="320" height="240" xres="2834.645910"
       yres="2834.645910" view-box="-1.5 1.5 1.5 -1.5" antialias="1"
       fps="24.000" begin-time="0f" end-time="5s"
       bgcolor="0.1 0.2 0.3 1.0" gamma-r="1.0" gamma-g="1.0" gamma-b="1.0"/>"""
)


class TestBlend:
    @pytest.mark.parametrize("name", sorted(BLEND_METHODS))
    def test_roundtrip_names(self, name: str) -> None:
        value = parse_blend_method(name)
        assert blend_method_name(value) == name

    def test_numeric_and_text(self) -> None:
        assert parse_blend_method(6) == 6
        assert parse_blend_method("6") == 6
        assert parse_blend_method("multiply") == 6
        assert parse_blend_method("alpha-over") == 19
        assert parse_blend_method("hard light") == 17

    def test_defaults(self) -> None:
        assert parse_blend_method(None) == 0
        assert parse_blend_method(False) == 0
        assert parse_blend_method(True) == 1

    def test_invalid(self) -> None:
        with pytest.raises(ParameterError, match="Unknown blend"):
            parse_blend_method(99)
        with pytest.raises(ParameterError, match="Unknown blend"):
            parse_blend_method("multiplay")
        assert blend_method_name(99) == "unknown(99)"


class TestGet:
    def test_props(self) -> None:
        props = get_canvas_props(ROOT)
        assert props["width"] == 320
        assert props["height"] == 240
        assert props["fps"] == 24.0
        assert props["background"] == {"r": 0.1, "g": 0.2, "b": 0.3, "a": 1.0}
        assert props["gamma"] == (1.0, 1.0, 1.0)

    def test_defaults_and_invalid(self) -> None:
        root = etree.fromstring('<canvas width="bad" fps="bad" antialias="x"/>')
        props = get_canvas_props(root)
        assert props["width"] == 0
        assert props["fps"] == 24.0
        assert props["antialias"] == 1
        assert props["background"] is None

    def test_bad_bgcolor(self) -> None:
        root = etree.fromstring('<canvas bgcolor="nope"/>')
        assert get_canvas_props(root)["background"] is None


class TestSet:
    def test_dimensions(self) -> None:
        root = etree.fromstring("<canvas/>")
        applied = set_canvas_props(root, {"width": 800, "height": 600, "antialias": 4})
        assert root.get("width") == "800"
        assert root.get("antialias") == "4"
        assert applied["width"] == 800

    def test_invalid_dimensions(self) -> None:
        root = etree.fromstring("<canvas/>")
        for value in (0, -1, 9000, "x"):
            with pytest.raises(ParameterError):
                set_canvas_props(root, {"width": value}, max_resolution=8192)

    def test_res_and_fps(self) -> None:
        root = etree.fromstring("<canvas/>")
        set_canvas_props(root, {"xres": 100, "yres": 200, "fps": 30})
        assert root.get("xres") == "100.000000"
        assert root.get("fps") == "30.000000"

    def test_bounds(self) -> None:
        root = etree.fromstring("<canvas/>")
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"xres": 0})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"antialias": 100})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"fps": 500})

    def test_time(self) -> None:
        root = etree.fromstring('<canvas fps="24.000"/>')
        set_canvas_props(root, {"begin_time": "1s", "end_time": "2s 12f"})
        assert root.get("begin-time") == "1s"
        assert root.get("end-time") == "2s 12f"

    def test_view_box(self) -> None:
        root = etree.fromstring("<canvas/>")
        set_canvas_props(root, {"view_box": [-1, 2, 3, -4]})
        assert root.get("view-box") == "-1.000000 2.000000 3.000000 -4.000000"
        set_canvas_props(root, {"view_box": "0 1 2 3"})
        assert root.get("view-box") == "0.000000 1.000000 2.000000 3.000000"
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"view_box": "1 2 3"})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"view_box": ["a", "b", "c", "d"]})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"view_box": [1, 2]})

    def test_background(self) -> None:
        root = etree.fromstring("<canvas/>")
        set_canvas_props(root, {"background": "#ff0000"})
        assert root.get("bgcolor") == "1.000000 0.000000 0.000000 1.000000"
        set_canvas_props(root, {"background": "0.1 0.2 0.3 0.4"})
        assert root.get("bgcolor") == "0.100000 0.200000 0.300000 0.400000"
        set_canvas_props(root, {"background": [0.5, 0.5, 0.5]})
        assert root.get("bgcolor") == "0.500000 0.500000 0.500000 1.000000"
        set_canvas_props(root, {"background": [0.1, 0.2, 0.3, 0.4]})
        assert root.get("bgcolor").startswith("0.100000")
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"background": "1 2 3"})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"background": "a b c d"})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"background": [1, 2]})

    def test_gamma(self) -> None:
        root = etree.fromstring("<canvas/>")
        set_canvas_props(root, {"gamma": 1.2})
        assert root.get("gamma-r") == "1.200000"
        set_canvas_props(root, {"gamma": [0.9, 1.0, 1.1]})
        assert root.get("gamma-g") == "1.000000"
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"gamma": [1, 2]})
        with pytest.raises(ParameterError):
            set_canvas_props(root, {"gamma": [20, 1, 1]})

    def test_none_ignored(self) -> None:
        root = etree.fromstring("<canvas/>")
        assert set_canvas_props(root, {"width": None, "background": None}) == {}
