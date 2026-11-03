# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for waypoint/animation helpers."""

from __future__ import annotations

import pytest
from lxml import etree

from synfig_mcp.document.animation import (
    EASE_TCB_TENSION,
    animate_param,
    ensure_animated,
    export_animated_xml,
    find_waypoint,
    get_animated,
    interpolation_keyword,
    remove_waypoint,
    set_interpolation,
    set_waypoint,
    waypoints,
)
from synfig_mcp.errors import ParameterError, WaypointError


def vector_param(name: str = "origin") -> etree._Element:
    return etree.fromstring(f'<param name="{name}"><vector><x>0.0</x><y>0.0</y></vector></param>')


def real_param() -> etree._Element:
    return etree.fromstring('<param name="radius"><real value="1.0"/></param>')


class TestInterpolation:
    @pytest.mark.parametrize(
        ("name", "keyword"),
        [
            ("linear", "linear"),
            ("clamped", "clamped"),
            ("tcb", "auto"),
            ("auto", "auto"),
            ("ease", "auto"),
            ("halt", "halt"),
            ("manual", "manual"),
            ("constant", "constant"),
            ("EASE", "auto"),
            ("HALT", "halt"),
        ],
    )
    def test_keyword(self, name: str, keyword: str) -> None:
        assert interpolation_keyword(name) == keyword

    def test_invalid(self) -> None:
        with pytest.raises(ParameterError, match="Unknown interpolation"):
            interpolation_keyword("wobbly")


class TestAnimated:
    def test_ensure(self) -> None:
        param = vector_param()
        animated = ensure_animated(param)
        assert animated.tag == "animated"
        assert animated.get("type") == "vector"
        assert len(waypoints(animated)) == 1
        assert ensure_animated(param) is animated

    def test_ensure_custom_type(self) -> None:
        param = real_param()
        assert ensure_animated(param, "real").get("type") == "real"

    def test_ensure_reference(self) -> None:
        param = etree.fromstring('<param name="x" use=":ref"/>')
        with pytest.raises(WaypointError, match="reference"):
            ensure_animated(param)

    def test_ensure_unsupported(self) -> None:
        param = etree.fromstring('<param name="x"><canvas/></param>')
        with pytest.raises(WaypointError, match="Cannot animate"):
            ensure_animated(param)

    def test_get_none(self) -> None:
        assert get_animated(real_param()) is None


class TestWaypoints:
    def test_set_and_replace(self) -> None:
        param = real_param()
        set_waypoint(param, "0f", 2.0, interpolation="linear")
        set_waypoint(param, "24f", 4.0, interpolation="constant")
        animated = get_animated(param)
        assert animated is not None
        assert len(waypoints(animated)) == 2
        assert [wp.get("time") for wp in waypoints(animated)] == ["0f", "1s"]

        set_waypoint(param, "1s", 8.0)
        assert len(waypoints(animated)) == 2
        updated = find_waypoint(animated, "1s", fps=24)
        assert updated is not None
        assert float(updated.find("real").get("value")) == 8.0  # type: ignore[union-attr]

    def test_set_inserts_sorted(self) -> None:
        param = real_param()
        set_waypoint(param, "2s", 2.0)
        set_waypoint(param, "1s", 1.0)
        set_waypoint(param, "0f", 0.0)
        animated = get_animated(param)
        assert [wp.get("time") for wp in waypoints(animated)] == ["0f", "1s", "2s"]  # type: ignore[union-attr]

    def test_set_skips_malformed_existing_time(self) -> None:
        param = real_param()
        animated = ensure_animated(param)
        etree.SubElement(animated, "waypoint", time="bogus")
        set_waypoint(param, "1s", 3.0)
        assert len(waypoints(animated)) == 3

    def test_remove(self) -> None:
        param = real_param()
        assert remove_waypoint(param, "0f", fps=24) is False
        set_waypoint(param, "0f", 1.0)
        assert remove_waypoint(param, "1s", fps=24) is False
        assert remove_waypoint(param, "0f", fps=24) is True

    def test_set_interpolation_all(self) -> None:
        param = real_param()
        animate_param(param, [{"time": "0f", "value": 0.0}, {"time": "1s", "value": 1.0}])
        assert set_interpolation(param, "linear") == 2

    def test_set_interpolation_one(self) -> None:
        param = real_param()
        animate_param(param, [{"time": "0f", "value": 0.0}, {"time": "1s", "value": 1.0}])
        assert set_interpolation(param, "constant", time_text="1s") == 1

    def test_set_interpolation_ease(self) -> None:
        param = real_param()
        set_waypoint(param, "0f", 0.0)
        assert set_interpolation(param, "ease") == 1
        animated = get_animated(param)
        wp = waypoints(animated)[0]
        assert wp.get("before") == "auto"
        assert float(wp.get("tension", "0")) == pytest.approx(EASE_TCB_TENSION)

    def test_set_interpolation_errors(self) -> None:
        param = real_param()
        with pytest.raises(WaypointError, match="not animated"):
            set_interpolation(param, "linear")
        set_waypoint(param, "0f", 1.0)
        with pytest.raises(WaypointError, match="No waypoint"):
            set_interpolation(param, "linear", time_text="10s")


class TestAnimateParam:
    def test_basic(self) -> None:
        param = vector_param()
        count = animate_param(
            param,
            [
                {"time": "1s", "value": [1.0, 0.0]},
                {"time": "0f", "value": [0.0, 0.0]},
            ],
            interpolation="linear",
        )
        assert count == 2
        animated = get_animated(param)
        assert [wp.get("time") for wp in waypoints(animated)] == ["0f", "1s"]  # type: ignore[arg-type]
        assert all(wp.get("before") == "linear" for wp in waypoints(animated))  # type: ignore[union-attr]

    def test_per_waypoint_interpolation(self) -> None:
        param = real_param()
        animate_param(
            param,
            [
                {"time": "0f", "value": 0.0, "before": "constant", "after": "tcb"},
                {"time": "1s", "value": 1.0, "interpolation": "clamped"},
            ],
        )
        wps = waypoints(get_animated(param))  # type: ignore[arg-type]
        assert wps[0].get("before") == "constant"
        assert wps[0].get("after") == "auto"
        assert wps[1].get("before") == "clamped"

    def test_empty(self) -> None:
        with pytest.raises(ParameterError, match="non-empty"):
            animate_param(real_param(), [])

    def test_bad_spec(self) -> None:
        with pytest.raises(ParameterError, match="time"):
            animate_param(real_param(), [{"time": "0f"}])

    def test_bad_interpolation(self) -> None:
        with pytest.raises(ParameterError):
            animate_param(real_param(), [{"time": "0f", "value": 1.0}], interpolation="nope")

    def test_export_xml(self) -> None:
        param = real_param()
        set_waypoint(param, "0f", 1.0)
        xml = export_animated_xml(param)
        assert "<param" in xml and "waypoint" in xml
