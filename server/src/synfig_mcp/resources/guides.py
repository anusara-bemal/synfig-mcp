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
- `all` (default): The complete suite - all 93 tools: documents, canvases, scene
  building, layers, parameters and value nodes, animation, selection, history,
  effect recipes, style presets, character rigging, storyboards, production
  orchestration, licensed assets, rendering (frame, sequence, video, contact
  sheet, async jobs), visual review and schema introspection.
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
    "scene": """# End-to-End Scene Workflow (connect -> build -> animate -> render -> save)

Execute, do not just describe. Ordered tool sequence for a request like
"blue sky, green ground, red sun moving left->right, a walking character, easing,
render a preview, save":

1. `studio_info()` — check `bridge.reachable`. If false, `studio_launch()` and
   re-check. Never claim success while the bridge is unreachable.
2. `doc_new(width, height, fps, duration)` — create the project.
3. `doc_set_time_range(doc_id, start_time, end_time, fps)` — set the timeline
   (e.g. 0..5s for a 5-second move).
4. Build geometry in ONE undo step with `scene_build` (see
   `synfig_help('declarative_build')`): a `solid_color` sky, a `rectangle`/
   `solid_color` ground, a `circle` sun, and basic-shape character parts.
   Use `layer_add` only for single incremental layers.
5. Animate with `anim_animate_param` (batch waypoints, one undo step): sun
   `origin` from left to right across the time range; character `origin` for the
   walk. Set `interpolation` (e.g. "clamped"/"ease") for easing.
6. `render_frame(doc_id, time, ...)` — render a preview PNG and inspect it.
7. `doc_save(doc_id, file_path)` — persist the .sif. Verify the file exists.

Coordinates: origin is canvas centre, +Y up, 60 px per Synfig unit. Colors are
normalized `[0,1]` tagged unions. Confirm each step's returned state before the
next; on failure read the error code and correct, do not silently continue.
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
   preview. Look at `preview_base64` and decide what each number is.
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
    "production": """# AI Production Orchestration

`production_run` turns a structured brief into a dependency-ordered, resumable task
graph and executes it against the backend: create document -> build characters,
backgrounds, props and rigs -> lay out / camera / animate / effects per shot ->
validate -> render preview (and final when `render_final`) -> write manifest and
report. Every task is verified before it is reported done, and the run state is
saved after each task, so an interrupted run resumes exactly where it stopped.

## Brief schema
```json
{
  "title": "My Short", "slug": "my-short", "logline": "...",
  "width": 1920, "height": 1080, "fps": 24, "style": "shonen_action",
  "characters": [{
    "id": "hero", "manifest": "parts/manifest.json",
    "position": {"x": 300, "y": 950}, "height": 600,
    "actions": [{"motion": "walk", "start": 0, "end": 4}]
  }],
  "backgrounds": [{"id": "sky", "file": "bg.png"}],
  "props": [], "rigs": [],
  "episodes": [{"id": "ep1", "sequences": [{"id": "sq1", "shots": [{
    "id": "sh010", "title": "Hero enters", "duration": 4,
    "characters": ["hero"], "background": "sky",
    "effects": [{"name": "vignette", "params": {"opacity": 0.4}}],
    "camera": [{"time": 0, "zoom": 1}, {"time": 4, "zoom": 1.2}]
  }]}]}],
  "render_profiles": [{"name": "hd", "width": 1920, "height": 1080}],
  "checkpoints": ["layout", "animation"],
  "root": "C:/Users/me/Documents/SynfigMCP", "render_final": false
}
```
A character uses `manifest` (from `rig_sheet_slice`) or inline `parts` (same shape
as `scene_auto_build`). Backgrounds use `file` or `color`. Shots reference
characters/backgrounds by id.

## Human-approval checkpoints
Stages named in `checkpoints` (e.g. `layout`, `animation`, `render`) pause the run
with status `awaiting_approval`. Inspect with `production_status`, approve with
`production_approve(slug, checkpoint)`, then `production_resume(slug)` to continue.
Resume never bypasses an unapproved gate.

## On-disk layout
`<root>/projects/<slug>/` holds `project.json` (manifest: assets with sha256 and
license, versions, shots), `shots/*.sif`, `renders/<shot>/preview.png` and
`final/`, `checkpoints/state.json` (resumable state), `logs/events.jsonl`, and
`reports/production-report.{md,json}`.

## Tools
- `production_run(brief, dry_run)` - start; `dry_run=true` returns the plan only.
- `production_resume(slug, root, max_attempts)` - continue an interrupted run.
- `production_approve(slug, checkpoint, root)` - approve a gate.
- `production_status(slug, root)` - read-only manifest, task states, approvals.
""",
    "review": """# Visual Review Loop & Token Efficiency

## Adaptive Image Preview
- For quick alignment and critique: render at `320x240` (only ~103 Claude tokens / ~258 Gemini tokens).
- For multi-frame animation checks: use `render_contact_sheet` to composite multiple frames into one compact grid.
- Objective metrics flag luminance clipping, safe-area boundary violations, and strobe hazards without consuming vision tokens.
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
