# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for ProjectSession: navigation, dirty tracking and history."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from synfig_mcp.config import Settings
from synfig_mcp.document import io
from synfig_mcp.document.model import ProjectSession, layer_display_name
from synfig_mcp.errors import HistoryError, LayerNotFoundError

XML = """<canvas version="1.0" width="100" height="50" fps="24.000" begin-time="0f" end-time="1s">
  <name>session</name>
  <layer type="circle" desc="Ball"><param name="radius"><real value="0.5"/></param>
    <param name="canvas"><canvas><layer type="star" desc="Nested">
      <param name="points"><integer value="5"/></param></layer></canvas></param>
  </layer>
  <layer type="circle"><param name="name"><string>Unnamed</string></param></layer>
  <layer type="circle" desc="Ball"/>
</canvas>
"""


@pytest.fixture
def session(tmp_path: Path) -> ProjectSession:
    tree = io.parse_sif(XML.encode())
    return ProjectSession(tree, settings=Settings(workspace=tmp_path), name="session")


class TestIdentity:
    def test_name_and_set_name(self, session: ProjectSession) -> None:
        assert session.name == "session"
        session.set_name("new")
        assert session.name == "new"
        assert session.root.findtext("name") == "new"
        assert session.dirty

    def test_set_name_creates_element(self, session: ProjectSession) -> None:
        name_el = session.root.find("name")
        assert name_el is not None
        session.root.remove(name_el)
        session.set_name("created")
        assert session.root.findtext("name") == "created"

    def test_default_name(self, tmp_path: Path) -> None:
        tree = io.parse_sif(b"<canvas width='1' height='1'/>")
        assert ProjectSession(tree, settings=Settings(workspace=tmp_path)).name == "synfig-project"

    def test_canvas_id(self, session: ProjectSession) -> None:
        assert session.canvas_id() is None
        session.root.set("id", "c1")
        assert session.canvas_id() == "c1"

    def test_info(self, session: ProjectSession) -> None:
        info = session.info()
        assert info["width"] == 100
        assert info["height"] == 50
        assert info["layer_count"] == 3
        assert info["total_layer_count"] == 4
        assert info["dirty"] is False
        assert info["version"] == "1.0"
        assert info["gamma"] == (1.0, 1.0, 1.0)


class TestNavigation:
    def test_layers(self, session: ProjectSession) -> None:
        assert len(session.layers()) == 3

    def test_all_layers(self, session: ProjectSession) -> None:
        entries = session.all_layers()
        assert len(entries) == 4
        assert entries[1][0] == (0, 0)

    def test_layer_by_index(self, session: ProjectSession) -> None:
        assert session.layer_by_index(0).get("desc") == "Ball"
        with pytest.raises(LayerNotFoundError):
            session.layer_by_index(99)
        with pytest.raises(LayerNotFoundError):
            session.layer_by_index(-1)

    def test_layer_by_name(self, session: ProjectSession) -> None:
        assert session.layer_by_name("Ball").get("desc") == "Ball"
        assert session.layer_by_name("Unnamed").get("type") == "circle"
        with pytest.raises(LayerNotFoundError) as excinfo:
            session.layer_by_name("Bal")
        assert "Ball" in (excinfo.value.hint or "")

    def test_resolve(self, session: ProjectSession) -> None:
        assert session.resolve_layer(0)[0] == 0
        assert session.resolve_layer("1")[0] == 1
        assert session.resolve_layer("Ball")[0] == 0
        assert session.resolve_layer(True)[0] == 1

    def test_display_name_fallbacks(self) -> None:
        layer = etree.fromstring('<layer type="circle"/>')
        assert layer_display_name(layer) == "circle"
        layer = etree.fromstring(
            '<layer type="circle"><param name="name"><string>Hi</string></param></layer>'
        )
        assert layer_display_name(layer) == "Hi"
        layer = etree.fromstring(
            '<layer type="circle"><param name="name"><string> </string></param></layer>'
        )
        assert layer_display_name(layer) == "circle"

    def test_defs_creation_placement(self, session: ProjectSession) -> None:
        defs = session.defs(create=True)
        assert defs is not None
        children = list(session.root)
        assert children.index(defs) < children.index(session.layers()[0])
        assert session.defs(create=True) is defs

    def test_defs_append_when_no_layers(self, tmp_path: Path) -> None:
        tree = io.parse_sif(b"<canvas width='1' height='1'/>")
        session = ProjectSession(tree, settings=Settings(workspace=tmp_path))
        defs = session.defs(create=True)
        assert defs is not None
        assert list(session.root)[-1] is defs


class TestHistory:
    def test_undo_redo(self, session: ProjectSession) -> None:
        session.set_name("one")
        session.touch()
        session.record_history()
        session.set_name("two")
        assert session.undo() == "undo"
        assert session.name == "one"
        assert session.redo() == "redo"
        assert session.name == "two"

    def test_undo_without_history(self, session: ProjectSession) -> None:
        with pytest.raises(HistoryError, match="Nothing to undo"):
            session.undo()

    def test_redo_without_history(self, session: ProjectSession) -> None:
        with pytest.raises(HistoryError, match="Nothing to redo"):
            session.redo()

    def test_record_clears_redo(self, session: ProjectSession) -> None:
        session.record_history()
        session.set_name("one")
        session.undo()
        session.record_history()
        with pytest.raises(HistoryError):
            session.redo()

    def test_batch_suppresses_history(self, session: ProjectSession) -> None:
        session.batch_depth = 1
        session.record_history()
        session.batch_depth = 0
        with pytest.raises(HistoryError):
            session.undo()

    def test_clear_history(self, session: ProjectSession) -> None:
        session.record_history()
        session.clear_history()
        with pytest.raises(HistoryError):
            session.undo()

    def test_bounded_history(self, tmp_path: Path) -> None:
        tree = io.parse_sif(b"<canvas width='1' height='1'/>")
        session = ProjectSession(tree, settings=Settings(workspace=tmp_path, history_depth=2))
        for index in range(5):
            session.record_history()
            session.set_name(str(index))
        assert session.undo() == "undo"
        assert session.undo() == "undo"
        with pytest.raises(HistoryError):
            session.undo()

    def test_restore_marks_dirty(self, session: ProjectSession) -> None:
        session.record_history()
        session.set_name("changed")
        session.dirty = False
        session.undo()
        assert session.dirty is True
