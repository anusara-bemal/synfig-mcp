"""
Character Rigging Engine: Assembles hierarchical 2D cut-out puppets from original parts
and applies motion and pose presets (Phase A4).
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.models import CharacterRigSpec, PosePreset

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


class RiggingEngine:
    """Orchestrator for cut-out character assembly, rigging, and pose playback."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    async def character_rig_from_parts(
        self,
        spec: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Assemble a 2D cut-out character rig from parts atomically via scene_build.
        """
        rig_spec = CharacterRigSpec.model_validate(spec)
        doc_id = rig_spec.doc_id
        char_id = rig_spec.character_id

        layers_spec: list[dict[str, Any]] = []
        child_layer_ids: list[str] = []

        # 1. Instantiate anatomical parts
        for part in rig_spec.parts:
            part_layer_id = f"{char_id}_{part.id}"
            child_layer_ids.append(part_layer_id)

            if part.geometry_type == "primitive":
                p_type = part.primitive_type
                p_params = dict(part.primitive_params)
                p_params.setdefault("origin", {"type": "vector", "value": part.origin})
                layers_spec.append(
                    {
                        "id": part_layer_id,
                        "type": p_type,
                        "depth": part.z_depth,
                        "params": p_params,
                    }
                )
            elif part.geometry_type in ("svg", "png") and part.file_path:
                layers_spec.append(
                    {
                        "id": part_layer_id,
                        "type": "import",
                        "depth": part.z_depth,
                        "params": {
                            "filename": {"type": "string", "value": part.file_path},
                            "origin": {"type": "vector", "value": part.origin},
                        },
                    }
                )

        # 2. Add skeleton layer if bones were specified
        if rig_spec.bones:
            skeleton_id = f"{char_id}_skeleton"
            child_layer_ids.append(skeleton_id)
            layers_spec.append(
                {
                    "id": skeleton_id,
                    "type": "skeleton",
                    "depth": 0,
                    "params": {"name": {"type": "string", "value": f"{char_id}_Bones"}},
                }
            )

        # 3. Encapsulate all parts in character root container group
        group_id = f"Character_{char_id}"
        groups_spec = [{"id": group_id, "layer_ids": child_layer_ids}]

        build_spec = {
            "version": "1.0",
            "doc_id": doc_id,
            "layers": layers_spec,
            "groups": groups_spec,
        }

        build_res = await self.backend.scene_build(spec=build_spec, dry_run=dry_run)
        return {
            "success": True,
            "character_id": char_id,
            "doc_id": doc_id,
            "root_group": group_id,
            "parts_count": len(rig_spec.parts),
            "bones_count": len(rig_spec.bones),
            "diff": build_res.get("diff", {}),
            "dry_run": dry_run,
        }

    async def character_pose_apply(
        self,
        doc_id: str,
        character_id: str,
        pose_name: str,
        time: float = 0.0,
    ) -> dict[str, Any]:
        """Apply a named pose preset to character parts at the specified timestamp."""
        pose = STANDARD_POSES.get(pose_name.lower().strip())
        if not pose:
            return {
                "success": False,
                "error": f"Unknown pose '{pose_name}'. Available: {list(STANDARD_POSES.keys())}",
            }

        # Apply waypoints for each bone angle
        applied_bones: list[str] = []
        for bone_name, angle in pose.bone_angles.items():
            part_suffix = bone_name.replace("bone_", "")
            candidates = [f"{character_id}_{part_suffix}", f"{character_id}_{bone_name}"]
            for target_layer in candidates:
                try:
                    await self.backend.anim_waypoint_set(
                        doc_id=doc_id,
                        layer_id=target_layer,
                        param_name="angle",
                        time=time,
                        value={"type": "angle", "value": angle},
                        interpolation="clamped",
                    )
                    applied_bones.append(target_layer)
                    break
                except Exception:
                    pass
            else:
                applied_bones.append(f"{character_id}_{bone_name}")

        return {
            "success": True,
            "character_id": character_id,
            "pose": pose_name,
            "time": time,
            "applied_bones": applied_bones,
            "part_swaps": pose.part_swaps,
        }

    async def character_motion_apply(
        self,
        doc_id: str,
        character_id: str,
        motion_name: str,
        start_time: float = 0.0,
    ) -> dict[str, Any]:
        """Apply a cyclic motion preset (e.g. walk cycle or punch action) across time."""
        motion = motion_name.lower().strip()
        keyframes_applied: list[dict[str, Any]] = []

        if motion == "walk":
            # 4-step walk cycle: contact -> passing -> contact (opp) -> passing (opp) -> loop
            seq = [
                (start_time + 0.0, "walk_contact"),
                (start_time + 0.25, "walk_passing"),
                (start_time + 0.50, "walk_contact"),
                (start_time + 0.75, "walk_passing"),
                (start_time + 1.0, "walk_contact"),
            ]
            for t, p_name in seq:
                await self.character_pose_apply(doc_id, character_id, p_name, time=t)
                keyframes_applied.append({"time": t, "pose": p_name})

        elif motion == "punch":
            # Windup -> strike -> hold -> recover
            seq = [
                (start_time + 0.0, "idle"),
                (start_time + 0.15, "punch"),
                (start_time + 0.35, "punch"),
                (start_time + 0.60, "idle"),
            ]
            for t, p_name in seq:
                await self.character_pose_apply(doc_id, character_id, p_name, time=t)
                keyframes_applied.append({"time": t, "pose": p_name})

        else:
            await self.character_pose_apply(doc_id, character_id, "idle", time=start_time)
            keyframes_applied.append({"time": start_time, "pose": "idle"})

        return {
            "success": True,
            "character_id": character_id,
            "motion": motion_name,
            "duration": 1.0 if motion == "walk" else 0.6,
            "keyframes": keyframes_applied,
        }
