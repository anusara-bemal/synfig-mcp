"""
Parameter type table for every Synfig layer type.

The table is produced by ``scripts/introspect_param_types.py`` which asks the
patched Synfig Studio for the value type of every parameter.  It is checked
into the repository so the schema tools report accurate types even when no
Synfig binary is available, and it is validated against the binary by
``server/tests/unit/test_schema_registry.py``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

#: Value types the MCP can read and write.
WRITABLE_VALUE_TYPES: frozenset[str] = frozenset(
    {
        "real",
        "integer",
        "bool",
        "string",
        "angle",
        "time",
        "color",
        "vector",
        "gradient",
    }
)

#: Complex value types that Synfig stores as spline/point lists.
COMPLEX_VALUE_TYPES: frozenset[str] = frozenset(
    {"list", "transformation", "bline_point_list", "width_point_list", "dash_item_list"}
)

_PARAM_TYPES_FILE = Path(__file__).with_name("param_types.json")


@lru_cache(maxsize=1)
def load_param_types() -> dict[str, dict[str, str]]:
    """Return the introspected ``{layer_type: {param: value_type}}`` table."""
    if not _PARAM_TYPES_FILE.is_file():
        return {}
    try:
        data = json.loads(_PARAM_TYPES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        layer: {param: str(value) for param, value in params.items()}
        for layer, params in data.items()
        if isinstance(params, dict)
    }


def is_writable(value_type: str) -> bool:
    """Return whether the MCP can write values of the given Synfig type."""
    return value_type.lower() in WRITABLE_VALUE_TYPES


def is_editable_param(param_name: str, value_type: str) -> bool:
    """Return whether the MCP can write the given parameter.

    ``bline`` holds spline points and is written as a ``<bline>`` element, so it
    is editable even though Synfig reports its type as the generic ``list``.
    """
    if is_writable(value_type):
        return True
    return value_type.lower() == "list" and param_name == "bline"
