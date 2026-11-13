"""
Resource guides and topic documentation offloaded from tool docstrings.
Accessible via MCP resources (synfig://guide/{topic}) and the synfig_help tool.
"""

GUIDE_TOPICS: dict[str, str] = {
    "overview": """# Synfig MCP Overview & Best Practices

## Current document rule (like Blender's active scene)
- Always work in the **currently open/selected document** by default. Every tool's `doc_id` defaults to `doc_0`, which the bridge resolves to the Studio window you have selected.
- Never call `doc_new` or `doc_open` unless the user explicitly asked for a new file or a specific file to open. Creating a document silently discards the document the user is looking at.
- Before building, confirm the target with `doc_list` and `scene_summary`; pass the returned `doc_id` explicitly on every subsequent call.
- If no document is open (or `doc_list` is empty), tell the user instead of creating one unasked.

## Studio-Grade Workflow
1. Use declarative `scene_build` for assembling layers, parameters, and keyframes in a single atomic call instead of sequential round trips.
2. Verify visual results using `render_frame` (or `review_frame`) at low resolution (320x240) for fast iteration.
3. Switch tool profiles via `SYNFIG_MCP_PROFILE` to keep context token usage minimal.
4. All live edits in Synfig Studio are undoable via standard `Ctrl+Z` (mapped to `history_undo`).
""",
    "profiles": """# Synfig MCP Tool Profiles

Control tool footprint using environment variable `SYNFIG_MCP_PROFILE`:
- `all` (default): The complete suite - all 89 tools: documents, canvases, scene
  building, layers, parameters and value nodes, animation, selection, history,
  effect recipes, style presets, character rigging, storyboards, licensed assets, the anime
  production pipeline,
  rendering (frame, sequence, video, contact sheet, async jobs), visual review
  and schema introspection.
- `core`: Minimal set for document lifecycle, declarative build, inspection, undo
  (< 3,000 tokens).
- `anim`: Waypoint and keyframe animation tools, time controls, interpolation modes.
- `fx`: Layer filters, composites, parameter conversions, and recipes.
- `rig`: Cut-out character assembly, bone skeletons, valuenode exports and linking.
- `assets`: Search and import openly licensed artwork (Openverse, Wikimedia).
- `review`: Frame critiques, SSIM diff heatmaps, contact sheets, safety metrics.
""",
    "declarative_build": """# Declarative Scene Building (scene_build)

`scene_build` accepts a single structured JSON specification and applies it atomically:
- All layers are created in sequence.
- Parameters and colors are applied.
- Keyframe waypoints are registered.
- Grouping containers are assembled.
- The entire operation executes as **ONE single undo step** in Synfig Studio's history.

## Example Spec:
```json
{
  "doc_id": "doc_0",
  "layers": [
    {
      "id": "Background",
      "type": "solid_color",
      "params": {"color": {"type": "color", "r": 0.1, "g": 0.1, "b": 0.2, "a": 1.0}}
    },
    {
      "id": "Orb",
      "type": "circle",
      "params": {
        "radius": {"type": "real", "value": 1.5},
        "color": {"type": "color", "r": 1.0, "g": 0.7, "b": 0.1, "a": 1.0},
        "origin": {"type": "vector", "x": -3.0, "y": 0.0}
      },
      "waypoints": [
        {"param": "origin", "time": 0.0, "value": {"type": "vector", "x": -3.0, "y": 0.0}, "interpolation": "clamped"},
        {"param": "origin", "time": 2.0, "value": {"type": "vector", "x": 3.0, "y": 0.0}, "interpolation": "clamped"}
      ]
    }
  ],
  "groups": [{"id": "Scene", "layer_ids": ["Background", "Orb"]}]
}
```

## Available layer types
Call `schema_list_layers()` for the exact list of the installed Synfig build and
`schema_get_layer("<type>")` for the parameters, their value types and whether
they are writable.
""",
    "animation": """# Synfig MCP Animation System

## Waypoint Interpolation Modes
- `clamped`: Smooth cubic spline avoiding overshoot (recommended default).
- `linear`: Constant rate of change between waypoints.
- `halt`: Ease-in and ease-out with zero velocity at waypoints.
- `constant`: Step function hold until next waypoint.
- `auto`: Automatic spline mode (Synfig's TCB mode).
- `manual`: Fully manual handles; the waypoint keeps its stored tangents.

Any other value is rejected, because Synfig refuses to load a document with an
unknown interpolation.

## Parameter Values
Parameters take typed dictionaries:
- `real`: `{"type": "real", "value": 1.5}`
- `vector`: `{"type": "vector", "x": 0.0, "y": 1.0}`
- `color`: `{"type": "color", "r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}`
- `angle`: `{"type": "angle", "degrees": 45.0}`
- `bool`: `{"type": "bool", "value": true}`
- `string`: `{"type": "string", "value": "text"}`
- `integer`: `{"type": "integer", "value": 3}`
- `time`: `{"type": "time", "seconds": 1.5}`

Plain numbers and `[x, y]` pairs are coerced into the type the parameter
expects, and the nested spelling `{"type": "vector", "value": {...}}` is
accepted as well.
""",
    "characters": """# Rig sheet to animated scene

Three calls take a character sheet and a background to a moving shot.

1. `rig_sheet_slice(file_path)` - finds every part on the sheet and returns a numbered
   preview. Look at `preview_base64` and decide what each number is. Each part already
   carries its rig metadata (role, parent, pivot, z), a confidence score and a
   `rig_compatibility` report; enclosed gaps are reconstructed best-effort.
2. `rig_sheet_slice(file_path, names={"1": "head", "2": "torso", ...})` - writes one
   transparent PNG per named part and a `manifest.json`. Unnamed numbers (captions,
   stray marks) are left out.
3. `scene_auto_build(spec)` - builds everything in one undo step:

```json
{
  "width": 1920, "height": 1080, "fps": 24, "duration": 6,
  "background": {"file": "bg.png"},
  "characters": [{
    "id": "hero", "manifest": "sheet_parts/manifest.json",
    "position": {"x": 300, "y": 950}, "height": 600,
    "actions": [
      {"motion": "walk", "start": 0, "end": 4, "move_to": {"x": 1400, "y": 950}},
      {"motion": "wave", "start": 4}
    ]
  }],
  "camera": [{"time": 0, "zoom": 1}, {"time": 6, "zoom": 1.3, "center": {"x": 1400, "y": 600}}],
  "save_path": "shot_01.sif"
}
```

## Naming parts
Parts named by body role get their joints and hierarchy automatically:
`torso` (root), `head`, `neck`, `hips`, `upper_arm_l/r`, `forearm_l/r`, `hand_l/r`,
`upper_leg_l/r`, `lower_leg_l/r`, `foot_l/r`, or single-piece `arm_l/r`, `leg_l/r`.
`_l` limbs are drawn behind the torso, `_r` limbs in front. Anything else (hair, tail,
sword) needs `parent` and `attach`.

## Fixing joints
The defaults are estimates. Look at the preview, then override per part:
- `pivot: {fx, fy}` - the joint inside the part image (0,0 = top-left, 1,1 = bottom-right).
- `attach: {fx, fy}` - where that joint sits on the parent image.
- `z` - stacking inside the parent: negative is behind the parent art.
- `layout: "in_place"` keeps the sheet positions (for parts exported in place).

## Animating
- Motions: walk, run, idle, talk (loop), wave, jump, nod, punch (once), rest, pose, move.
- Angles are degrees from the rest pose, counter-clockwise; `flip: true` mirrors a character.
- `character_motion_apply` and `character_pose_apply(angles={"upper_arm_r": 120})` refine a
  built character; the joint layers are `<id>_<part>_rot`, the position layer `<id>_pos`.
- Check the result with `review_sequence`, export with `render_video`.

## Limits
- Joints are rotate layers (forward kinematics); there is no IK, mesh deformation or lip-sync.
- Without `doc_id` a new document is created; pass `doc_id` to build into the open one.
""",
    "review": """# Visual Review Loop & Token Efficiency

## Adaptive Image Preview
- For quick alignment and critique: render at `320x240` (only ~103 Claude tokens / ~258 Gemini tokens).
- For multi-frame animation checks: use `render_contact_sheet` to composite multiple frames into one compact grid.
- Objective metrics flag luminance clipping, safe-area boundary violations, and strobe hazards without consuming vision tokens.
""",
    "production": """# Anime Production Pipeline (produce_anime_project)

One brief in, one renderable project out. The pipeline runs seven stages:
document -> storyboard -> characters -> assets -> scene_build -> style -> render -> review.

## Brief shape
```json
{
  "title": "Skyline Run",
  "style": "shonen_action",
  "width": 1280, "height": 720, "fps": 24.0, "duration": 6.0, "seed": 7,
  "shots": [{"shot_id": "shot_01", "description": "rooftop chase", "duration_seconds": 3.0,
             "camera_movement": "pan_right", "characters_present": ["hero"]}],
  "characters": [{"id": "hero", "archetype": "humanoid", "height": 420.0,
    "palette": ["#2b3a55", "#ff5c5c", "#f2e8cf", "#6fa8dc"],
    "facing": "right", "position": {"x": 200, "y": 660}, "z": 10,
    "actions": [{"motion": "run", "start": 0.0, "end": 6.0, "move_to": {"x": 1000, "y": 660}}]}],
  "assets": [{"id": "tree1", "kind": "prop", "procedural": {"generator": "tree"},
              "position": {"x": 300, "y": 660}, "height": 180}],
  "background": {"generator": "landscape"},
  "camera": [{"time": 0.0, "zoom": 1.0, "center": {"x": 640, "y": 360}}],
  "render": {"video": true, "video_format": "mp4", "contact_sheet": true,
             "review": true, "preview_frames": 4},
  "output_dir": "out", "save_path": "out/reel.sif"
}
```
- `archetype`: `humanoid` or `chibi`. `facing`: `left` or `right`.
- Motions: walk, run, idle, wave, jump, nod, talk, rest, pose, move.
- Positions are canvas pixels from the top-left; a character stands with its feet on `position`.
- `assets[].kind`: `background`, `prop` or `texture`. Sources: `procedural: {generator}` or
  `search: {query, provider, license}` (opt-in network fetch; every asset is license-checked).
- Styles: shonen_action, dark_fantasy, supernatural_noir, cyber_mecha, retro_anime.

## Other entry points
- `production_plan(brief)`: dry-run; reports stages and layer counts without building.
- `character_model_sheet(descriptor)`: labeled front/three-quarter/side sheet in its own document.
- `procedural_asset_list()` / `procedural_asset_generate(...)`: the IP-safe vector generators.
- `sprite_slice(source, output_dir, strategy)`: slice a sprite sheet into rig-ready part PNGs.
- CLI: `synfig-mcp produce brief.json [--dry-run] [--json] [--output-dir DIR]`.

## Limits
- Rendering needs the Synfig CLI on PATH; without it the document is still saved and the
  render/review stages report "skipped" rather than failing.
- Characters are cut-out (vector) rigs driven by forward-kinematic rotations; no IK or mesh deform.
""",
}


def get_guide_content(topic: str) -> str:
    """Retrieve guide content for topic, falling back to overview and list of topics."""
    t = topic.lower().strip()
    if t in GUIDE_TOPICS:
        return GUIDE_TOPICS[t]
    available = ", ".join(sorted(GUIDE_TOPICS.keys()))
    return (
        f"# Topic '{topic}' not found\n\n"
        f"Available guide topics: {available}.\n\n"
        f"Run `synfig_help('overview')` for general guidance."
    )
