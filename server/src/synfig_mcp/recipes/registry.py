"""
Effects Recipe Registry: Composable anime-style and motion graphics visual effects
built purely from native Synfig layers (Phase A3).
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.recipes.models import RecipeManifest, RecipeParamDefinition

RECIPES: dict[str, RecipeManifest] = {
    "speed_lines": RecipeManifest(
        name="speed_lines",
        category="action",
        description="Dynamic radial or linear action lines with noise-driven density and speed blur.",
        native_layers_used=["star", "radial_blur", "group"],
        parameters={
            "intensity": RecipeParamDefinition(
                name="intensity",
                type="float",
                default=0.7,
                min_value=0.1,
                max_value=1.0,
                description="Visual density of the lines.",
            ),
            "color": RecipeParamDefinition(
                name="color",
                type="color",
                default=[1.0, 1.0, 1.0, 0.8],
                description="Line color and alpha.",
            ),
            "zoom": RecipeParamDefinition(
                name="zoom",
                type="float",
                default=0.3,
                min_value=0.05,
                max_value=1.0,
                description="Radial blur zoom factor.",
            ),
        },
        notes="Places a Star geometry layer coupled with Radial Blur in an overlay group.",
    ),
    "radial_blur_burst": RecipeManifest(
        name="radial_blur_burst",
        category="action",
        description="Zoom blur burst focusing viewer attention towards a focal coordinate.",
        native_layers_used=["radial_blur"],
        parameters={
            "center": RecipeParamDefinition(
                name="center",
                type="vector",
                default={"x": 0.0, "y": 0.0},
                description="Focal origin center.",
            ),
            "zoom": RecipeParamDefinition(
                name="zoom",
                type="float",
                default=0.25,
                min_value=0.01,
                max_value=0.8,
                description="Zoom stretch intensity.",
            ),
        },
        notes="Place above the target layer/group to apply radial distortion.",
    ),
    "impact_frame": RecipeManifest(
        name="impact_frame",
        category="action",
        description="Single-frame or two-frame visual shock with inverted silhouette or high-contrast flash.",
        native_layers_used=["solid_color", "inside_out"],
        parameters={
            "mode": RecipeParamDefinition(
                name="mode",
                type="str",
                default="invert",
                enum=["invert", "white_flash", "black_silhouette"],
                description="Impact style.",
            ),
            "duration_frames": RecipeParamDefinition(
                name="duration_frames",
                type="int",
                default=2,
                min_value=1,
                max_value=6,
                description="Duration in frames.",
            ),
        },
        notes="Creates momentary high-contrast inversion or flash overlay.",
    ),
    "slash_arc": RecipeManifest(
        name="slash_arc",
        category="action",
        description="Curved weapon slash trail with inner core and luminous outer glow.",
        native_layers_used=["curve_gradient", "blur", "group"],
        parameters={
            "color": RecipeParamDefinition(
                name="color",
                type="color",
                default=[0.2, 0.8, 1.0, 0.9],
                description="Slash energy glow color.",
            ),
            "width": RecipeParamDefinition(
                name="width",
                type="float",
                default=0.15,
                min_value=0.02,
                max_value=0.5,
                description="Arc stroke thickness.",
            ),
        },
        notes="Assembles curved gradient with directional motion blur trail.",
    ),
    "energy_aura": RecipeManifest(
        name="energy_aura",
        category="action",
        description="Fluctuating power aura using noise-driven distortion and colored glow.",
        native_layers_used=["noise", "blur", "group"],
        parameters={
            "aura_color": RecipeParamDefinition(
                name="aura_color",
                type="color",
                default=[1.0, 0.7, 0.1, 0.8],
                description="Aura glow tint.",
            ),
            "noise_size": RecipeParamDefinition(
                name="noise_size",
                type="float",
                default=0.2,
                min_value=0.05,
                max_value=1.0,
                description="Noise turbulence frequency.",
            ),
        },
        notes="Composites animated noise onto a blurred contour group.",
    ),
    "vignette": RecipeManifest(
        name="vignette",
        category="lens",
        description="Radial lens darkening towards the outer canvas perimeter.",
        native_layers_used=["radial_gradient"],
        parameters={
            "radius": RecipeParamDefinition(
                name="radius",
                type="float",
                default=2.0,
                min_value=0.5,
                max_value=4.0,
                description="Vignette falloff radius.",
            ),
            "opacity": RecipeParamDefinition(
                name="opacity",
                type="float",
                default=0.6,
                min_value=0.1,
                max_value=1.0,
                description="Darkening intensity.",
            ),
        },
        notes="Top-level radial gradient with multiply blend mode.",
    ),
    "film_grain": RecipeManifest(
        name="film_grain",
        category="lens",
        description="Subtle analog film grain and texture overlay.",
        native_layers_used=["noise"],
        parameters={
            "intensity": RecipeParamDefinition(
                name="intensity",
                type="float",
                default=0.08,
                min_value=0.01,
                max_value=0.3,
                description="Grain opacity level.",
            ),
            "grain_size": RecipeParamDefinition(
                name="grain_size",
                type="float",
                default=0.02,
                min_value=0.01,
                max_value=0.1,
                description="Noise particle scale.",
            ),
        },
        notes="High-frequency low-opacity noise layer stacked at depth 0.",
    ),
    "chromatic_aberration": RecipeManifest(
        name="chromatic_aberration",
        category="lens",
        description="RGB spectral channel shift at high-contrast lens margins.",
        native_layers_used=["colorcorrect"],
        parameters={
            "shift": RecipeParamDefinition(
                name="shift",
                type="float",
                default=0.03,
                min_value=0.005,
                max_value=0.1,
                description="Channel displacement offset.",
            ),
        },
        notes="Simulates optical refraction distortion.",
    ),
    "camera_shake": RecipeManifest(
        name="camera_shake",
        category="action",
        description="Simulated impact camera shake via multi-axis high-frequency translation.",
        native_layers_used=["group"],
        parameters={
            "intensity": RecipeParamDefinition(
                name="intensity",
                type="float",
                default=0.4,
                min_value=0.05,
                max_value=2.0,
                description="Peak shake offset in canvas units.",
            ),
            "duration": RecipeParamDefinition(
                name="duration",
                type="float",
                default=0.4,
                min_value=0.1,
                max_value=1.5,
                description="Shake duration in seconds.",
            ),
        },
        notes="Wraps scene or target group with animated decay waypoints.",
    ),
    "halftone_screentone": RecipeManifest(
        name="halftone_screentone",
        category="shading",
        description="Manga/comic dot screentone shading overlay.",
        native_layers_used=["halftone2"],
        parameters={
            "dot_size": RecipeParamDefinition(
                name="dot_size",
                type="float",
                default=0.05,
                min_value=0.01,
                max_value=0.2,
                description="Screentone dot spacing.",
            ),
            "density": RecipeParamDefinition(
                name="density",
                type="float",
                default=0.5,
                min_value=0.1,
                max_value=0.9,
                description="Dot threshold density.",
            ),
        },
        notes="Composites Halftone 2 layer with multiply blend mode.",
    ),
    "cel_shade_rim": RecipeManifest(
        name="cel_shade_rim",
        category="shading",
        description="Sharp cel-shade threshold with dynamic edge rim-lighting.",
        native_layers_used=["bevel", "blur", "group"],
        parameters={
            "rim_color": RecipeParamDefinition(
                name="rim_color",
                type="color",
                default=[0.9, 0.95, 1.0, 1.0],
                description="Rim highlight color.",
            ),
            "depth": RecipeParamDefinition(
                name="depth",
                type="float",
                default=0.08,
                min_value=0.01,
                max_value=0.3,
                description="Rim light bevel thickness.",
            ),
        },
        notes="Bevel layer paired with high-pass threshold.",
    ),
    "color_grade_stack": RecipeManifest(
        name="color_grade_stack",
        category="grading",
        description="Full-canvas color grading (gamma, contrast, hue, saturation adjustment).",
        native_layers_used=["colorcorrect"],
        parameters={
            "gamma": RecipeParamDefinition(
                name="gamma",
                type="float",
                default=1.1,
                min_value=0.5,
                max_value=2.0,
                description="Midtone gamma curve.",
            ),
            "contrast": RecipeParamDefinition(
                name="contrast",
                type="float",
                default=1.15,
                min_value=0.5,
                max_value=2.0,
                description="Luminance contrast multiplier.",
            ),
            "saturation": RecipeParamDefinition(
                name="saturation",
                type="float",
                default=0.9,
                min_value=0.0,
                max_value=2.0,
                description="Color saturation level.",
            ),
        },
        notes="Top-level Color Correct layer applying non-destructive grading.",
    ),
    "limited_animation_timing": RecipeManifest(
        name="limited_animation_timing",
        category="timing",
        description="Anime-style stepped timing (holds on twos or threes with constant interpolation).",
        native_layers_used=["timeloop"],
        parameters={
            "interval": RecipeParamDefinition(
                name="interval",
                type="int",
                default=2,
                min_value=2,
                max_value=4,
                description="Step hold interval (2 = twos, 3 = threes).",
            ),
        },
        notes="Quantizes continuous tweening into rhythmic traditional holds.",
    ),
    "transition_whip_pan": RecipeManifest(
        name="transition_whip_pan",
        category="action",
        description="High-velocity whip pan transition with linear motion blur.",
        native_layers_used=["motion_blur", "group"],
        parameters={
            "duration": RecipeParamDefinition(
                name="duration",
                type="float",
                default=0.25,
                min_value=0.1,
                max_value=0.5,
                description="Transition duration in seconds.",
            ),
            "direction": RecipeParamDefinition(
                name="direction",
                type="str",
                default="left",
                enum=["left", "right", "up", "down"],
                description="Pan direction.",
            ),
        },
        notes="Rapid horizontal/vertical blur burst across scene cut.",
    ),
}


def get_recipe_manifest(name: str) -> RecipeManifest | None:
    """Retrieve recipe manifest by name."""
    return RECIPES.get(name.lower().strip())


def list_recipes() -> list[dict[str, Any]]:
    """List all registered recipe manifests."""
    return [
        {
            "name": m.name,
            "category": m.category,
            "description": m.description,
            "layers": m.native_layers_used,
            "parameter_count": len(m.parameters),
        }
        for m in sorted(RECIPES.values(), key=lambda r: (r.category, r.name))
    ]
