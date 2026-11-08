"""
Data models for the Effects Recipe Library and Generic Style Presets (Phase A3).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecipeParamDefinition(BaseModel):
    """Schema definition for a single recipe parameter."""

    name: str = Field(description="Parameter name.")
    type: str = Field(
        description="Type identifier (e.g. 'float', 'int', 'color', 'vector', 'bool', 'str')."
    )
    default: Any = Field(description="Default value.")
    description: str = Field(default="", description="Human/LLM-readable parameter description.")
    min_value: float | None = Field(default=None, description="Optional minimum numeric value.")
    max_value: float | None = Field(default=None, description="Optional maximum numeric value.")
    enum: list[str] | None = Field(
        default=None, description="Optional set of allowed string values."
    )


class RecipeManifest(BaseModel):
    """Manifest definition of a composable effect recipe."""

    name: str = Field(description="Unique recipe identifier.")
    category: str = Field(
        description="Category (e.g. 'action', 'lighting', 'lens', 'grading', 'timing')."
    )
    description: str = Field(description="Concise description of the effect.")
    native_layers_used: list[str] = Field(
        default_factory=list,
        description="List of native Synfig layer types instantiated by this recipe.",
    )
    parameters: dict[str, RecipeParamDefinition] = Field(
        default_factory=dict, description="Configurable parameters with types and default values."
    )
    notes: str = Field(default="", description="Usage notes or layer stacking advice.")


class StylePreset(BaseModel):
    """Generic style configuration for palette, grain, timing, and default recipe stack."""

    name: str = Field(
        description="Generic style identifier (e.g. 'shonen_action', 'dark_fantasy')."
    )
    description: str = Field(description="Description of visual mood and conventions.")
    palette: list[str] = Field(default_factory=list, description="Primary hex color palette.")
    contrast: str = Field(
        default="standard", description="Luminance contrast profile ('high', 'medium', 'crushed')."
    )
    grain_intensity: float = Field(
        default=0.0, description="Film grain noise overlay intensity (0.0 to 1.0)."
    )
    line_weight: float = Field(
        default=1.0, description="Recommended character contour stroke width in points."
    )
    timing_interval: int = Field(
        default=1, description="Animation keyframe hold interval (1 = ones, 2 = twos, 3 = threes)."
    )
    recipe_stack: list[str] = Field(
        default_factory=list, description="List of recipe names active by default."
    )
