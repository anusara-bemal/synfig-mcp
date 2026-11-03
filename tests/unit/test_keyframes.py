# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for keyframe management."""

from __future__ import annotations

import pytest
from lxml import etree

from synfig_mcp.document.keyframes import (
    add_keyframe,
    list_keyframes,
    move_keyframe,
    remove_keyframe,
    set_keyframe_active,
)
from synfig_mcp.errors import KeyframeNotFoundError

FPS = 24.0


def root() -> etree._Element:
    return etree.fromstring('<canvas><name>x</name><defs/><layer type="circle"/></canvas>')


class TestKeyframes:
    def test_add_and_list(self) -> None:
        canvas = root()
        result = add_keyframe(canvas, "1s", "second", fps=FPS)
        assert result["updated"] is False
        assert result["label"] == "second"
        keyframes = list_keyframes(canvas, fps=FPS)
        assert keyframes == [
            {"index": 0, "time": "1s", "seconds": 1.0, "active": True, "label": "second"}
        ]

    def test_insert_sorted(self) -> None:
        canvas = root()
        add_keyframe(canvas, "2s", fps=FPS)
        add_keyframe(canvas, "0f", fps=FPS)
        add_keyframe(canvas, "1s", fps=FPS)
        assert [kf.get("time") for kf in canvas.findall("keyframe")] == ["0f", "1s", "2s"]

    def test_insert_before_anchor(self) -> None:
        canvas = root()
        add_keyframe(canvas, "0f", fps=FPS)
        children = [child.tag for child in canvas]
        assert children.index("keyframe") < children.index("defs")

    def test_update_existing(self) -> None:
        canvas = root()
        add_keyframe(canvas, "0f", "old", fps=FPS)
        result = add_keyframe(canvas, "0f", "new", fps=FPS)
        assert result["updated"] is True
        assert list_keyframes(canvas, fps=FPS)[0]["label"] == "new"

    def test_sanitizes_label(self) -> None:
        canvas = root()
        add_keyframe(canvas, "0f", "a\x00b\x01c", fps=FPS)
        assert list_keyframes(canvas, fps=FPS)[0]["label"] == "abc"

    def test_remove(self) -> None:
        canvas = root()
        add_keyframe(canvas, "0f", fps=FPS)
        assert remove_keyframe(canvas, "0f", fps=FPS) is True
        assert remove_keyframe(canvas, "0f", fps=FPS) is False

    def test_move(self) -> None:
        canvas = root()
        add_keyframe(canvas, "0f", "start", fps=FPS)
        add_keyframe(canvas, "1s", "end", fps=FPS)
        result = move_keyframe(canvas, "0f", "2s", fps=FPS)
        assert result["from"] == "0f"
        assert result["to"] == "2s"
        assert [kf.get("time") for kf in canvas.findall("keyframe")] == ["1s", "2s"]

    def test_move_missing(self) -> None:
        with pytest.raises(KeyframeNotFoundError):
            move_keyframe(root(), "0f", "1s", fps=FPS)

    def test_active(self) -> None:
        canvas = root()
        add_keyframe(canvas, "0f", fps=FPS)
        assert set_keyframe_active(canvas, "0f", False, fps=FPS) == {"time": "0f", "active": False}
        assert list_keyframes(canvas, fps=FPS)[0]["active"] is False
        with pytest.raises(KeyframeNotFoundError):
            set_keyframe_active(canvas, "1s", True, fps=FPS)

    def test_append_without_anchor(self) -> None:
        canvas = etree.fromstring("<canvas/>")
        add_keyframe(canvas, "0f", fps=FPS)
        assert canvas.find("keyframe") is not None

    def test_reorder_without_anchor(self) -> None:
        canvas = etree.fromstring("<canvas/>")
        add_keyframe(canvas, "1s", fps=FPS)
        add_keyframe(canvas, "0f", fps=FPS)
        move_keyframe(canvas, "0f", "3s", fps=FPS)
        assert [kf.get("time") for kf in canvas.findall("keyframe")] == ["1s", "3s"]

    def test_default_time_and_active(self) -> None:
        canvas = etree.fromstring("<canvas><keyframe/></canvas>")
        assert list_keyframes(canvas, fps=FPS)[0]["time"] == "0f"
