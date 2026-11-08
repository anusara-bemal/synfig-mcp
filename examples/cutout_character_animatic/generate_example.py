#!/usr/bin/env python3
"""
Example generator for 100% original cut-out character and 3-shot animatic (Phase A4).
Constructs a complete scene graph purely from native Synfig primitives.
"""

import asyncio
import json
from pathlib import Path

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.characters.rigging import RiggingEngine
from synfig_mcp.characters.storyboard import StoryboardEngine
from synfig_mcp.recipes.engine import RecipeEngine

HERE = Path(__file__).resolve().parent


async def main() -> None:
    backend = HeadlessBackend()
    doc_info = await backend.doc_new(width=640, height=360, fps=24.0)
    doc_id = doc_info.id

    # 1. Assemble storyboard from script
    with open(HERE / "storyboard_script.json", "r", encoding="utf-8") as f:
        sb_spec = json.load(f)
    sb_spec["doc_id"] = doc_id

    sb_engine = StoryboardEngine(backend=backend)
    sb_res = await sb_engine.storyboard_from_script(sb_spec)
    print(f"Assembled animatic with {sb_res['total_shots']} shots ({sb_res['total_duration_seconds']}s).")

    # 2. Build cut-out character puppet from original geometry
    with open(HERE / "character_spec.json", "r", encoding="utf-8") as f:
        char_spec = json.load(f)
    char_spec["doc_id"] = doc_id

    rig_engine = RiggingEngine(backend=backend)
    rig_res = await rig_engine.character_rig_from_parts(char_spec)
    print(f"Rigged character '{rig_res['character_id']}' with {rig_res['parts_count']} parts.")

    # 3. Apply motion presets across keyframes
    # Shot 1: Idle
    await rig_engine.character_pose_apply(doc_id, "original_hero", "idle", time=0.0)
    # Shot 2: Walk passing
    await rig_engine.character_motion_apply(doc_id, "original_hero", "walk", start_time=2.5)
    # Shot 3: Punch action
    await rig_engine.character_motion_apply(doc_id, "original_hero", "punch", start_time=4.5)

    # 4. Apply effects stack for Shot 3 (Speed lines & Vignette)
    recipe_engine = RecipeEngine(backend=backend)
    await recipe_engine.apply_recipe(doc_id=doc_id, name="speed_lines")
    await recipe_engine.apply_recipe(doc_id=doc_id, name="vignette", params={"opacity": 0.4})

    # Save output SIF within sandbox-allowed temp root
    import tempfile

    out_sif = Path(tempfile.gettempdir()) / "output_animatic.sif"
    await backend.doc_save(doc_id, str(out_sif))
    print(f"Saved complete animatic project: {out_sif}")


if __name__ == "__main__":
    asyncio.run(main())
