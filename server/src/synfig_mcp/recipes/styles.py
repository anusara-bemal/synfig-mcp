"""
Generic style presets for anime-style aesthetic configurations (Phase A3).
Strict IP Policy: descriptive traits only, no franchise or copyrighted names.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.recipes.models import StylePreset

STYLE_PRESETS: dict[str, StylePreset] = {
    "shonen_action": StylePreset(
        name="shonen_action",
        description="High-energy shonen animation style: punchy primary colors, high contrast, impact frames, speed bursts.",
        palette=["#ff2a2a", "#ffaa00", "#ffffff", "#1a1a24", "#00a2ff"],
        contrast="high",
        grain_intensity=0.04,
        line_weight=2.0,
        timing_interval=2,
        recipe_stack=["speed_lines", "impact_frame", "camera_shake"],
    ),
    "dark_fantasy": StylePreset(
        name="dark_fantasy",
        description="Atmospheric dark fantasy style: crushed midtones, desaturated earth hues, luminous rim lights, vignette.",
        palette=["#121016", "#2a1f2d", "#8c2e3a", "#c4a35a", "#e0e6ed"],
        contrast="crushed",
        grain_intensity=0.12,
        line_weight=1.5,
        timing_interval=2,
        recipe_stack=["vignette", "film_grain", "cel_shade_rim"],
    ),
    "supernatural_noir": StylePreset(
        name="supernatural_noir",
        description="Stylized supernatural noir: stark chiaroscuro, heavy black silhouettes, monochrome duotone with crimson accents.",
        palette=["#08080a", "#1e1e24", "#787882", "#ffffff", "#c9182b"],
        contrast="high",
        grain_intensity=0.10,
        line_weight=2.5,
        timing_interval=3,
        recipe_stack=["vignette", "film_grain", "color_grade_stack"],
    ),
    "cyber_mecha": StylePreset(
        name="cyber_mecha",
        description="Sci-fi mecha aesthetic: sharp hard-surface lines, chromatic aberration, neon cyan/magenta energy glows.",
        palette=["#0b0e14", "#00f0ff", "#ff0055", "#ffe600", "#e6f1ff"],
        contrast="high",
        grain_intensity=0.03,
        line_weight=1.2,
        timing_interval=2,
        recipe_stack=["chromatic_aberration", "energy_aura", "radial_blur_burst"],
    ),
    "retro_anime": StylePreset(
        name="retro_anime",
        description="Vintage 1980s/90s cel animation aesthetic: warm pastel wash, dot screentone shading, subtle analog film grain.",
        palette=["#1e1b2e", "#e87a90", "#fcd575", "#70c1b3", "#fcfcfc"],
        contrast="medium",
        grain_intensity=0.15,
        line_weight=1.8,
        timing_interval=2,
        recipe_stack=["halftone_screentone", "film_grain", "limited_animation_timing"],
    ),
}


def get_style_preset(name: str) -> StylePreset | None:
    """Retrieve style preset by generic name."""
    return STYLE_PRESETS.get(name.lower().strip())


def list_style_presets() -> list[dict[str, Any]]:
    """List all available generic style presets."""
    return [
        {
            "name": p.name,
            "description": p.description,
            "contrast": p.contrast,
            "grain": p.grain_intensity,
            "line_weight": p.line_weight,
            "timing_interval": p.timing_interval,
            "palette": p.palette,
            "default_recipes": p.recipe_stack,
        }
        for p in STYLE_PRESETS.values()
    ]
