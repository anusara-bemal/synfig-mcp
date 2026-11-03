# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""In-memory project session: tree navigation, dirty tracking, undo/redo.

The tree is never rebuilt from a typed mirror — every mutation edits the
lxml tree directly, which is what makes round-trips lossless.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from lxml import etree

from ..config import Settings
from ..errors import HistoryError, LayerNotFoundError
from . import io

LAYER_INDEX_ATTR = "data-mcp-layer-index"  # never written to disk; indices are computed on demand


class ReentrantLock:
    """Async lock that a single task can re-enter.

    Batch tool execution nests tool calls inside a session lock (one outer
    acquisition in ``batch_operations``, one per inner tool). A plain
    ``asyncio.Lock`` would deadlock there, so ownership is tracked per task.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner: asyncio.Task[Any] | None = None
        self._depth = 0

    async def __aenter__(self) -> ReentrantLock:
        task = asyncio.current_task()
        if task is not None and self._owner is task:
            self._depth += 1
            return self
        await self._lock.acquire()
        self._owner = task
        self._depth = 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        task = asyncio.current_task()
        if self._owner is not task:
            raise RuntimeError("ReentrantLock released by a task that does not own it")
        self._depth -= 1
        if self._depth == 0:
            self._owner = None
            self._lock.release()

    def locked(self) -> bool:
        return self._lock.locked()


class ProjectSession:
    """One open project, its tree, lock, dirty flag and undo/redo history."""

    def __init__(
        self,
        tree: etree._ElementTree,
        *,
        settings: Settings,
        project_id: str | None = None,
        path: Path | None = None,
        name: str | None = None,
    ) -> None:
        self.settings = settings
        self.tree = tree
        self.project_id = project_id or uuid.uuid4().hex[:12]
        self.path = path
        self._name = name or self._read_name()
        self.dirty = False
        self.lock = ReentrantLock()
        self.batch_depth = 0  # >0 while a batch_operations run is in flight
        self._undo: deque[bytes] = deque(maxlen=settings.history_depth)
        self._redo: deque[bytes] = deque(maxlen=settings.history_depth)

    # -- identity ---------------------------------------------------------
    @property
    def name(self) -> str:
        return self._name

    def _read_name(self) -> str:
        root = self.tree.getroot()
        node = root.find("name")
        return (
            (node.text or "synfig-project").strip()
            if node is not None and node.text
            else "synfig-project"
        )

    def set_name(self, name: str) -> None:
        root = self.tree.getroot()
        node = root.find("name")
        if node is None:
            node = etree.Element("name")
            root.insert(0, node)
        node.text = name
        self._name = name
        self.touch()

    # -- tree access -------------------------------------------------------
    @property
    def root(self) -> etree._Element:
        return self.tree.getroot()

    def touch(self) -> None:
        self.dirty = True

    def canvas_id(self) -> str | None:
        value = self.root.get("id")
        return str(value) if value is not None else None

    def defs(self, *, create: bool = False) -> etree._Element | None:
        root = self.root
        defs = root.find("defs")
        if defs is None and create:
            defs = etree.Element("defs")
            # Insert defs before the first layer (or at the end if no layers).
            insert_at = len(root)
            for index, child in enumerate(root):
                if child.tag == "layer":
                    insert_at = index
                    break
            root.insert(insert_at, defs)
        return defs

    def layers(self) -> list[etree._Element]:
        """Top-level layers of the root canvas, in document (paint) order."""
        return [child for child in self.root if child.tag == "layer"]

    def all_layers(self) -> list[tuple[tuple[int, ...], etree._Element]]:
        """All layers including nested canvases, with path indices."""
        out: list[tuple[tuple[int, ...], etree._Element]] = []

        def walk(canvas_el: etree._Element, prefix: tuple[int, ...]) -> None:
            top = [child for child in canvas_el if child.tag == "layer"]
            for index, layer in enumerate(top):
                path = (*prefix, index)
                out.append((path, layer))
                for sub in layer.iter("canvas"):
                    if sub is not layer:
                        walk(sub, path)
                        break  # only the layer's own canvas children matter here

        walk(self.root, ())
        return out

    def layer_by_index(self, index: int) -> etree._Element:
        layers = self.layers()
        if index < 0 or index >= len(layers):
            raise LayerNotFoundError(
                index,
                suggestions=[f"index {i}" for i in range(max(0, len(layers) - 3), len(layers))]
                or None,
            )
        return layers[index]

    def layer_by_name(self, name: str) -> etree._Element:
        layers = self.layers()
        matches = [layer for layer in layers if layer_display_name(layer) == name]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return matches[0]  # first match wins; callers may disambiguate by index
        names = [layer_display_name(layer) for layer in layers]
        from difflib import get_close_matches

        close = get_close_matches(name, names, n=3, cutoff=0.4)
        raise LayerNotFoundError(name, suggestions=close)

    def resolve_layer(self, ref: str | int) -> tuple[int, etree._Element]:
        if isinstance(ref, bool):  # bool is int subclass; treat as index
            ref = int(ref)
        if isinstance(ref, int):
            return ref, self.layer_by_index(ref)
        text = str(ref).strip()
        if text.lstrip("-").isdigit():
            index = int(text)
            return index, self.layer_by_index(index)
        layer = self.layer_by_name(text)
        return self.layers().index(layer), layer

    # -- history -------------------------------------------------------------
    def snapshot(self) -> bytes:
        return io.serialize(self.tree)

    def record_history(self, snapshot: bytes | None = None) -> None:
        # Nested history recording (e.g. inside batch_operations) is suppressed;
        # the batch records a single snapshot of its pre-state itself.
        if self.batch_depth > 0:
            return
        self._undo.append(snapshot if snapshot is not None else self.snapshot())
        self._redo.clear()

    def undo(self) -> str:
        if not self._undo:
            raise HistoryError(
                "Nothing to undo.", hint="No prior mutation recorded for this project."
            )
        self._redo.append(self.snapshot())
        payload = self._undo.pop()
        self._restore(payload)
        return "undo"

    def redo(self) -> str:
        if not self._redo:
            raise HistoryError("Nothing to redo.", hint="No undone mutation to re-apply.")
        self._undo.append(self.snapshot())
        payload = self._redo.pop()
        self._restore(payload)
        return "redo"

    def _restore(self, payload: bytes) -> None:
        self.tree = io.parse_sif(payload, source="<undo snapshot>")
        self._name = self._read_name()
        self.touch()

    def clear_history(self) -> None:
        self._undo.clear()
        self._redo.clear()

    # -- info ------------------------------------------------------------------
    def info(self) -> dict[str, Any]:
        root = self.root
        layers = self.layers()
        keyframes = root.findall("keyframe")
        return {
            "project_id": self.project_id,
            "name": self.name,
            "path": str(self.path) if self.path else None,
            "dirty": self.dirty,
            "width": int(root.get("width", "0") or 0),
            "height": int(root.get("height", "0") or 0),
            "fps": float(root.get("fps", "24") or 24),
            "begin_time": root.get("begin-time"),
            "end_time": root.get("end-time"),
            "layer_count": len(layers),
            "total_layer_count": sum(1 for _ in root.iter("layer")),
            "keyframe_count": len(keyframes),
            "version": root.get("version"),
            "view_box": root.get("view-box"),
            "antialias": int(root.get("antialias", "1") or 1),
            "gamma": (
                float(root.get("gamma-r", "1") or 1),
                float(root.get("gamma-g", "1") or 1),
                float(root.get("gamma-b", "1") or 1),
            ),
            "bgcolor": root.get("bgcolor"),
        }


def layer_display_name(layer: etree._Element) -> str:
    desc = layer.get("desc")
    if desc:
        return str(desc)
    for param in layer.findall("param"):
        if param.get("name") == "name" and len(param):
            text = (param[0].text or "").strip()
            if text:
                return text
    return str(layer.get("type") or "layer")
