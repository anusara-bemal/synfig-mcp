"""
Character Rigging Engine: assembles hierarchical 2D cut-out puppets from part images
or primitives and applies poses and motion cycles to their joints.

The geometry and the motion library live in ``characters.cutout``; this module
talks to the backend and remembers the rigs it has built.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.cutout import (
    CanvasFrame,
    CompiledRig,
    CutoutCharacter,
    CutoutPart,
    MotionAction,
    MotionPlan,
    RigPart,
    angle,
    attach_waypoints,
    compile_character,
    infer_role,
    motion_catalog,
    plan_actions,
    resolve_part,
)
from synfig_mcp.characters.models import CharacterRigSpec, PosePreset
from synfig_mcp.errors import DocumentNotFoundError, SynfigError
from synfig_mcp.errors import ValidationError as SpecError

# Standard anatomical pose presets
STANDARD_POSES: dict[str, PosePreset] = {
    "idle": PosePreset(
        name="idle",
        bone_angles={
            "bone_root": 0.0,
            "bone_spine": 0.0,
            "bone_head": 0.0,
            "bone_arm_l": 15.0,
            "bone_arm_r": -15.0,
            "bone_leg_l": 0.0,
            "bone_leg_r": 0.0,
        },
        part_swaps={"mouth": "neutral", "eyes": "open"},
    ),
    "punch": PosePreset(
        name="punch",
        bone_angles={
            "bone_root": -10.0,
            "bone_spine": -15.0,
            "bone_head": 10.0,
            "bone_arm_r": 85.0,  # extended forward
            "bone_arm_l": -45.0,  # cocked back
            "bone_leg_l": -25.0,
            "bone_leg_r": 35.0,
        },
        part_swaps={"mouth": "open_grit", "eyes": "narrow"},
    ),
    "jump": PosePreset(
        name="jump",
        bone_angles={
            "bone_root": 0.0,
            "bone_spine": 10.0,
            "bone_head": -10.0,
            "bone_arm_l": 110.0,  # arms raised
            "bone_arm_r": 110.0,
            "bone_leg_l": 45.0,  # legs bent
            "bone_leg_r": 45.0,
        },
        part_swaps={"mouth": "open", "eyes": "wide"},
    ),
    "walk_contact": PosePreset(
        name="walk_contact",
        bone_angles={
            "bone_root": 0.0,
            "bone_spine": 5.0,
            "bone_head": -5.0,
            "bone_arm_l": -30.0,
            "bone_arm_r": 30.0,
            "bone_leg_l": 35.0,
            "bone_leg_r": -35.0,
        },
        part_swaps={"mouth": "neutral", "eyes": "open"},
    ),
    "walk_passing": PosePreset(
        name="walk_passing",
        bone_angles={
            "bone_root": 0.0,
            "bone_spine": 0.0,
            "bone_head": 0.0,
            "bone_arm_l": 5.0,
            "bone_arm_r": -5.0,
            "bone_leg_l": 0.0,
            "bone_leg_r": 10.0,
        },
        part_swaps={"mouth": "neutral", "eyes": "open"},
    ),
}


#: Bone names of the legacy pose presets -> body roles of the rig.
_BONE_ROLES = {
    "bone_spine": "torso",
    "bone_head": "head",
    "bone_arm_l": "upper_arm_l",
    "bone_arm_r": "upper_arm_r",
    "bone_leg_l": "upper_leg_l",
    "bone_leg_r": "upper_leg_r",
}

#: Rigs built by this server process: (doc_id, character_id) -> rig.
_RIGS: dict[tuple[str, str], CompiledRig] = {}


def remember_rig(doc_id: str, rig: CompiledRig) -> None:
    """Keep a built rig so that later pose and motion calls can address its joints."""
    _RIGS[(doc_id, rig.character_id)] = rig


def _legacy_to_cutout(rig_spec: CharacterRigSpec) -> CutoutCharacter:
    """Translate the original ``character_id`` / ``part_type`` spec."""
    parts: list[CutoutPart] = []
    for part in rig_spec.parts:
        role = infer_role(part.id) or infer_role(part.part_type)
        if part.geometry_type == "primitive":
            parts.append(
                CutoutPart(
                    name=part.id,
                    role=role,
                    primitive_type=part.primitive_type,
                    primitive_params=part.primitive_params,
                    origin=part.origin,
                    z=float(part.z_depth),
                )
            )
        else:
            parts.append(CutoutPart(name=part.id, role=role, file=part.file_path))
    return CutoutCharacter(
        id=rig_spec.character_id,
        parts=parts,
        position=rig_spec.origin,
        scale=rig_spec.scale if rig_spec.scale != 1.0 else None,
    )


class RiggingEngine:
    """Orchestrator for cut-out character assembly, rigging, and pose playback."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    # -- helpers -----------------------------------------------------------

    async def canvas_frame(self, doc_id: str, coords: str = "pixels") -> CanvasFrame:
        """Size and view box of a document."""
        info = next((d for d in await self.backend.doc_list() if d.id == doc_id), None)
        if info is None:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found.")
        view_box = await self.backend.doc_view_box(doc_id)
        return CanvasFrame.for_document(info.width, info.height, view_box, coords=coords)

    async def _end_time(self, doc_id: str) -> float:
        info = next((d for d in await self.backend.doc_list() if d.id == doc_id), None)
        return info.end_time if info is not None else 5.0

    async def find_rig(self, doc_id: str, character_id: str) -> CompiledRig | None:
        """Return the rig of a character, checked against the layers that are in the document.

        A rig built by this process is used when its joints still exist; otherwise
        the rig is rediscovered from the ``<character>_<part>_rot`` layer names, so
        a document that was saved and reopened can still be animated.
        """
        remembered = _RIGS.get((doc_id, character_id))
        try:
            tree = await self.backend.scene_tree(doc_id)
        except SynfigError:
            return None
        prefix, suffix = f"{character_id}_", "_rot"
        pos_layer = f"{character_id}_pos"
        found: dict[str, RigPart] = {}
        position = (0.0, 0.0)
        has_pos = False

        def walk(nodes: list[dict[str, Any]]) -> None:
            nonlocal position, has_pos
            for node in nodes:
                layer_id = str(node.get("id") or node.get("desc") or "")
                if layer_id == pos_layer:
                    has_pos = True
                    origin: Any = (node.get("params") or {}).get("origin")
                    if origin is not None and hasattr(origin, "model_dump"):
                        origin = origin.model_dump()
                    if isinstance(origin, dict) and "x" in origin:
                        position = (float(origin["x"]), float(origin["y"]))
                elif layer_id.startswith(prefix) and layer_id.endswith(suffix):
                    name = layer_id[len(prefix) : -len(suffix)]
                    found[name] = RigPart(name, infer_role(name), None, layer_id)
                walk(node.get("children") or [])

        walk(tree.get("layers") or [])
        if not found:
            _RIGS.pop((doc_id, character_id), None)
            return None
        if remembered is not None and {p.rot_layer for p in remembered.parts.values()} <= {
            p.rot_layer for p in found.values()
        }:
            return remembered
        rig = CompiledRig(
            character_id=character_id,
            root_group=f"Character_{character_id}",
            pos_layer=pos_layer if has_pos else "",
            position=position,
            height_units=1.0,
            parts=found,
        )
        return rig

    async def _write_plan(self, doc_id: str, plan: MotionPlan) -> int:
        """Write planned waypoints; one bulk call per animated parameter."""
        written = 0
        for layer_id, params in plan.tracks.items():
            if not layer_id:
                continue
            for param in params:
                waypoints = plan.waypoints(layer_id, param)
                await self.backend.anim_animate_param(
                    doc_id=doc_id, layer_id=layer_id, param_name=param, waypoints=waypoints
                )
                written += len(waypoints)
        return written

    def _unknown_character(self, doc_id: str, character_id: str) -> SynfigError:
        known = sorted(char for (doc, char) in _RIGS if doc == doc_id)
        return SpecError(
            f"No rig named '{character_id}' in document '{doc_id}'. Build it first with "
            "character_rig_from_parts or scene_auto_build."
            + (f" Known characters: {known}." if known else "")
        )

    # -- tools -------------------------------------------------------------

    async def character_rig_from_parts(
        self,
        spec: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Assemble a cut-out character rig atomically via scene_build.

        Accepts the cut-out spec (``id`` + image ``parts`` or a ``manifest``) and
        the original ``character_id`` spec with primitive parts.
        """
        bones_count = 0
        coords = str(spec.get("coords", "pixels"))
        if "character_id" in spec:
            legacy = CharacterRigSpec.model_validate(spec)
            doc_id = legacy.doc_id
            character = _legacy_to_cutout(legacy)
            bones_count = len(legacy.bones)
            coords = "units"
        else:
            data = {k: v for k, v in spec.items() if k not in ("doc_id", "coords")}
            doc_id = str(spec.get("doc_id", "doc_0"))
            character = CutoutCharacter.model_validate(data)

        frame = await self.canvas_frame(doc_id, coords=coords)
        rig = compile_character(character, frame)
        if bones_count:
            rig.notes.append(
                "The 'bones' list is informational: every part gets a rotate joint layer "
                "(<character>_<part>_rot) that poses and motions animate."
            )
        plan = MotionPlan()
        if character.actions:
            plan = plan_actions(rig, character.actions, frame, await self._end_time(doc_id))
            attach_waypoints(rig, plan)

        build_spec = {"doc_id": doc_id, "layers": rig.layers, "groups": rig.groups}
        build_res = await self.backend.scene_build(spec=build_spec, dry_run=dry_run)
        if build_res.get("success") is False:
            raise SynfigError(str(build_res.get("error", "scene_build rejected the rig.")))
        if not dry_run:
            remember_rig(doc_id, rig)
        return {
            "success": True,
            "character_id": rig.character_id,
            "doc_id": doc_id,
            "root_group": rig.root_group,
            "position_layer": rig.pos_layer,
            "parts_count": len(rig.parts),
            "bones_count": bones_count,
            "parts": rig.summary()["parts"],
            "waypoints": plan.count(),
            "notes": rig.notes,
            "diff": build_res.get("diff", {}),
            "dry_run": dry_run,
        }

    async def character_pose_apply(
        self,
        doc_id: str,
        character_id: str,
        pose_name: str = "idle",
        time: float = 0.0,
        angles: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Key a pose at ``time``: a named preset or explicit joint ``angles`` in degrees."""
        part_swaps: dict[str, str] = {}
        if angles:
            wanted = dict(angles)
            pose_label = pose_name if pose_name and pose_name != "idle" else "custom"
        else:
            pose = STANDARD_POSES.get(pose_name.lower().strip())
            if not pose:
                raise SpecError(
                    f"Unknown pose '{pose_name}'. Available: {list(STANDARD_POSES.keys())}, "
                    "or pass explicit 'angles'."
                )
            wanted = {
                _BONE_ROLES[bone]: value
                for bone, value in pose.bone_angles.items()
                if bone in _BONE_ROLES
            }
            part_swaps = pose.part_swaps
            pose_label = pose_name

        rig = await self.find_rig(doc_id, character_id)
        if rig is None:
            raise self._unknown_character(doc_id, character_id)

        plan = MotionPlan()
        skipped: list[str] = []
        for key, degrees in wanted.items():
            part = resolve_part(rig, key)
            if part is None:
                skipped.append(key)
                continue
            plan.add(
                part.rot_layer, "amount", time, angle(part.rest_angle + float(degrees)), "clamped"
            )
            plan.applied.append(part.rot_layer)
        if not plan.applied:
            raise SpecError(
                f"Pose '{pose_label}' addresses {sorted(wanted)}, but '{character_id}' has "
                f"none of them. Parts: {sorted(rig.parts)}."
            )
        await self._write_plan(doc_id, plan)
        return {
            "success": True,
            "character_id": character_id,
            "pose": pose_label,
            "time": time,
            "applied_bones": plan.applied,
            "skipped": skipped,
            "part_swaps": part_swaps,
        }

    async def character_motion_apply(
        self,
        doc_id: str,
        character_id: str,
        motion_name: str,
        start_time: float = 0.0,
        end_time: float | None = None,
        speed: float = 1.0,
        move_to: dict[str, float] | None = None,
        coords: str = "pixels",
    ) -> dict[str, Any]:
        """Apply a motion (walk, run, idle, wave, jump, nod, talk, punch, rest, move) to a rig."""
        motion = motion_name.lower().strip()
        rig = await self.find_rig(doc_id, character_id)
        if rig is None:
            raise self._unknown_character(doc_id, character_id)

        if motion == "punch":
            # Windup -> strike -> hold -> recover, built from the pose presets.
            keyframes: list[dict[str, Any]] = []
            for offset, pose in ((0.0, "idle"), (0.15, "punch"), (0.35, "punch"), (0.6, "idle")):
                await self.character_pose_apply(
                    doc_id, character_id, pose, time=start_time + offset
                )
                keyframes.append({"time": start_time + offset, "pose": pose})
            return {
                "success": True,
                "character_id": character_id,
                "motion": motion_name,
                "duration": 0.6,
                "keyframes": keyframes,
                "waypoints": len(keyframes),
            }

        if motion not in motion_catalog():
            raise SpecError(
                f"Unknown motion '{motion_name}'. Available: "
                f"{', '.join(sorted([*motion_catalog(), 'punch']))}."
            )
        frame = await self.canvas_frame(doc_id, coords=coords)
        if move_to is not None and not rig.pos_layer:
            raise SpecError(f"'{character_id}' has no position layer; it cannot be moved.")
        action = MotionAction(
            motion=motion, start=start_time, end=end_time, speed=speed, move_to=move_to
        )
        plan = plan_actions(rig, [action], frame, await self._end_time(doc_id))
        written = await self._write_plan(doc_id, plan)
        if move_to is not None:
            rig.position = frame.point(float(move_to.get("x", 0)), float(move_to.get("y", 0)))
        times = sorted(
            {t for params in plan.tracks.values() for keys in params.values() for t in keys}
        )
        return {
            "success": True,
            "character_id": character_id,
            "motion": motion_name,
            "start_time": start_time,
            "end_time": plan.end_time,
            "duration": round(plan.end_time - start_time, 4),
            "keyframes": [{"time": t} for t in times],
            "waypoints": written,
            "animated_layers": sorted(k for k in plan.tracks if k),
            "skipped_roles": plan.skipped_roles,
        }
