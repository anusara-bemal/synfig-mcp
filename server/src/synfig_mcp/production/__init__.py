"""
Anime production pipeline: one brief in, one complete animated project out.

This package composes the existing engines (storyboard, rigging, recipes,
assets, render, review) behind a single orchestration entry point, and adds the
three capability modules the pipeline needs but the server did not have:

* :mod:`~synfig_mcp.production.asset_generator` - procedural, IP-safe vector
  backgrounds and props.
* :mod:`~synfig_mcp.production.character_builder` - a high-level character
  brief expanded into rig-ready parts.
* :mod:`~synfig_mcp.production.rig_sheet` - a labeled model sheet rendered from
  a rigged character.

Scope note: the output is a deterministic *vector / cut-out* animation, not
generative hand-drawn sakuga.  See ``docs/scope.md`` and ``docs/production.md``.
"""

from synfig_mcp.production.models import (
    AssetRequest,
    CharacterDescriptor,
    ProductionBrief,
    ProductionReport,
    RenderOptions,
    StageReport,
)
from synfig_mcp.production.pipeline import AnimeProductionPipeline

__all__ = [
    "AnimeProductionPipeline",
    "AssetRequest",
    "CharacterDescriptor",
    "ProductionBrief",
    "ProductionReport",
    "RenderOptions",
    "StageReport",
]
