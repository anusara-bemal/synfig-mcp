# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for exported values and parameter linking."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from synfig_mcp.config import Settings
from synfig_mcp.document import io
from synfig_mcp.document.exported_values import (
    defs_ids,
    export_value,
    find_defs_entry,
    link_params,
    list_exported,
    unlink_params,
)
from synfig_mcp.document.model import ProjectSession
from synfig_mcp.errors import ExportError

XML = """<canvas width="100" height="100">
  <name>exports</name>
  <layer type="circle" desc="A">
    <param name="color"><color><r>1</r><g>0</g><b>0</b><a>1</a></color></param>
    <param name="radius"><real value="0.5"/></param>
    <param name="origin"><vector><x>0</x><y>0</y></vector></param>
  </layer>
  <layer type="rectangle" desc="B">
    <param name="color"><color><r>0</r><g>1</g><b>0</b><a>1</a></color></param>
    <param name="radius"><real value="1.0"/></param>
  </layer>
</canvas>"""


@pytest.fixture
def session(tmp_path: Path) -> ProjectSession:
    return ProjectSession(
        io.parse_sif(XML.encode()), settings=Settings(workspace=tmp_path), name="exports"
    )


class TestLookup:
    def test_find_missing_defs(self, session: ProjectSession) -> None:
        assert find_defs_entry(session.root, "x") is None
        assert defs_ids(session.root) == set()
        assert list_exported(session.root) == []

    def test_list_and_find(self, session: ProjectSession) -> None:
        defs = session.defs(create=True)
        assert defs is not None
        defs.append(etree.fromstring('<gradient id="brand"/>'))
        assert find_defs_entry(session.root, ":brand") is not None
        assert defs_ids(session.root) == {"brand"}
        assert list_exported(session.root) == [{"id": "brand", "tag": "gradient", "use": ":brand"}]

    def test_non_element_children_ignored(self, session: ProjectSession) -> None:
        defs = session.defs(create=True)
        assert defs is not None
        defs.append(etree.Comment("hello"))
        assert defs_ids(session.root) == set()


class TestExport:
    def test_success(self, session: ProjectSession) -> None:
        result = export_value(session, 0, "color", "brand")
        assert result["export_name"] == "brand"
        assert result["use"] == ":brand"
        param = session.layers()[0].find("param[@name='color']")
        assert param is not None
        assert param.get("use") == ":brand"
        entry = find_defs_entry(session.root, "brand")
        assert entry is not None
        assert entry.get("id") == "brand"
        assert session.dirty

    def test_missing_param(self, session: ProjectSession) -> None:
        with pytest.raises(ExportError, match="not found"):
            export_value(session, 0, "nope", "x")

    def test_already_exported(self, session: ProjectSession) -> None:
        export_value(session, 0, "color", "brand")
        with pytest.raises(ExportError, match="already exported"):
            export_value(session, 0, "color", "other")

    def test_reference(self, session: ProjectSession) -> None:
        param = session.layers()[0].find("param[@name='color']")
        assert param is not None
        for child in list(param):
            param.remove(child)
        param.set("use", "some-id")
        with pytest.raises(ExportError, match="references defs"):
            export_value(session, 0, "color", "other")

    def test_empty_param(self, session: ProjectSession) -> None:
        param = etree.SubElement(session.layers()[0], "param", name="empty")
        assert param is not None
        with pytest.raises(ExportError, match="no value"):
            export_value(session, 0, "empty", "x")

    @pytest.mark.parametrize("name", ["", "a b", "a:b", "a#b", "a\nb"])
    def test_invalid_name(self, session: ProjectSession, name: str) -> None:
        with pytest.raises(ExportError, match="Invalid export name"):
            export_value(session, 0, "color", name)

    def test_duplicate_name(self, session: ProjectSession) -> None:
        export_value(session, 0, "color", "brand")
        with pytest.raises(ExportError, match="already exists"):
            export_value(session, 1, "color", "brand")


class TestLink:
    def test_inline_source(self, session: ProjectSession) -> None:
        result = link_params(session, 0, "radius", 1, "radius")
        assert result["reference"] == "radius_0"
        a = session.layers()[0].find("param[@name='radius']")
        b = session.layers()[1].find("param[@name='radius']")
        assert a is not None and a.get("use") == ":radius_0"
        assert b is not None and b.get("use") == "radius_0"

    def test_explicit_export_name(self, session: ProjectSession) -> None:
        result = link_params(session, 0, "radius", 1, "radius", export_name="shared")
        assert result["reference"] == "shared"

    def test_unique_name(self, session: ProjectSession) -> None:
        export_value(session, 0, "radius", "shared")
        result = link_params(session, 1, "radius", 0, "radius", export_name="shared")
        assert result["reference"] == "shared2"

    def test_exported_source(self, session: ProjectSession) -> None:
        export_value(session, 0, "radius", "shared")
        result = link_params(session, 0, "radius", 1, "radius")
        assert result["reference"] == "shared"

    def test_external_reference_source(self, session: ProjectSession) -> None:
        param = session.layers()[0].find("param[@name='radius']")
        assert param is not None
        param.set("use", "external")
        result = link_params(session, 0, "radius", 1, "radius")
        assert result["reference"] == "external"

    def test_source_missing(self, session: ProjectSession) -> None:
        with pytest.raises(ExportError, match="Source parameter"):
            link_params(session, 0, "nope", 1, "radius")

    def test_source_empty(self, session: ProjectSession) -> None:
        param = etree.SubElement(session.layers()[0], "param", name="empty")
        assert param is not None
        with pytest.raises(ExportError, match="no value"):
            link_params(session, 0, "empty", 1, "radius")

    def test_destination_missing(self, session: ProjectSession) -> None:
        with pytest.raises(ExportError, match="Destination parameter"):
            link_params(session, 0, "radius", 1, "missing")


class TestUnlink:
    def test_unlink(self, session: ProjectSession) -> None:
        export_value(session, 0, "color", "brand")
        result = unlink_params(session, 0, "color")
        assert result["unlinked_from"] == ":brand"
        param = session.layers()[0].find("param[@name='color']")
        assert param is not None
        assert param.get("use") is None
        assert param.find("color") is not None
        assert find_defs_entry(session.root, "brand") is not None

    def test_missing_param(self, session: ProjectSession) -> None:
        with pytest.raises(ExportError, match="not found"):
            unlink_params(session, 0, "nope")

    def test_not_a_reference(self, session: ProjectSession) -> None:
        with pytest.raises(ExportError, match="not a reference"):
            unlink_params(session, 0, "color")

    def test_missing_defs_entry(self, session: ProjectSession) -> None:
        param = session.layers()[0].find("param[@name='color']")
        assert param is not None
        for child in list(param):
            param.remove(child)
        param.set("use", ":missing")
        with pytest.raises(ExportError, match="not found"):
            unlink_params(session, 0, "color")
