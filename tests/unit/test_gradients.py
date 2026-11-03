# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for gradient defs and binding."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from synfig_mcp.config import Settings
from synfig_mcp.document import io
from synfig_mcp.document.gradients import (
    assign_gradient,
    create_gradient_def,
    delete_gradient_def,
    list_gradients,
    new_inline_gradient,
    upsert_gradient,
)
from synfig_mcp.document.model import ProjectSession
from synfig_mcp.errors import ParameterError

STOPS = [{"pos": 0.0, "color": "#000000"}, {"pos": 1.0, "color": "#ffffff"}]

XML = """<canvas width="100" height="100">
  <name>gradients</name>
  <layer type="linear_gradient" desc="Background"><param name="gradient"><gradient/></param></layer>
</canvas>"""


@pytest.fixture
def session(tmp_path: Path) -> ProjectSession:
    return ProjectSession(
        io.parse_sif(XML.encode()), settings=Settings(workspace=tmp_path), name="gradients"
    )


class TestDefs:
    def test_empty(self, session: ProjectSession) -> None:
        assert list_gradients(session.root) == []
        assert delete_gradient_def(session, "x") is False

    def test_create(self, session: ProjectSession) -> None:
        result = create_gradient_def(session, "brand", STOPS)
        assert result["id"] == "brand"
        assert result["replaced"] is False
        assert len(result["stops"]) == 2
        assert list_gradients(session.root)[0]["kind"] == "gradient"

    def test_duplicate(self, session: ProjectSession) -> None:
        create_gradient_def(session, "brand", STOPS)
        with pytest.raises(ParameterError, match="already exists"):
            create_gradient_def(session, "brand", STOPS)

    def test_upsert_replaces(self, session: ProjectSession) -> None:
        create_gradient_def(session, "brand", STOPS)
        result = upsert_gradient(session, "brand", [{"pos": 0.5, "color": "#ff0000"}], replace=True)
        assert result["replaced"] is True
        assert len(result["stops"]) == 1
        assert len(session.defs().findall("gradient")) == 1  # type: ignore[union-attr]

    @pytest.mark.parametrize("name", ["", "a b", "a:b", "a#b"])
    def test_invalid_id(self, session: ProjectSession, name: str) -> None:
        with pytest.raises(ParameterError, match="Invalid gradient id"):
            upsert_gradient(session, name, STOPS, replace=False)

    def test_delete(self, session: ProjectSession) -> None:
        create_gradient_def(session, "brand", STOPS)
        assert delete_gradient_def(session, "brand") is True
        assert delete_gradient_def(session, "brand") is False

    def test_list_other_kinds(self, session: ProjectSession) -> None:
        defs = session.defs(create=True)
        assert defs is not None
        defs.append(etree.fromstring('<stripes id="s"/>'))
        defs.append(etree.fromstring('<twotone id="t"/>'))
        defs.append(etree.Comment("x"))
        defs.append(etree.fromstring("<gradient/>"))
        kinds = [item["kind"] for item in list_gradients(session.root)]
        assert kinds == ["stripes", "twotone"]

    def test_assign(self, session: ProjectSession) -> None:
        create_gradient_def(session, "brand", STOPS)
        result = assign_gradient(session, 0, "brand")
        assert result == {"layer_index": 0, "gradient": "brand"}
        param = session.layers()[0].find("param[@name='gradient']")
        assert param is not None
        assert param.get("use") == "brand"

    def test_assign_missing(self, session: ProjectSession) -> None:
        with pytest.raises(ParameterError, match="No gradient defs entry"):
            assign_gradient(session, 0, "missing")

    def test_assign_without_defs(self, tmp_path: Path) -> None:
        tree = io.parse_sif(b'<canvas><layer type="linear_gradient"/></canvas>')
        session = ProjectSession(tree, settings=Settings(workspace=tmp_path))
        with pytest.raises(ParameterError):
            assign_gradient(session, 0, "missing")

    def test_inline_gradient_has_guid(self) -> None:
        element = new_inline_gradient(STOPS)
        assert element.get("guid")
        assert len(element.findall("color")) == 2
