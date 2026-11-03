# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for skeleton bone storage and binding."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from synfig_mcp.config import Settings
from synfig_mcp.document import io
from synfig_mcp.document.bones import (
    bind_skeleton,
    bones_section,
    create_bone,
    ensure_root_bone,
    is_guid,
    list_bones,
    set_bone_param,
)
from synfig_mcp.document.model import ProjectSession
from synfig_mcp.errors import ExportError, ParameterError

XML = """<canvas width="100" height="100">
  <name>bones</name>
  <layer type="circle" desc="Body">
    <param name="origin"><vector><x>0</x><y>0</y></vector></param>
  </layer>
</canvas>"""


@pytest.fixture
def session(tmp_path: Path) -> ProjectSession:
    return ProjectSession(
        io.parse_sif(XML.encode()), settings=Settings(workspace=tmp_path), name="bones"
    )


class TestSection:
    def test_create_placement(self, session: ProjectSession) -> None:
        section = bones_section(session.root, create=True)
        assert section is not None
        tags = [child.tag for child in session.root]
        assert tags.index("bones") < tags.index("layer")

    def test_append_without_anchor(self, tmp_path: Path) -> None:
        tree = io.parse_sif(b"<canvas/>")
        session = ProjectSession(tree, settings=Settings(workspace=tmp_path))
        section = bones_section(session.root, create=True)
        assert section is not None
        assert list(session.root)[-1] is section

    def test_get_without_create(self, session: ProjectSession) -> None:
        assert bones_section(session.root) is None

    def test_root_bone(self, session: ProjectSession) -> None:
        guid = ensure_root_bone(session.root)
        assert is_guid(guid)
        assert ensure_root_bone(session.root) == guid
        section = bones_section(session.root)
        assert section is not None
        assert section.find("bone_root").get("type") == "bone_object"  # type: ignore[union-attr]

    def test_root_bone_missing_guid(self, session: ProjectSession) -> None:
        section = bones_section(session.root, create=True)
        assert section is not None
        etree.SubElement(section, "bone_root")
        assert is_guid(ensure_root_bone(session.root))


class TestCreate:
    def test_default(self, session: ProjectSession) -> None:
        result = create_bone(session, "spine")
        assert result["name"] == "spine"
        assert is_guid(result["guid"])
        info = list_bones(session.root)[0]
        assert info["name"] == "spine"
        assert info["id"] == "spine"
        assert info["origin"] == {"x": 0.0, "y": 0.0}
        assert info["parent_guid"] == result["parent_guid"]

    def test_full_params_and_parent(self, session: ProjectSession) -> None:
        parent = create_bone(
            session,
            "root",
            origin=[1.0, 2.0],
            angle=45.0,
            length=2.0,
            width=0.4,
            tipwidth=0.2,
            scalelx=1.2,
            scalex=0.8,
            bone_depth=0.5,
        )
        child = create_bone(session, "arm", parent="root", origin={"x": 0.5, "y": 0.5})
        assert child["parent_guid"] == parent["guid"]
        info = list_bones(session.root)[1]
        assert info["angle"] == 0.0
        root_info = list_bones(session.root)[0]
        assert root_info["angle"] == 45.0
        assert root_info["length"] == 2.0
        assert root_info["width"] == 0.4
        assert root_info["scalelx"] == 1.2

    def test_no_export(self, session: ProjectSession) -> None:
        result = create_bone(session, "hidden", export=False)
        assert result["export"] is False
        assert list_bones(session.root)[0]["id"] is None

    def test_duplicate(self, session: ProjectSession) -> None:
        create_bone(session, "spine")
        with pytest.raises(ParameterError, match="already exists"):
            create_bone(session, "spine")

    @pytest.mark.parametrize("name", ["", " ", "a b", "a:b", "a#b"])
    def test_invalid_name(self, session: ProjectSession, name: str) -> None:
        with pytest.raises(ParameterError, match="Invalid bone name"):
            create_bone(session, name)

    def test_missing_parent(self, session: ProjectSession) -> None:
        with pytest.raises(ParameterError, match="Parent bone"):
            create_bone(session, "arm", parent="missing")

    def test_empty_list(self, session: ProjectSession) -> None:
        assert list_bones(session.root) == []
        assert list_bones(etree.fromstring("<canvas/>")) == []

    def test_default_values_for_minimal_bone(self, session: ProjectSession) -> None:
        section = bones_section(session.root, create=True)
        assert section is not None
        section.append(etree.fromstring('<bone id="x" guid="G"/>'))
        info = list_bones(session.root)[0]
        assert info["name"] is None
        assert info["angle"] == 0.0
        assert info["width"] == 0.3
        assert info["length"] == 1.0


