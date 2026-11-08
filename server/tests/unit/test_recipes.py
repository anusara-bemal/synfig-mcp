"""
Unit tests for Effects Recipe Library and Generic Style Presets (Phase A3).
"""

from __future__ import annotations

from synfig_mcp.recipes.engine import RecipeEngine
from synfig_mcp.recipes.registry import get_recipe_manifest, list_recipes
from synfig_mcp.recipes.styles import list_style_presets


def test_recipe_registry_manifests() -> None:
    recipes = list_recipes()
    assert len(recipes) >= 12

    names = [r["name"] for r in recipes]
    assert "speed_lines" in names
    assert "vignette" in names
    assert "film_grain" in names
    assert "impact_frame" in names
    assert "radial_blur_burst" in names
    assert "color_grade_stack" in names


def test_recipe_info_spec() -> None:
    manifest = get_recipe_manifest("vignette")
    assert manifest is not None
    assert manifest.category == "lens"
    assert "radius" in manifest.parameters
    assert "opacity" in manifest.parameters
    assert manifest.parameters["radius"].default == 2.0


def test_style_presets() -> None:
    styles = list_style_presets()
    assert len(styles) >= 5

    names = [s["name"] for s in styles]
    assert "shonen_action" in names
    assert "dark_fantasy" in names
    assert "supernatural_noir" in names
    assert "cyber_mecha" in names
    assert "retro_anime" in names


def test_ip_policy_neutral_naming() -> None:
    """Hard rule: No copyrighted franchise names in recipes or styles."""
    forbidden = [
        "dragonball",
        "naruto",
        "goku",
        "bleach",
        "jujutsu",
        "evangelion",
        "attack_on_titan",
        "ghibli",
        "disney",
        "marvel",
        "batman",
    ]

    all_names = [r["name"] for r in list_recipes()] + [s["name"] for s in list_style_presets()]
    for n in all_names:
        for f in forbidden:
            assert f not in n.lower(), f"IP Policy violation: '{f}' in '{n}'"


def test_recipe_parameter_bounds() -> None:
    # Test bounds clamping
    from synfig_mcp.backend.headless import HeadlessBackend

    backend = HeadlessBackend()
    engine = RecipeEngine(backend=backend)

    manifest = get_recipe_manifest("vignette")
    assert manifest is not None
    # User provides opacity 5.0 (max is 1.0) and radius 0.1 (min is 0.5)
    resolved = engine._resolve_params(manifest.parameters, {"opacity": 5.0, "radius": 0.1})
    assert resolved["opacity"] == 1.0
    assert resolved["radius"] == 0.5
