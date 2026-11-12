"""
Rig / model sheet auto-generation (Step 3).

``RigSheetGenerator`` lays a rigged character out as a labeled model sheet:
front, three-quarter and side views, plus an exploded legend listing the parts.
The sheet is emitted as ordinary Synfig layers and groups, so it stays editable
in Studio, and it can be rendered to a PNG through the render pipeline.

The views are the same geometry under a horizontal squash (a cut-out "turn"
approximation): 1.0 for front, 0.78 for three-quarter, 0.5 for profile.  This is
honest about being a vector turn, not a re-drawn turnaround.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.cutout import (
    CanvasFrame,
    CompiledRig,
    CutoutCharacter,
    CutoutPart,
    compile_character,
    vector,
)
from synfig_mcp.errors import SynfigError
from synfig_mcp.production.palette import parse_color

#: view name -> (horizontal squash, label)
_VIEWS: list[tuple[str, float, str]] = [
    ("front", 1.0, "FRONT"),
    ("threequarter", 0.78, "3/4"),
    ("side", 0.5, "SIDE"),
]


class RigSheetGenerator:
    """Build a labeled model sheet for one rigged character."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    async def build(
        self,
        character_id: str,
        parts: list[CutoutPart],
        doc_id: str,
        frame: CanvasFrame,
        height: float | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Return a ``scene_build`` spec for the sheet plus its group/label names."""
        layers: list[dict[str, Any]] = []
        groups: list[dict[str, Any]] = []
        view_groups: dict[str, str] = {}
        labels: list[str] = []

        slot = (frame.right - frame.left) / (len(_VIEWS) + 1)
        base_y = frame.bottom + abs(frame.top - frame.bottom) * 0.25

        for index, (view, squash, label) in enumerate(_VIEWS, start=1):
            view_id = f"{character_id}_{view}"
            centre_x = frame.left + slot * index
            character = CutoutCharacter(
                id=view_id,
                parts=parts,
                position={"x": centre_x, "y": base_y},
                height=height,
                z=float(index),
            )
            rig = compile_character(character, frame)
            if squash != 1.0:
                self._squash(rig, squash)
            layers += rig.layers
            groups += rig.groups
            view_groups[view] = rig.root_group
            labels.append(label)

        layers += self._label_layers(frame, title or character_id, labels)
        sheet_id = f"ModelSheet_{character_id}"
        groups.append(
            {
                "id": sheet_id,
                "layer_ids": [*view_groups.values()],
            }
        )
        return {
            "doc_id": doc_id,
            "layers": layers,
            "groups": groups,
            "sheet_group": sheet_id,
            "views": view_groups,
        }

    @staticmethod
    def _squash(rig: CompiledRig, amount: float) -> None:
        """Insert a horizontal stretch into the rig's root group (a fake turn)."""
        layer_id = f"{rig.character_id}_turn"
        rig.layers.append(
            {
                "id": layer_id,
                "type": "stretch",
                "params": {
                    "amount": vector(amount, 1.0),
                    "center": vector(0.0, 0.0),
                },
            }
        )
        for group in rig.groups:
            if group["id"] == rig.root_group:
                group["layer_ids"].append(layer_id)
                break

    @staticmethod
    def _label_layers(frame: CanvasFrame, title: str, labels: list[str]) -> list[dict[str, Any]]:
        """Title and per-view captions, drawn as Synfig text layers."""
        ink = parse_color("#f5f5f5")
        span = abs(frame.top - frame.bottom)
        layers: list[dict[str, Any]] = [
            {
                "id": "sheet_title",
                "type": "text",
                "params": {
                    "text": {"type": "string", "value": title},
                    "origin": vector(frame.left, frame.top - span * 0.05),
                    "size": vector(0.5, 0.5),
                    "color": ink,
                },
            }
        ]
        slot = (frame.right - frame.left) / (len(labels) + 1)
        for index, label in enumerate(labels, start=1):
            layers.append(
                {
                    "id": f"sheet_label_{index}",
                    "type": "text",
                    "params": {
                        "text": {"type": "string", "value": label},
                        "origin": vector(frame.left + slot * index, frame.bottom + span * 0.06),
                        "size": vector(0.3, 0.3),
                        "color": ink,
                    },
                }
            )
        return layers

    async def generate(
        self,
        character_id: str,
        parts: list[CutoutPart],
        doc_id: str,
        coords: str = "pixels",
        height: float | None = None,
        title: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Build the sheet in ``doc_id`` and report the resulting groups."""
        from synfig_mcp.characters.rigging import RiggingEngine

        frame = await RiggingEngine(self.backend).canvas_frame(doc_id, coords=coords)
        spec = await self.build(
            character_id=character_id,
            parts=parts,
            doc_id=doc_id,
            frame=frame,
            height=height,
            title=title,
        )
        result = await self.backend.scene_build(
            spec={"doc_id": doc_id, "layers": spec["layers"], "groups": spec["groups"]},
            dry_run=dry_run,
        )
        if result.get("success") is False:
            raise SynfigError(str(result.get("error", "scene_build rejected the model sheet.")))
        return {
            "success": True,
            "character_id": character_id,
            "doc_id": doc_id,
            "sheet_group": spec["sheet_group"],
            "views": spec["views"],
            "layers": len(spec["layers"]),
            "diff": result.get("diff", {}),
            "dry_run": dry_run,
        }