class TestSetParam:
    def test_all_params(self, session: ProjectSession) -> None:
        create_bone(session, "spine")
        create_bone(session, "arm")
        assert set_bone_param(session, "spine", "name", "torso")["param"] == "name"
        assert list_bones(session.root)[0]["name"] == "torso"
        set_bone_param(session, "torso", "origin", [1.0, 2.0])
        assert list_bones(session.root)[0]["origin"] == {"x": 1.0, "y": 2.0}
        set_bone_param(session, "torso", "angle", 30.0)
        assert list_bones(session.root)[0]["angle"] == 30.0
        for key in ("scalelx", "scalex", "width", "tipwidth", "bone_depth", "length"):
            set_bone_param(session, "torso", key, 2.0)
        info = list_bones(session.root)[0]
        assert info["scalelx"] == 2.0
        assert info["length"] == 2.0
        set_bone_param(session, "torso", "parent", "arm")
        assert list_bones(session.root)[0]["parent_guid"] == list_bones(session.root)[1]["guid"]

    def test_creates_missing_nodes(self, session: ProjectSession) -> None:
        create_bone(session, "spine")
        bone = bones_section(session.root).find("bone")  # type: ignore[union-attr]
        for child in list(bone):
            if child.tag in {"origin", "angle"}:
                bone.remove(child)
        set_bone_param(session, "spine", "origin", [0.0, 0.0])
        set_bone_param(session, "spine", "angle", 10.0)
        assert list_bones(session.root)[0]["angle"] == 10.0

    def test_missing_bone(self, session: ProjectSession) -> None:
        with pytest.raises(ParameterError, match="not found"):
            set_bone_param(session, "nope", "angle", 1.0)

    def test_unknown_param(self, session: ProjectSession) -> None:
        create_bone(session, "spine")
        with pytest.raises(ParameterError, match="Unknown bone parameter"):
            set_bone_param(session, "spine", "colour", 1.0)

    def test_invalid_rename(self, session: ProjectSession) -> None:
        create_bone(session, "spine")
        with pytest.raises(ParameterError, match="Invalid bone name"):
            set_bone_param(session, "spine", "name", "a b")

    def test_missing_parent(self, session: ProjectSession) -> None:
        create_bone(session, "spine")
        with pytest.raises(ParameterError, match="Parent bone"):
            set_bone_param(session, "spine", "parent", "nope")

    def test_find_by_guid(self, session: ProjectSession) -> None:
        result = create_bone(session, "spine")
        assert set_bone_param(session, result["guid"], "angle", 5.0)["bone"] == result["guid"]


class TestBind:
    def test_bind(self, session: ProjectSession) -> None:
        create_bone(session, "a")
        create_bone(session, "b")
        result = bind_skeleton(session, 0, "origin", ["a", "b"], weights=[0.75, 0.25])
        assert result["type"] == "vector"
        assert result["bones"] == [{"ref": "a", "weight": 0.75}, {"ref": "b", "weight": 0.25}]
        param = session.layers()[0].find("param[@name='origin']")
        assert param is not None
        influence = param.find("boneinfluence")
        assert influence is not None
        assert influence.find("bone_weight_list") is not None
        assert influence.find("link/vector") is not None

    def test_default_weights(self, session: ProjectSession) -> None:
        create_bone(session, "a")
        result = bind_skeleton(session, 0, "origin", ["a"])
        assert result["bones"][0]["weight"] == 1.0

    def test_no_bones(self, session: ProjectSession) -> None:
        with pytest.raises(ParameterError, match="at least one"):
            bind_skeleton(session, 0, "origin", [])

    def test_missing_param(self, session: ProjectSession) -> None:
        create_bone(session, "a")
        with pytest.raises(ExportError, match="not found"):
            bind_skeleton(session, 0, "nope", ["a"])

    def test_wrong_type(self, session: ProjectSession) -> None:
        create_bone(session, "a")
        etree.SubElement(session.layers()[0], "param", name="real").append(
            etree.fromstring('<real value="1"/>')
        )
        with pytest.raises(ParameterError, match="supports vector"):
            bind_skeleton(session, 0, "real", ["a"])

    def test_reference_param(self, session: ProjectSession) -> None:
        create_bone(session, "a")
        param = etree.SubElement(session.layers()[0], "param", name="ref")
        param.set("use", ":x")
        with pytest.raises(ParameterError, match="reference"):
            bind_skeleton(session, 0, "ref", ["a"])

    def test_weight_mismatch(self, session: ProjectSession) -> None:
        create_bone(session, "a")
        with pytest.raises(ParameterError, match="same length"):
            bind_skeleton(session, 0, "origin", ["a"], weights=[1.0, 2.0])

    def test_missing_bone(self, session: ProjectSession) -> None:
        with pytest.raises(ParameterError, match="not found"):
            bind_skeleton(session, 0, "origin", ["nope"])

    def test_guid_validation(self) -> None:
        assert is_guid("A" * 32)
        assert is_guid("a" * 32)
        assert not is_guid("G" * 32)
        assert not is_guid("A" * 31)
