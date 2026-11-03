# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for structural project validation."""

from __future__ import annotations

from lxml import etree

from synfig_mcp.document.validators import KNOWN_LAYER_TYPES, validate_document


def canvas(body: str = "", **attrs: object) -> etree._Element:
    base = {
        "version": "1.0",
        "width": "100",
        "height": "100",
        "xres": "2834.6",
        "yres": "2834.6",
        "view-box": "-1 1 1 -1",
        "antialias": "1",
        "fps": "24",
        "begin-time": "0f",
        "end-time": "1s",
    }
    base.update(attrs)
    attr_text = " ".join(f'{k}="{v}"' for k, v in base.items() if v is not None)
    return etree.fromstring(f"<canvas {attr_text}>{body}</canvas>")


def codes(report: dict) -> set[str]:
    return {entry["code"] for entry in report["errors"]} | {
        entry["code"] for entry in report["warnings"]
    }


class TestValid:
    def test_minimal(self) -> None:
        report = validate_document(canvas('<layer type="circle"/>'))
        assert report["valid"] is True
        assert report["errors"] == []
        assert report["summary"]["layers"] == 1

    def test_known_types_sanity(self) -> None:
        assert {"circle", "region", "skeleton"} <= KNOWN_LAYER_TYPES

    def test_good_defs_bones_keyframes(self) -> None:
        body = (
            '<defs><gradient id="g"/></defs>'
            "<bones><bone_root/><bone id='a'/></bones>"
            '<keyframe time="1s">start</keyframe>'
            '<layer type="circle" desc="A"><param name="radius"/></layer>'
        )
        report = validate_document(canvas(body))
        assert report["valid"] is True
        assert report["summary"]["defs_ids"] == 1
        assert report["summary"]["bones"] == 1
        assert report["summary"]["keyframes"] == 1


class TestRootAndCanvas:
    def test_wrong_root(self) -> None:
        report = validate_document(etree.fromstring("<svg/>"))
        assert report["valid"] is False
        assert report["errors"][0]["code"] == "root_tag"

    def test_bad_resolution(self) -> None:
        report = validate_document(canvas(width="0"))
        assert "resolution_range" in codes(report)
        report = validate_document(canvas(width="nope"))
        assert "resolution_missing" in codes(report)

    def test_resolution_cap(self) -> None:
        report = validate_document(canvas(width="99999"), max_resolution=100)
        assert "resolution_range" in codes(report)

    def test_bad_fps_and_res(self) -> None:
        report = validate_document(canvas(fps="0"))
        assert "fps_range" in codes(report)
        report = validate_document(canvas(fps="x"))
        assert "fps_invalid" in codes(report)
        report = validate_document(canvas(xres="0", yres="x"))
        assert {"res_range", "res_invalid"} <= codes(report)

    def test_view_box(self) -> None:
        report = validate_document(canvas(**{"view-box": "1 2 3"}))
        assert "view_box_format" in codes(report)
        report = validate_document(canvas(**{"view-box": "a b c d"}))
        assert "view_box_format" in codes(report)
        report = validate_document(canvas(**{"view-box": None}))
        assert "view_box_missing" in codes(report)

    def test_missing_version(self) -> None:
        report = validate_document(canvas(version=None))
        assert "version_missing" in codes(report)


class TestDefsAndBones:
    def test_invalid_and_duplicate_ids(self) -> None:
        body = '<defs><gradient id="bad id"/><gradient id="x"/><gradient id="x"/></defs>'
        report = validate_document(canvas(body))
        assert {"defs_id_invalid", "defs_id_duplicate"} <= codes(report)

    def test_defs_entries_without_ids_ignored(self) -> None:
        report = validate_document(canvas("<defs><gradient/><comment/></defs>"))
        assert report["valid"] is True

    def test_bone_duplicates(self) -> None:
        body = "<bones><bone id='a'/><bone id='a'/><bone_root/><bone_root/></bones>"
        report = validate_document(canvas(body))
        assert {"bone_id_duplicate", "bone_root_duplicate"} <= codes(report)


class TestLayers:
    def test_layer_limit(self) -> None:
        body = '<layer type="circle"/><layer type="circle"/>'
        report = validate_document(canvas(body), max_layers=1)
        assert "layer_limit" in codes(report)

    def test_missing_type(self) -> None:
        report = validate_document(canvas("<layer/>"))
        assert "layer_type_missing" in codes(report)

    def test_unknown_type_hint(self) -> None:
        report = validate_document(canvas('<layer type="circl"/>'))
        assert "layer_type_unknown" in codes(report)
        warning = next(w for w in report["warnings"] if w["code"] == "layer_type_unknown")
        assert "circle" in warning["hint"]

    def test_unknown_type_no_hint(self) -> None:
        report = validate_document(canvas('<layer type="zzzzzzzz"/>'))
        warning = next(w for w in report["warnings"] if w["code"] == "layer_type_unknown")
        assert "hint" not in warning

    def test_custom_known_types(self) -> None:
        report = validate_document(canvas('<layer type="custom"/>'), known_layer_types={"custom"})
        assert report["valid"] is True

    def test_duplicate_descs(self) -> None:
        body = '<layer type="circle" desc="a"/><layer type="circle" desc="a"/>'
        report = validate_document(canvas(body))
        assert "layer_desc_duplicate" in codes(report)

    def test_param_without_name(self) -> None:
        report = validate_document(canvas('<layer type="circle"><param/></layer>'))
        assert "param_name_missing" in codes(report)

    def test_bad_keyframe_time(self) -> None:
        report = validate_document(canvas('<keyframe time="nope"/>'))
        assert "keyframe_time_unparsable" in codes(report)

    def test_unknown_layer_types_are_warnings(self) -> None:
        report = validate_document(canvas('<layer type="future_layer"/>'))
        assert report["valid"] is True
        assert any(w["code"] == "layer_type_unknown" for w in report["warnings"])
