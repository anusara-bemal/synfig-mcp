"""
Cut-out Characters, Bone Rigs, and Storyboard Animatic pipeline (Phase A4).
"""

from synfig_mcp.characters.models import (
    BoneSpec,
    CharacterPartSpec,
    CharacterRigSpec,
    PosePreset,
    StoryboardShot,
    StoryboardSpec,
)
from synfig_mcp.characters.rigging import RiggingEngine
from synfig_mcp.characters.storyboard import StoryboardEngine

__all__ = [
    "BoneSpec",
    "CharacterPartSpec",
    "CharacterRigSpec",
    "PosePreset",
    "RiggingEngine",
    "StoryboardEngine",
    "StoryboardShot",
    "StoryboardSpec",
]
