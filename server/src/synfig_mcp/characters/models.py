"""
Data models for Cut-out Characters, Bone Rigs, and Storyboards (Phase A4).
Strict IP Policy: Original/licensed geometric parts and neutral motion presets only.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CharacterPartSpec(BaseModel):
    """Specification of an anatomical or prop part for a cut-out character."""

    id: str = Field(description="Part identifier (e.g. 'head', 'torso', 'arm_upper_l').")
    part_type: str = Field(
        description="Anatomical type ('head', 'torso', 'upper_arm', 'forearm', 'hand', 'upper_leg', 'lower_leg', 'foot', 'eye', 'mouth')."
    )
    geometry_type: Literal["primitive", "svg", "png"] = Field(
        default="primitive",
        description="Source format: procedural primitive or imported vector/raster.",
    )
    primitive_type: str = Field(
        default="circle",
        description="Primitive layer type if geometry_type == 'primitive' (e.g. 'circle', 'rectangle', 'star').",
    )
    primitive_params: dict[str, Any] = Field(
        default_factory=dict, description="Initial parameters if primitive_type is used."
    )
    file_path: str | None = Field(default=None, description="Workspace file path if svg/png part.")
    origin: dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0},
        description="Pivot coordinate {x, y} in canvas units.",
    )
    z_depth: int = Field(default=0, description="Stacking order depth within character group.")


class BoneSpec(BaseModel):
    """Bone specification for hierarchical forward-kinematics skeleton."""

    name: str = Field(description="Bone identifier (e.g. 'bone_root', 'bone_spine', 'bone_arm_l').")
    parent: str | None = Field(default=None, description="Parent bone name (None for root).")
    origin: dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0}, description="Joint origin {x, y}."
    )
    length: float = Field(default=1.0, description="Bone segment length.")
    angle_deg: float = Field(default=0.0, description="Rest angle in degrees.")


class CharacterRigSpec(BaseModel):
    """Complete specification for assembling a 2D cut-out character rig."""

    character_id: str = Field(description="Unique character identifier.")
    doc_id: str = Field(default="doc_0", description="Target document ID.")
    origin: dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0},
        description="Placement origin {x, y} on canvas.",
    )
    scale: float = Field(default=1.0, description="Uniform scaling factor.")
    parts: list[CharacterPartSpec] = Field(
        default_factory=list, description="List of anatomical character parts."
    )
    bones: list[BoneSpec] = Field(
        default_factory=list, description="Hierarchical bone skeleton structure."
    )


class PosePreset(BaseModel):
    """Named keyframe pose preset mapping bones to rotations and facial swaps."""

    name: str = Field(
        description="Pose identifier ('idle', 'walk_contact', 'walk_passing', 'jump', 'punch')."
    )
    bone_angles: dict[str, float] = Field(
        default_factory=dict, description="Mapping bone_name -> angle_degrees."
    )
    part_swaps: dict[str, str] = Field(
        default_factory=dict, description="Mapping slot ('mouth', 'eyes') -> active variant shape."
    )


class StoryboardShot(BaseModel):
    """Single scene/shot within an animatic storyboard."""

    shot_id: str = Field(description="Shot identifier (e.g. 'shot_01', 'shot_02').")
    description: str = Field(description="Action and narrative description.")
    duration_seconds: float = Field(default=2.0, description="Duration of this shot in seconds.")
    camera_movement: str = Field(
        default="static",
        description="Camera movement ('static', 'pan_left', 'pan_right', 'zoom_in', 'zoom_out', 'tilt_up').",
    )
    characters_present: list[str] = Field(
        default_factory=list, description="Characters involved in this shot."
    )
    dialogue: str = Field(default="", description="Dialogue or audio cue.")


class StoryboardSpec(BaseModel):
    """Storyboard script specification for assembling shot manifests and animatic time tracks."""

    title: str = Field(description="Project or episode title.")
    doc_id: str = Field(default="doc_0", description="Target document ID.")
    fps: float = Field(default=24.0, description="Project frame rate.")
    shots: list[StoryboardShot] = Field(
        default_factory=list, description="Ordered sequence of shots."
    )
