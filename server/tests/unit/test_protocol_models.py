"""
The wire format of the bridge must match the Python value models.

The bridge and the MCP server are two halves of one contract: whatever
``valuebase_to_json`` produces has to validate against the ``SynfigValue``
models, otherwise every call that touches that value type fails with an
obscure validation error instead of returning data.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from synfig_mcp.protocol.models import SynfigValue

adapter: TypeAdapter[SynfigValue] = TypeAdapter(SynfigValue)


def test_gradient_wire_format_validates() -> None:
    """The format the bridge returns for a gradient must validate."""
    payload = {
        "type": "gradient",
        "cpoints": [
            {"pos": 0.0, "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}},
            {"pos": 1.0, "color": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}},
        ],
    }
    value = adapter.validate_python(payload)
    assert value.type == "gradient"
    assert len(value.cpoints) == 2


def test_gradient_documented_format_matches_the_model() -> None:
    """docs/protocol.md and the model must describe the same spelling."""
    from pathlib import Path

    protocol = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "protocol.md"
    content = protocol.read_text(encoding="utf-8")
    assert '"cpoints"' in content, "the protocol does not document the gradient format"


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "real", "value": 1.5},
        {"type": "integer", "value": 3},
        {"type": "bool", "value": True},
        {"type": "string", "value": "text"},
        {"type": "angle", "degrees": 45.0},
        {"type": "time", "seconds": 1.5},
        {"type": "color", "r": 1.0, "g": 0.5, "b": 0.0, "a": 1.0},
        {"type": "vector", "x": 1.0, "y": 2.0, "unit": "synfig"},
        {"type": "canvas_ref", "canvas_id": ":root"},
        {"type": "valuenode_link", "link_id": "shared"},
    ],
)
def test_basic_wire_formats_validate(payload: dict[str, object]) -> None:
    """Every basic value type of the bridge must validate against the model."""
    assert adapter.validate_python(payload).type == payload["type"]


def test_spline_wire_format_validates() -> None:
    """The spline point list format must validate as well."""
    payload = {
        "type": "bline_point_list",
        "points": [
            {
                "vertex": (-1.0, 0.0),
                "t1": (0.0, 0.0),
                "t2": (0.0, 0.0),
                "width": 1.0,
                "origin": 0.5,
                "split": False,
            }
        ],
    }
    value = adapter.validate_python(payload)
    assert value.type == "bline_point_list"
