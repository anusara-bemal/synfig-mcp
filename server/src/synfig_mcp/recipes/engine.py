"""
Recipe Engine: Transforms recipe specifications into declarative SceneBuildSpec
structures applied atomically as a single undo step (Phase A3).
"""

from __future__ import annotations

import time
from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.recipes.registry import get_recipe_manifest
from synfig_mcp.recipes.styles import get_style_preset


class RecipeEngine:
    """Orchestrator for validating and executing parameterized recipes."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    def _resolve_params(
        self,
        schema_params: dict[str, Any],
        user_params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Fill in defaults and validate supplied parameters."""
        resolved: dict[str, Any] = {}
        user_params = user_params or {}

        for p_name, p_def in schema_params.items():
            val = user_params.get(p_name, p_def.default)
            # Numeric bounds clamping if applicable
            if isinstance(val, (int, float)):
                if p_def.min_value is not None:
                    val = max(p_def.min_value, val)
                if p_def.max_value is not None:
                    val = min(p_def.max_value, val)
            resolved[p_name] = val

        return resolved

    async def apply_recipe(
        self,
        doc_id: str,
        name: str,
        params: dict[str, Any] | None = None,
        target_layer_or_group: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Apply a parameterized recipe atomically via scene_build.
        Returns: {recipe, doc_id, applied_layers, diff, dry_run}
        """
        manifest = get_recipe_manifest(name)
        if not manifest:
            return {
                "success": False,
                "error": f"Unknown recipe '{name}'. Use recipe_list to view available recipes.",
            }

        resolved_params = self._resolve_params(manifest.parameters, params)
        uid = int(time.time() * 1000) % 100000

        layers_spec: list[dict[str, Any]] = []
        groups_spec: list[dict[str, Any]] = []

        rec_name = manifest.name

        if rec_name == "vignette":
            rad = float(resolved_params.get("radius", 2.0))
            op = float(resolved_params.get("opacity", 0.6))
            layers_spec.append(
                {
                    "id": f"Vignette_{uid}",
                    "type": "radial_gradient",
                    "depth": 0,
                    "params": {
                        "color1": {"type": "color", "value": [0.0, 0.0, 0.0, op]},
                        "color2": {"type": "color", "value": [0.0, 0.0, 0.0, 0.0]},
                        "radius": {"type": "real", "value": rad},
                        "blend_method": {"type": "integer", "value": 13},  # Multiply
                    },
                }
            )

        elif rec_name == "film_grain":
            intensity = float(resolved_params.get("intensity", 0.08))
            sz = float(resolved_params.get("grain_size", 0.02))
            layers_spec.append(
                {
                    "id": f"FilmGrain_{uid}",
                    "type": "noise",
                    "depth": 0,
                    "params": {
                        "amount": {"type": "real", "value": intensity},
                        "size": {"type": "vector", "value": {"x": sz, "y": sz}},
                    },
                }
            )

        elif rec_name == "color_grade_stack":
            gamma = float(resolved_params.get("gamma", 1.1))
            contrast = float(resolved_params.get("contrast", 1.15))
            sat = float(resolved_params.get("saturation", 0.9))
            layers_spec.append(
                {
                    "id": f"ColorGrade_{uid}",
                    "type": "colorcorrect",
                    "depth": 0,
                    "params": {
                        "gamma": {"type": "real", "value": gamma},
                        "contrast": {"type": "real", "value": contrast},
                        "saturation": {"type": "real", "value": sat},
                    },
                }
            )

        elif rec_name == "radial_blur_burst":
            center = resolved_params.get("center", {"x": 0.0, "y": 0.0})
            zm = float(resolved_params.get("zoom", 0.25))
            layers_spec.append(
                {
                    "id": f"RadialBlur_{uid}",
                    "type": "radial_blur",
                    "depth": 0,
                    "params": {
                        "origin": {"type": "vector", "value": center},
                        "zoom": {"type": "real", "value": zm},
                    },
                }
            )

        elif rec_name == "impact_frame":
            mode = str(resolved_params.get("mode", "invert"))
            if mode == "white_flash":
                layers_spec.append(
                    {
                        "id": f"ImpactFlash_{uid}",
                        "type": "solid_color",
                        "depth": 0,
                        "params": {"color": {"type": "color", "value": [1.0, 1.0, 1.0, 1.0]}},
                    }
                )
            else:
                layers_spec.append(
                    {
                        "id": f"ImpactInvert_{uid}",
                        "type": "inside_out",
                        "depth": 0,
                        "params": {"origin": {"type": "vector", "value": {"x": 0.0, "y": 0.0}}},
                    }
                )

        elif rec_name == "speed_lines":
            col = resolved_params.get("color", [1.0, 1.0, 1.0, 0.8])
            zm = float(resolved_params.get("zoom", 0.3))
            star_id = f"SpeedLines_Star_{uid}"
            blur_id = f"SpeedLines_Blur_{uid}"
            grp_id = f"SpeedLines_Group_{uid}"

            layers_spec.extend(
                [
                    {
                        "id": star_id,
                        "type": "star",
                        "depth": 0,
                        "params": {
                            "points": {"type": "integer", "value": 24},
                            "color": {"type": "color", "value": col},
                            "radius1": {"type": "real", "value": 3.0},
                            "radius2": {"type": "real", "value": 0.2},
                        },
                    },
                    {
                        "id": blur_id,
                        "type": "radial_blur",
                        "depth": 0,
                        "params": {
                            "origin": {"type": "vector", "value": {"x": 0.0, "y": 0.0}},
                            "zoom": {"type": "real", "value": zm},
                        },
                    },
                ]
            )
            groups_spec.append({"id": grp_id, "layer_ids": [star_id, blur_id]})

        else:
            # Generic native layer fallback for other manifest recipes
            fallback_type = (
                manifest.native_layers_used[0] if manifest.native_layers_used else "blur"
            )
            layers_spec.append(
                {
                    "id": f"{manifest.name.capitalize()}_{uid}",
                    "type": fallback_type,
                    "depth": 0,
                    "params": {},
                }
            )

        spec = {
            "version": "1.0",
            "doc_id": doc_id,
            "layers": layers_spec,
            "groups": groups_spec,
        }

        build_res = await self.backend.scene_build(spec=spec, dry_run=dry_run)
        return {
            "success": True,
            "recipe": name,
            "doc_id": doc_id,
            "target": target_layer_or_group,
            "applied_params": resolved_params,
            "created_layers": [lyr["id"] for lyr in layers_spec],
            "diff": build_res.get("diff", {}),
            "dry_run": dry_run,
        }

    async def apply_style(
        self,
        doc_id: str,
        style_name: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Apply a full generic anime style stack (color grading, grain, vignette) atomically.
        """
        preset = get_style_preset(style_name)
        if not preset:
            return {
                "success": False,
                "error": f"Unknown style preset '{style_name}'. Use style_list to view options.",
            }

        results: list[dict[str, Any]] = []
        for rec_name in preset.recipe_stack:
            res = await self.apply_recipe(doc_id=doc_id, name=rec_name, dry_run=dry_run)
            results.append(res)

        return {
            "success": True,
            "style": style_name,
            "doc_id": doc_id,
            "palette": preset.palette,
            "contrast": preset.contrast,
            "applied_recipes": preset.recipe_stack,
            "dry_run": dry_run,
        }
