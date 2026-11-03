# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for layer tree operations."""

from __future__ import annotations

import pytest
from lxml import etree

from synfig_mcp.document.layers import (
    clone_layer,
    get_param,
    get_param_or_none,
    insert_layer,
    layer_index,
    layer_summary,
    list_layers,
    move_layer,
    remove_layer,
    set_active,
    set_amount,
    set_blend_method,
    set_exclude_from_rendering,
    set_hit_locked,
    set_or_create_param,
    set_z_depth,
)
from synfig_mcp.errors import LayerNotFoundError

PAYLOAD = """<canvas>
  <layer type="circle" desc="Ball" active="false">
    <param name="name"><string>Ball</string></param>
    <param name="amount"><real value="0.5"/></param>
    <param name="blend_method"><integer value="6"/></param>
    <param name="z_depth"><real value="1.5"/></param>
    <param name="canvas"><canvas><layer type="star" desc="Nested"/></canvas></param>
  </layer>
  <layer type="rectangle"/>
</canvas>"""


@pytest.fixture
def root() -> etree._Element:
    return etree.fromstring(PAYLOAD)


class TestList:
    def test_list(self, root: etree._Element) -> None:
        items = list_layers(root)
        assert len(items) == 3
        assert items[0]["name"] == "Ball"
        assert items[0]["active"] is False
        assert items[0]["amount"] == 0.5
        assert items[0]["blend_method_name"] == "multiply"
        assert items[1]["depth"] == 1
        assert items[1]["path"] == [0, 0]

    def test_list_hidden_params(self, root: etree._Element) -> None:
        items = list_layers(root, include_hidden_params=True)
        assert items[0]["params"]

    def test_attributes(self, root: etree._Element) -> None:
        root[0].set("exclude_from_rendering", "true")
        root[0].set("hit_locked", "true")
        root[0].set("group", "g")
        item = list_layers(root)[0]
        assert item["exclude_from_rendering"] is True
        assert item["hit_locked"] is True
        assert item["group"] == "g"


class TestParams:
    def test_get_param(self, root: etree._Element) -> None:
        assert get_param(root[0], "amount").get("name") == "amount"
        assert get_param_or_none(root[0], "missing") is None
        with pytest.raises(LayerNotFoundError):
            get_param(root[0], "missing")

    def test_set_or_create_replaces_and_keeps_attrs(self, root: etree._Element) -> None:
        param = get_param(root[0], "amount")
        param.set("static", "true")
        new = set_or_create_param(root[0], "amount", 0.75)
        assert new.get("static") == "true"
        assert float(new.find("real").get("value")) == 0.75  # type: ignore[union-attr]
        assert len(root[0].findall("param[@name='amount']")) == 1

    def test_set_or_create_new(self, root: etree._Element) -> None:
        param = set_or_create_param(root[0], "radius", 0.5)
        assert param.get("name") == "radius"
        assert param[0].tag == "real"

    def test_set_or_create_reference(self, root: etree._Element) -> None:
        param = set_or_create_param(root[0], "color", None, reference=":brand")
        assert param.get("use") == ":brand"

    def test_set_or_create_on_reference(self, root: etree._Element) -> None:
        param = set_or_create_param(root[0], "x", None, reference=":ref")
        assert param.get("use") == ":ref"

    def test_param_preserves_existing_type(self, root: etree._Element) -> None:
        param = set_or_create_param(root[0], "amount", 2)
        assert param[0].tag == "real"


class TestMutators:
    def test_amount_clamped(self, root: etree._Element) -> None:
        set_amount(root[1], 5)
        assert float(get_param(root[1], "amount").find("real").get("value")) == 1.0  # type: ignore[union-attr]
        set_amount(root[1], -1)
        assert float(get_param(root[1], "amount").find("real").get("value")) == 0.0  # type: ignore[union-attr]

    def test_blend_and_depth(self, root: etree._Element) -> None:
        set_blend_method(root[1], 6)
        assert get_param(root[1], "blend_method").find("integer").get("value") == "6"  # type: ignore[union-attr]
        set_z_depth(root[1], 2.5)
        assert float(get_param(root[1], "z_depth").find("real").get("value")) == 2.5  # type: ignore[union-attr]

    def test_flags(self, root: etree._Element) -> None:
        set_active(root[1], False)
        assert root[1].get("active") == "false"
        set_exclude_from_rendering(root[1], True)
        assert root[1].get("exclude_from_rendering") == "true"
        set_hit_locked(root[1], True)
        assert root[1].get("hit_locked") == "true"
        set_hit_locked(root[1], False)
        assert root[1].get("hit_locked") is None

    def test_summary(self, root: etree._Element) -> None:
        summary = layer_summary(root[0])
        assert summary["type"] == "circle"
        assert summary["z_depth"] == 1.5
        assert layer_summary(root[1])["amount"] is None

    def test_clone_is_deep(self, root: etree._Element) -> None:
        clone = clone_layer(root[0])
        clone.set("desc", "Copy")
        assert root[0].get("desc") == "Ball"


class TestOrder:
    def test_index(self, root: etree._Element) -> None:
        assert layer_index(root, root[0]) == 0
        assert layer_index(root, root[1]) == 1

    def test_insert(self, root: etree._Element) -> None:
        layer = etree.Element("layer", type="star")
        assert insert_layer(root, layer) == 2
        assert layer_index(root, layer) == 2
        layer2 = etree.Element("layer", type="star")
        assert insert_layer(root, layer2, 0) == 0
        assert layer_index(root, layer2) == 0
        layer3 = etree.Element("layer", type="star")
        assert insert_layer(root, layer3, 2) == 2
        with pytest.raises(LayerNotFoundError):
            insert_layer(root, etree.Element("layer"), 99)

    def test_move(self, root: etree._Element) -> None:
        target = root[0]
        assert move_layer(root, target, 1) == 1
        assert layer_index(root, target) == 1
        with pytest.raises(LayerNotFoundError):
            move_layer(root, target, 99)

    def test_remove(self, root: etree._Element) -> None:
        remove_layer(root, root[0])
        assert len([c for c in root if c.tag == "layer"]) == 1
