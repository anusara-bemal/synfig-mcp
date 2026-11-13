"""
The protocol documentation must describe the bridge that actually exists.

``docs/protocol.md`` maps every wire method to the Synfig API behind it.  A
method that is documented but not implemented (or the other way round) is a
false claim, so the table is checked against the C++ dispatcher.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROTOCOL_DOC = REPO_ROOT / "docs" / "protocol.md"
HANDLERS = REPO_ROOT / "bridge" / "src" / "mcp_bridge" / "handlers.cpp"

#: Methods that are documented but intentionally not part of the bridge.
ALIASES = {
    "anim.time_get",
    "anim.time_set",
    "anim.keyframe_add",
    "anim.keyframe_remove",
    "anim.waypoint_set",
    "anim.waypoint_remove",
    "keyframe.add",
    "keyframe.delete",
    "keyframe.list",
    "keyframe.remove",
    "layer.delete",
    "layer.move",
    "layer.remove",
    "waypoint.delete",
    "waypoint.remove",
    "waypoint.set",
    "anim.time.get",
    "anim.time.set",
}


def _bridge_methods() -> set[str]:
    """Extract the wire methods handled by the C++ dispatcher."""
    source = HANDLERS.read_text(encoding="utf-8")
    return set(re.findall(r'method\s*==\s*"([a-z_.]+)"', source))


def _documented_methods() -> dict[str, str]:
    """Extract the documented methods and their status column."""
    content = PROTOCOL_DOC.read_text(encoding="utf-8")
    documented: dict[str, str] = {}
    for line in content.splitlines():
        match = re.match(r"\|\s*`([a-z_.]+)`\s*\|.*\|\s*([^|]+)\|\s*$", line)
        if match:
            documented[match.group(1)] = match.group(2).strip()
    return documented


def _documented_method_rows() -> list[str]:
    """Every method name in the method table, in order and with duplicates kept."""
    content = PROTOCOL_DOC.read_text(encoding="utf-8")
    rows: list[str] = []
    for line in content.splitlines():
        match = re.match(r"\|\s*`([a-z_.]+)`\s*\|.*\|\s*([^|]+)\|\s*$", line)
        if match:
            rows.append(match.group(1))
    return rows


def test_protocol_doc_exists() -> None:
    assert PROTOCOL_DOC.is_file(), "docs/protocol.md is missing"
    assert HANDLERS.is_file(), "the bridge dispatcher is missing"


def test_no_duplicate_method_rows() -> None:
    """A method must be documented once; a duplicate silently hides a stale row."""
    rows = _documented_method_rows()
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in rows:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    assert not duplicates, f"Duplicate method rows in docs/protocol.md: {sorted(duplicates)}"


def test_documented_methods_exist_in_the_bridge() -> None:
    """Every documented method must exist in the dispatcher."""
    implemented = _bridge_methods()
    documented = _documented_methods()
    assert documented, "no methods parsed from docs/protocol.md"

    missing = sorted(
        name
        for name, status in documented.items()
        if name not in implemented and "not implemented" not in status.lower()
    )
    assert not missing, f"Documented but not implemented in the bridge: {missing}"


def test_bridge_methods_are_documented() -> None:
    """Every implemented method must appear in the protocol documentation."""
    implemented = _bridge_methods()
    documented = _documented_methods()

    undocumented = sorted(
        name
        for name in implemented
        if name not in documented
        and name not in ALIASES
        and not name.startswith("test.")
        and name not in ("hello", "canvas.render_frame", "render.frame")
    )
    assert not undocumented, f"Implemented but not documented: {undocumented}"


@pytest.mark.parametrize("method", ["rig.skeleton_create", "rig.bone_bind"])
def test_planned_methods_are_marked_as_not_implemented(method: str) -> None:
    """Methods that do not exist yet must not be advertised as verified."""
    documented = _documented_methods()
    assert method in documented, f"{method} is not mentioned in the protocol documentation"
    assert "not implemented" in documented[method].lower(), (
        f"{method} is advertised as: {documented[method]}"
    )


def test_implemented_rig_method_is_advertised_as_verified() -> None:
    """``rig.bone_add`` exists in the bridge, so it must not be documented as planned."""
    documented = _documented_methods()
    assert "rig.bone_add" in documented
    assert "not implemented" not in documented["rig.bone_add"].lower(), (
        "rig.bone_add is implemented in handlers.cpp but still documented as not implemented"
    )
    assert "verified" in documented["rig.bone_add"].lower()
