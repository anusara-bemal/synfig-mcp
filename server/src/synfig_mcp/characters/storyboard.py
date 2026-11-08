"""
Storyboard Engine: Converts scripted storyboard manifests into Synfig scene sequences,
camera tracks, and shot lists for animatics (Phase A4).
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.models import StoryboardSpec


class StoryboardEngine:
    """Orchestrator for storyboard generation and animatic shot structuring."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    async def storyboard_from_script(
        self,
        spec: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Assemble a complete animatic timeline with shots and camera setups from script spec.
        """
        sb_spec = StoryboardSpec.model_validate(spec)
        doc_id = sb_spec.doc_id

        total_duration = 0.0
        shot_manifest: list[dict[str, Any]] = []
        shot_layers: list[dict[str, Any]] = []
        shot_groups: list[dict[str, Any]] = []

        for idx, shot in enumerate(sb_spec.shots):
            start_t = total_duration
            end_t = start_t + shot.duration_seconds
            total_duration = end_t

            shot_group_id = f"Shot_{shot.shot_id}"
            cam_layer_id = f"Camera_{shot.shot_id}"

            # Create camera transform layer for shot
            shot_layers.append(
                {
                    "id": cam_layer_id,
                    "type": "zoom",
                    "depth": 0,
                    "params": {"amount": {"type": "real", "value": 0.0}},
                }
            )
            shot_groups.append(
                {
                    "id": shot_group_id,
                    "layer_ids": [cam_layer_id],
                }
            )

            shot_manifest.append(
                {
                    "index": idx + 1,
                    "shot_id": shot.shot_id,
                    "description": shot.description,
                    "start_time": round(start_t, 2),
                    "end_time": round(end_t, 2),
                    "duration": round(shot.duration_seconds, 2),
                    "camera": shot.camera_movement,
                    "characters": shot.characters_present,
                    "dialogue": shot.dialogue,
                }
            )

        # Top-level scene spec with total animatic time range
        build_spec = {
            "version": "1.0",
            "doc_id": doc_id,
            "fps": sb_spec.fps,
            "start_time": 0.0,
            "end_time": total_duration,
            "layers": shot_layers,
            "groups": shot_groups,
        }

        build_res = await self.backend.scene_build(spec=build_spec, dry_run=dry_run)

        # Set canvas time range to match animatic duration if not dry_run
        if not dry_run:
            await self.backend.doc_set_time_range(
                doc_id=doc_id, start_time=0.0, end_time=total_duration
            )

        return {
            "success": True,
            "project_title": sb_spec.title,
            "doc_id": doc_id,
            "total_shots": len(sb_spec.shots),
            "total_duration_seconds": round(total_duration, 2),
            "shots": shot_manifest,
            "diff": build_res.get("diff", {}),
            "dry_run": dry_run,
        }
