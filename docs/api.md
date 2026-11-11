# MCP Tools API Reference

`synfig-mcp` exposes tools grouped into functional **profiles** configured via the `SYNFIG_MCP_PROFILE` environment variable (default: `all`).

The default profile exposes the **complete** Synfig feature set (all 74 tools) so a freshly installed server can create, animate, render and review animations without further configuration. The narrower profiles exist for clients with a tight context budget.

---

## 1. Profiles Overview

| Profile | Target Tokens (cl100k) | Tools Count | Primary Purpose |
|---|---|---|---|
| `all` (default) | < 22,000 (~18,500 actual) | 74 | Unrestricted full access to every tool: documents, layers, parameters, animation, rendering, review, assets. |
| `core` | < 3,000 (~2,700 actual) | 13 | Scene setup, declarative build, inspection, undo/redo, single-frame render. |
| `anim` | < 5,000 | 19 | Timeline navigation, keyframe manipulation, parameter animation, waypoints. |
| `fx` | < 5,500 | 24 | Layer tree modifications, effects recipes, style presets, parameters. |
| `rig` | < 4,000 | 17 | Bone hierarchies, cut-out character rigging, pose application, storyboards. |
| `assets` | < 2,500 | 12 | Licensed asset search, previews, hardened downloads, local imports. |
| `review` | < 4,500 | 18 | Visual critique, objective quality metrics, sequence review, diff heatmaps. |

---

## 2. Tool Reference by Profile

### Profile: `core` (Minimal Profile)
Designed for atomic declarative generation, quick iterations, and minimal token footprint.

- `health_check()`: Verifies server connectivity, active backend (`live` vs `headless`), and Synfig runtime status.
- `synfig_help(topic)`: Returns authoritative syntax, documentation, and schema guidance for a requested topic.
- `doc_new(width?, height?, fps?, name?)`: Creates a new animation document.
- `doc_open(file_path)`: Opens an existing `.sif`, `.sifz`, or `.sfg` document within the sandbox.
- `doc_save(file_path?)`: Saves the active document to disk.
- `doc_info()`: Returns active document dimensions, frame rate, duration, and canvas names.
- `scene_build(spec, dry_run?)`: **Primary construction tool**. Validates and executes a comprehensive scene specification (layers, hierarchies, parameters, waypoints, camera) in a single atomic undo step.
- `scene_export_spec(scope?, fields?)`: Serializes active canvas layers and parameters into a compact JSON scene spec.
- `scene_summary(budget_tokens?)`: Compact hierarchical text overview of the canvas with token-budget truncation.
- `history_undo()`: Rolls back the last atomic action.
- `history_redo()`: Reapplies the previously undone action.
- `render_frame(time?, width?, height?, quality?)`: Renders a single frame to PNG / WebP preview.

---

### Profile: `anim`
Timeline, keyframing, and parameter waypoint manipulation.

- `doc_set_time_range(start_time, end_time)`: Sets document timeline boundaries.
- `anim_time_get()` / `anim_time_set(time)`: Inspects or scrubs the timeline playhead.
- `anim_keyframe_add(time, description?)` / `anim_keyframe_list()` / `anim_keyframe_remove(time)`: Manages scene keyframes.
- `anim_waypoint_set(layer_name, param_name, time, value, interpolation?)`: Creates or updates a parameter waypoint with specific easing (clamped, smooth, linear, constant).
- `anim_waypoint_remove(layer_name, param_name, time)`: Deletes a parameter waypoint.
- `anim_animate_param(layer_name, param_name, waypoints)`: Batch-creates a sequence of waypoints for a parameter.
- `anim_interpolation_set(layer_name, param_name, interpolation)`: Sets default parameter interpolation mode.
- `param_get(layer_name, param_name)` / `param_set(layer_name, param_name, value)`: Reads or writes parameter values.

---

### Profile: `fx`
Procedural layer effects, parameter conversions, and visual style recipes.

