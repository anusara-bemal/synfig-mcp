"""
Unit tests for Cut-out Characters and Storyboard Models (Phase A4).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from synfig_mcp.characters.models import (
    BoneSpec,
    CharacterPartSpec,
    CharacterRigSpec,
    StoryboardShot,
    StoryboardSpec,
)
from synfig_mcp.characters.rigging import STANDARD_POSES


def test_character_part_spec_valid() -> None:
    part = CharacterPartSpec(
        id="torso",
        part_type="torso",
        geometry_type="primitive",
        primitive_type="rectangle",
        primitive_params={"color": {"type": "color", "value": [1.0, 0.0, 0.0, 1.0]}},
        origin={"x": 0.0, "y": 0.5},
        z_depth=2,
    )
    assert part.id == "torso"
    assert part.z_depth == 2
    assert part.origin["y"] == 0.5


def test_character_rig_spec_validation() -> None:
    rig = CharacterRigSpec(
        character_id="hero_unit",
        doc_id="doc_0",
        scale=1.5,
        parts=[
            CharacterPartSpec(id="head", part_type="head", primitive_type="circle"),
            CharacterPartSpec(id="torso", part_type="torso", primitive_type="rectangle"),
        ],
        bones=[
            BoneSpec(name="bone_root", length=1.0, angle_deg=90.0),
            BoneSpec(name="bone_head", parent="bone_root", length=0.5, angle_deg=90.0),
        ],
    )
    assert rig.character_id == "hero_unit"
    assert len(rig.parts) == 2
    assert len(rig.bones) == 2


def test_storyboard_spec_validation() -> None:
    sb = StoryboardSpec(
        title="Test Animatic",
        fps=24.0,
        shots=[
            StoryboardShot(
                shot_id="shot_01",
                description="Hero appears on cliff.",
                duration_seconds=3.0,
                camera_movement="pan_right",
                characters_present=["hero_unit"],
            ),
            StoryboardShot(
                shot_id="shot_02",
                description="Close-up of face.",
                duration_seconds=1.5,
                camera_movement="zoom_in",
            ),
        ],
    )
    assert sb.title == "Test Animatic"
    assert len(sb.shots) == 2
    assert sb.shots[0].duration_seconds == 3.0


def test_standard_poses_complete() -> None:
    assert "idle" in STANDARD_POSES
    assert "punch" in STANDARD_POSES
    assert "jump" in STANDARD_POSES
    assert "walk_contact" in STANDARD_POSES
    assert "walk_passing" in STANDARD_POSES

    # Punch pose has arm_r extended
    punch = STANDARD_POSES["punch"]
    assert punch.bone_angles["bone_arm_r"] > 70.0


def test_character_rig_spec_missing_fields() -> None:
    with pytest.raises(ValidationError):
        # Missing character_id
        CharacterRigSpec.model_validate({})
