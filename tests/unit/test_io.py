# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for .sif/.sifz/.sfg reading, writing and atomic round-trips."""

from __future__ import annotations

import gzip
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from synfig_mcp.document import io
from synfig_mcp.errors import (
    InvalidProjectError,
    LimitExceededError,
    UnsupportedFormatError,
    WorkspaceError,
)
from synfig_mcp.security.limits import Limits

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<canvas version="1.0" width="320" height="240" fps="24.000" begin-time="0f" end-time="2s"
        view-box="-1.5 1.5 1.5 -1.5" bgcolor="0 0 0 1" xmlns:custom="urn:test">
  <name>sample</name>
  <custom:extra keep="yes">payload</custom:extra>
  <defs><gradient id="g"><color pos="0"><r>1</r><g>0</g><b>0</b><a>1</a></color></gradient></defs>
  <layer type="circle" active="true" desc="Circle">
    <param name="radius"><real value="0.5"/></param>
  </layer>
</canvas>
"""


def sample_tree() -> etree._ElementTree:
    return io.parse_sif(SAMPLE.encode())


class TestParse:
    def test_parse_ok(self) -> None:
        tree = sample_tree()
        assert tree.getroot().tag == "canvas"
        assert io.count_layers(tree) == 1

    def test_parse_invalid_xml(self) -> None:
        with pytest.raises(InvalidProjectError, match="well-formed"):
            io.parse_sif(b"<canvas>")

    def test_parse_wrong_root(self) -> None:
        with pytest.raises(InvalidProjectError, match="canvas"):
            io.parse_sif(b"<notcanvas/>")

    def test_parse_preserves_unknown(self) -> None:
        tree = sample_tree()
        extra = tree.getroot().find("{urn:test}extra")
        assert extra is not None
        assert extra.get("keep") == "yes"
        assert extra.text == "payload"


class TestReadWrite:
    @pytest.mark.parametrize("suffix", [".sif", ".sifz", ".sfg"])
    def test_roundtrip(self, tmp_path: Path, suffix: str) -> None:
        path = tmp_path / f"project{suffix}"
        io.write_project(sample_tree(), path, backup=False)
        assert path.is_file()
        loaded = io.read_project(path)
        assert loaded.getroot().get("width") == "320"
        assert loaded.getroot().find("name").text == "sample"  # type: ignore[union-attr]
        assert loaded.getroot().find("{urn:test}extra").text == "payload"  # type: ignore[union-attr]

    def test_gzip_is_small(self, tmp_path: Path) -> None:
        path = tmp_path / "project.sifz"
        io.write_project(sample_tree(), path, backup=False, pretty=True)
        assert path.read_bytes()[:2] == b"\x1f\x8b"

    def test_sfg_preserves_other_entries(self, tmp_path: Path) -> None:
        path = tmp_path / "bundle.sfg"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("assets/note.txt", b"hello")
            bundle.writestr("canvas.sif", SAMPLE)
        io.write_project(sample_tree(), path, backup=True)
        with zipfile.ZipFile(path) as bundle:
            names = set(bundle.namelist())
        assert "canvas.sifz" in names
        assert "assets/note.txt" in names
        assert io.read_sif_bytes(path).startswith(b"<?xml")

    def test_sfg_chooses_shortest_sifz(self, tmp_path: Path) -> None:
        path = tmp_path / "bundle.sfg"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("nested/canvas.sifz", gzip.compress(SAMPLE.encode()))
        assert io.read_sif_bytes(path).startswith(b"<?xml")

    def test_sfg_without_canvas(self, tmp_path: Path) -> None:
        path = tmp_path / "bundle.sfg"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("readme.txt", b"no canvas")
        with pytest.raises(InvalidProjectError, match=r"no \.sif"):
            io.read_sif_bytes(path)

    def test_bad_zip(self, tmp_path: Path) -> None:
        path = tmp_path / "bundle.sfg"
        path.write_bytes(b"not a zip")
        with pytest.raises(InvalidProjectError, match=r"not a valid \.sfg"):
            io.read_sif_bytes(path)

    def test_bad_gzip(self, tmp_path: Path) -> None:
        path = tmp_path / "project.sifz"
        path.write_bytes(b"not gzip")
        with pytest.raises(InvalidProjectError, match="not a valid gzip"):
            io.read_sif_bytes(path)

    def test_corrupt_embedded_sifz(self, tmp_path: Path) -> None:
        path = tmp_path / "bundle.sfg"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("canvas.sifz", b"not gzip")
        with pytest.raises(InvalidProjectError, match="corrupt"):
            io.read_sif_bytes(path)

    def test_unsupported_read(self, tmp_path: Path) -> None:
        path = tmp_path / "project.xml"
        path.write_bytes(b"<canvas/>")
        with pytest.raises(UnsupportedFormatError):
            io.read_sif_bytes(path)

    def test_unsupported_write(self, tmp_path: Path) -> None:
        with pytest.raises(UnsupportedFormatError):
            io.write_project(sample_tree(), tmp_path / "project.xml")

    def test_backup(self, tmp_path: Path) -> None:
        path = tmp_path / "project.sif"
        path.write_text("<old/>")
        io.write_project(sample_tree(), path, backup=True)
        assert (tmp_path / "project.sif.bak").read_text() == "<old/>"
        assert path.read_text().startswith("<?xml")

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError):
            io.read_project(tmp_path / "missing.sif")

    def test_file_size_limit(self, tmp_path: Path) -> None:
        from synfig_mcp.config import Settings

        path = tmp_path / "project.sif"
        path.write_bytes(SAMPLE.encode())
        limits = Limits(Settings(workspace=tmp_path, max_file_mb=0))
        with pytest.raises(LimitExceededError):
            io.read_project(path, limits)

    def test_layer_limit(self, tmp_path: Path) -> None:
        from synfig_mcp.config import Settings

        path = tmp_path / "project.sif"
        path.write_bytes(SAMPLE.encode())
        limits = Limits(Settings(workspace=tmp_path, max_layers=0))
        with pytest.raises(LimitExceededError, match="layers"):
            io.read_project(path, limits)

    def test_count_layers_in_root(self) -> None:
        root = sample_tree().getroot()
        assert io.count_layers_in_root(root) == 1

    def test_pretty_serialize(self) -> None:
        assert b"\n" in io.serialize_pretty(sample_tree())

    def test_atomic_write_cleans_up_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import os

        def boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("replace failed")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(RuntimeError):
            io.atomic_write(tmp_path / "x.sif", b"data", backup=False)
        assert list(tmp_path.glob("*.tmp")) == []


class TestNewProject:
    def test_attributes(self) -> None:
        tree = io.new_project_xml(
            width=640,
            height=360,
            fps=30.0,
            begin_time="0f",
            end_time="5s",
            name="demo",
            bgcolor=(0.1, 0.2, 0.3, 1.0),
            antialias=2,
            gamma=(1.0, 0.9, 0.8),
        )
        root = tree.getroot()
        assert root.get("width") == "640"
        assert root.get("height") == "360"
        assert root.get("antialias") == "2"
        assert root.get("bgcolor") == "0.100000 0.200000 0.300000 1.000000"
        assert root.get("gamma-r") == "1.000000"
        assert root.findtext("name") == "demo"
        assert root.get("fps") == "30.000"

    def test_default_view_box_aspect(self) -> None:
        assert io.default_view_box(100, 100) == (-1.5, 1.5, 1.5, -1.5)
        view = io.default_view_box(200, 100)
        assert view == (-3.0, 1.5, 3.0, -1.5)

    def test_custom_view_box(self) -> None:
        tree = io.new_project_xml(
            width=10,
            height=10,
            fps=24,
            begin_time="0f",
            end_time="1s",
            name="x",
            bgcolor=(0, 0, 0, 1),
            view_box=(-1, 2, 3, -4),
        )
        assert tree.getroot().get("view-box") == "-1.000000 2.000000 3.000000 -4.000000"