- `layer_add(type, name?, desc?)` / `layer_remove(name)` / `layer_duplicate(name)`: Layer lifecycle tools.
- `layer_group(layer_names, group_name)` / `layer_ungroup(group_name)`: Hierarchical grouping.
- `layer_raise(name)` / `layer_lower(name)` / `layer_reorder(name, index)`: Z-order stack management.
- `recipe_list()`: Lists all 14 native anime and cinematic effects recipes.
- `recipe_info(name)`: Returns JSON Schema and parameter requirements for a recipe.
- `recipe_apply(name, params?, target?)`: Applies an effects recipe as an atomic undo step.
- `style_list()` / `style_get(name)` / `style_apply(name, time?)`: Inspects and applies aesthetic style presets.
- `param_convert(layer_name, param_name, valuenode_type)`: Converts static parameter to procedural valuenode (`add`, `scale`, `sine`, `timeloop`, etc.).

---

### Profile: `rig`
Cut-out character rigging, bone bindings, and storyboard sequences.

- `character_rig_from_parts(spec)`: Automatically creates bone hierarchies and binds anatomical SVG/PNG parts.
- `character_pose_apply(character_name, pose_name, time?)`: Sets character bones and parts to a keyframe pose preset (`idle`, `walk`, `run`, `punch`, `jump`).
- `character_motion_apply(character_name, motion_name, start_time, loops?)`: Generates multi-frame looped motion cycles.
- `storyboard_from_script(spec)`: Constructs an animatic project from shot lists, script notes, and camera directions.
- `selection_get()` / `selection_set(layer_names)`: Manages active layer selection.
- `param_export(layer_name, param_name, exported_name)`: Exports parameter valuenodes to canvas scope.

---

### Profile: `assets`
Safe internet asset search, vetting, downloading, and local ingest.

- `asset_search(query, provider?, license_type?, media_type?, page?, page_size?)`: Searches open media (Openverse / Wikimedia). Returns compact text metadata.
- `asset_preview(id, provider?)`: Returns a small image preview for visual inspection.
- `asset_download(id, provider?, target_name?)`: Downloads, validates, sanitizes, and registers asset in `assets/manifest.json`.
- `asset_import_local(source_path, target_name?, rights?, creator?, license?)`: Imports and sanitizes local vector/raster art with mandatory rights declaration.
- `import_asset(file_path, layer_name?)`: Instantiates an imported asset into the active canvas.

---

### Profile: `review`
Closed-loop visual critique, objective image analytics, and rendering pipelines.

- `review_frame(time?, focus?)`: Renders a frame preview alongside objective metrics (clipping, safe-areas, palette, photosensitivity/strobe warnings).
- `review_sequence(start_time?, end_time?, frames_count?, strategy?)`: Generates a compact contact sheet and per-frame motion/SSIM analytics.
- `review_compare(time_a?, time_b?, diff_threshold?)`: Compares two frames or iterations and generates a change heatmap.
- `render_contact_sheet(times?, columns?, width?)`: Generates a consolidated contact sheet image to conserve client tokens.
- `render_sequence(...)` / `render_video(...)`: Renders multi-frame PNG sequences or MP4 video files.
- `render_start(...)` / `render_status(...)` / `render_result(...)` / `render_cancel(...)`: Asynchronous background render job lifecycle.

---

### Profile: `all` (Default Profile)
Includes every tool of every profile above - all 74 tools: documents, canvases, scene building, layers, parameters and value nodes, animation and keyframes, selection, history, effects recipes, style presets, character rigging, storyboards, licensed assets, rendering (frame, sequence, video, contact sheet, async jobs), visual review and low-level schema inspection:
- `schema_list_layers()` / `schema_get_layer(layer_type)`
- `schema_list_valuenodes()`
- `schema_list_renderers()`
- `schema_list_targets()`
- `history_list()`
