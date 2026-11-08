"""
Pydantic schema definitions and validation for declarative scene build specs.
Enables atomic, single-undo, token-efficient scene assembly in Synfig.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class WaypointSpec(BaseModel):
    """Declarative keyframe waypoint on a layer parameter."""

    param: str = Field(description="Name of the parameter to animate.")
    time: float = Field(description="Time position in seconds.")
    value: dict[str, Any] = Field(description="Typed parameter value at this waypoint.")
    interpolation: Literal["clamped", "linear", "halt", "constant", "auto"] = Field(
        default="clamped", description="Synfig interpolation curve mode."
    )


class SceneLayerSpec(BaseModel):
    """Declarative specification for an individual layer."""

    id: str = Field(description="Unique layer identifier / description.")
    type: str = Field(description="Synfig layer type (e.g. circle, rectangle, blur, star).")
    depth: int = Field(default=0, description="Stacking depth within the canvas (0 = top).")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Initial parameter values mapping name to typed dict."
    )
    waypoints: list[WaypointSpec] = Field(
        default_factory=list, description="Animation waypoints for parameters of this layer."
    )


class SceneGroupSpec(BaseModel):
    """Declarative specification for encapsulating layers inside a group/subcanvas."""

    id: str = Field(description="Identifier / description for the group layer.")
    layer_ids: list[str] = Field(description="List of child layer IDs to group together.")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Optional parameters for the group container."
    )


class SceneBuildSpec(BaseModel):
    """Complete declarative specification for building or modifying a Synfig scene atomically."""

    doc_id: str = Field(default="doc_0", description="Target document ID.")
    canvas_path: str = Field(default="", description="Optional path to target subcanvas.")
    width: int | None = Field(default=None, description="Optional canvas width.")
    height: int | None = Field(default=None, description="Optional canvas height.")
    fps: float | None = Field(default=None, description="Optional canvas framerate.")
    start_time: float | None = Field(default=None, description="Optional canvas start time.")
    end_time: float | None = Field(default=None, description="Optional canvas end time.")
    layers: list[SceneLayerSpec] = Field(
        default_factory=list, description="Layers to instantiate and configure."
    )
    groups: list[SceneGroupSpec] = Field(
        default_factory=list, description="Group hierarchies to assemble from layers."
    )
