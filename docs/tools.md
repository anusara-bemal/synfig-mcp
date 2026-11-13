# Synfig MCP Tool Reference

> Complete typed reference for all 93 Model Context Protocol (MCP) tools provided by the `synfig-mcp` server.
> Each tool includes typed input schemas, execution semantics, and LLM-targeted guidance.

> Generated from the live tool registry by `scripts/generate_tool_docs.py`.

## Table of Contents

- [Animation & Keyframes](#animation-keyframes) (10 tools)
- [Canvas & Scene](#canvas-scene) (10 tools)
- [Character Rigging](#character-rigging) (3 tools)
- [Core & Diagnostics](#core-diagnostics) (2 tools)
- [Document Management](#document-management) (8 tools)
- [Effect Recipes](#effect-recipes) (3 tools)
- [History & Undo](#history-undo) (3 tools)
- [Layer Manipulation](#layer-manipulation) (9 tools)
- [Licensed Assets](#licensed-assets) (4 tools)
- [Other](#other) (8 tools)
- [Parameters & ValueNodes](#parameters-valuenodes) (7 tools)
- [Production Orchestration](#production-orchestration) (4 tools)
- [Render & Preview](#render-preview) (8 tools)
- [Schema & Introspection](#schema-introspection) (5 tools)
- [Selection](#selection) (2 tools)
- [Storyboards](#storyboards) (1 tools)
- [Style Presets](#style-presets) (3 tools)
- [Visual Review](#visual-review) (3 tools)

**Total: 93 tools.**

## Animation & Keyframes

### `anim_time_get`

*Profiles: all, anim*

Get the current timeline cursor / playhead position in seconds.

Returns: Object with 'time': float in seconds.

Gotcha: Confusing frame numbers with seconds. Synfig time is in seconds (frame = seconds * fps).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `anim_time_set`

*Profiles: all, anim*

Seek the timeline cursor / playhead to a specific time in seconds.

Returns: Object with 'time': float in seconds.

Gotcha: Passing negative time.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `time` | `number` | Yes | - |

---

### `anim_keyframe_list`

*Profiles: all, anim*

List all keyframes defined on the timeline.

Returns: Array of keyframe objects, each with 'time', 'time_string', 'description', and 'active'.

Gotcha: Assuming keyframes are automatically created without calling anim_keyframe_add.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_path` | `string` | No | - |

---

### `anim_keyframe_add`

*Profiles: all, anim*

Add a keyframe at the specified time to lock parameter values into an animation pose.

Returns: Object with 'time', 'description', 'active', and 'diff'.

Gotcha: Adding duplicate keyframes at the exact same time timestamp.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `time` | `number` | Yes | - |
| `description` | `string` | No | - |
| `active` | `boolean` | No | - |
| `canvas_path` | `string` | No | - |

---

### `anim_keyframe_remove`

*Profiles: all, anim*

Delete a keyframe at the specified time.

Returns: Object with 'removed': bool.

Gotcha: Specifying a time where no keyframe exists.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `time` | `number` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `anim_waypoint_list`

*Profiles: all, anim*

List the waypoints of an animated parameter.

Returns: Array of {time, time_string, value, interpolation_in, interpolation_out} objects.

Gotcha: The parameter has to be animated - a static parameter returns an empty list.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |

---

### `anim_waypoint_set`

*Profiles: all, anim*

Insert or update a waypoint for a layer parameter at a specific timeline timestamp.

Returns: Dictionary containing 'waypoint' details and 'interpolated_value'.

Gotcha: Passing invalid interpolation strings (valid: 'linear', 'constant', 'halt', 'clamped', 'auto', 'manual').

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `time` | `number` | Yes | - |
| `value` | `any` | Yes | - |
| `interpolation_in` | `string` | No | - |
| `interpolation_out` | `string` | No | - |

---

### `anim_waypoint_remove`

*Profiles: all, anim*

Remove a waypoint from a layer parameter at a given time.

Returns: Object with 'removed': bool.

Gotcha: Providing a time that does not match an existing waypoint.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `time` | `number` | Yes | - |

---

### `anim_animate_param`

*Profiles: all, anim*

Define a full parameter animation trajectory using a batch of waypoints in ONE single undo step.

Returns: Object containing 'count': number of waypoints applied.

Gotcha: Omitting 'time' or 'value' from waypoint dictionary items.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `waypoints` | `array` | Yes | - |

---

### `anim_interpolation_set`

*Profiles: all, anim*

Set default canvas waypoint interpolation or change interpolation on existing waypoints.

Returns: Object with 'success': bool and 'interpolation'.

Gotcha: Using unsupported interpolation types.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `interpolation` | `string` | Yes | - |
| `layer_id` | `any` | No | - |
| `param_name` | `any` | No | - |

---

## Canvas & Scene

### `canvas_list`

*Profiles: all*

List all canvas paths in the document (root canvas and nested group/subcanvases).

Returns: Object containing 'canvases': array of path strings (e.g. ['/', '/CharacterGroup']).

Gotcha: Assuming only the root canvas exists when layers are inside nested groups.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `scene_build`

*Profiles: all, core*

Apply a declarative scene spec {doc_id, layers:[{id,type,params}], groups}. Layer id required. Returns created/modified diff. Defaults to active document; don't call doc_new/doc_open first.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

### `scene_export_spec`

*Profiles: all, core*

Export scene state as a SceneBuildSpec JSON for scene_build. Use fields=['params','waypoints'] to trim payload.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `scope` | `string` | No | - |
| `fields` | `any` | No | - |

---

### `scene_summary`

*Profiles: all, anim, assets, core, fx, review, rig*

Token-bounded summary of canvas size, fps, duration, and layer hierarchy. Call first to confirm the target document before building.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `budget_tokens` | `integer` | No | - |

---

### `canvas_create`

*Profiles: all, rig*

Create a child canvas (a sub-canvas that group layers can reference).

Returns: Object with 'canvas_id' and a diff summary.

Gotcha: The canvas id must be unique inside the document.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_id` | `string` | No | - |

---

### `canvas_rename`

*Profiles: all, rig*

Rename a child canvas.

Returns: Object with 'canvas_id', 'name', 'previous_name' and a diff summary.

Gotcha: Passing the id of a canvas that does not exist.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_id` | `string` | No | - |
| `name` | `string` | No | - |

---

### `canvas_delete`

*Profiles: all, rig*

Delete a child canvas and everything inside it.

Returns: Object with 'canvas_id' and a diff summary.

Gotcha: The root canvas cannot be deleted.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_id` | `string` | No | - |

---

### `canvas_set_properties`

*Profiles: all, rig*

Change canvas resolution, fps, time range or background colour. Returns updated properties and diff. end_time must be after start_time.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_id` | `string` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |
| `fps` | `any` | No | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |
| `background_color` | `any` | No | - |

---

### `scene_tree`

*Profiles: all*

Get the full visual hierarchy of layers in depth order (topmost layer at index 0).

Returns: Hierarchical layer tree with child layers for PasteCanvas groups.

Gotcha: Looking for a layer ID without checking nested 'children' inside group layers.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_path` | `string` | No | - |

---

### `scene_auto_build`

*Profiles: all, rig*

Build a whole animated shot in one call: background, rigged characters, props, camera, audio.

One undo step; validated before the document changes. spec: {width, height, fps, duration,

background, characters, props, camera, audio, save_path, preview}. Positions are canvas pixels

from top-left; a character's feet sit on position. Full spec: synfig_help('declarative_build').

Returns doc_id, characters, props, warnings, saved_to, preview. Parts named by body role get

default joints; others need parent + attach.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

## Character Rigging

### `character_rig_from_parts`

*Profiles: all, rig*

Assemble a jointed cut-out character from part images in an open document. spec: {doc_id, id,

manifest | parts, position, height, flip, layout, actions}. Each part gets a joint layer

<id>_<part>_rot; turning a part carries its children. Returns root group, parts, roles, joint ids.

dry_run=true previews; pivot/attach are image fractions. See synfig_help('characters').

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

### `character_pose_apply`

*Profiles: all, rig*

Key a pose on a rigged character: preset (idle, punch, jump, walk_contact, walk_passing) or

angles={"upper_arm_r":120,...} (degrees from rest). Returns keyed joints and missing joints.

Fails if none of the addressed joints exist; nothing is keyed silently.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `character_id` | `string` | No | - |
| `pose_name` | `string` | No | - |
| `time` | `number` | No | - |
| `angles` | `any` | No | - |

---

### `character_motion_apply`

*Profiles: all, rig*

Animate a rigged character: walk, run, idle, talk (loop), wave, jump, nod, punch (once), rest,

move. move_to={x,y} (canvas pixels) travels there by end_time. Returns keyframe times, waypoint

count, animated layers, skipped joints. Character must come from character_rig_from_parts/scene_auto_build.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `character_id` | `string` | No | - |
| `motion_name` | `string` | No | - |
| `start_time` | `number` | No | - |
| `end_time` | `any` | No | - |
| `speed` | `number` | No | - |
| `move_to` | `any` | No | - |

---

## Core & Diagnostics

### `synfig_help`

*Profiles: all, anim, assets, core, fx, review, rig*

Get Synfig MCP guidance by topic (overview, scene, profiles, declarative_build, animation, characters, production, review). Returns Markdown guide text.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `topic` | `string` | No | - |

---

### `health_check`

*Profiles: all, anim, assets, core, fx, review, rig*

Check readiness and active backend ('live' Studio vs 'headless' SIF engine). Returns backend, connected, studio_running, details. In auto mode a blank canvas usually means Studio is open without its MCP bridge; check details.warning.

#### Parameters

*No parameters required.*

---

## Document Management

### `doc_list`

*Profiles: all, anim, assets, core, fx, review, rig*

List open documents. Returns array with id, name, width, height, fps, duration_frames. Use these doc_id values, not file paths.

#### Parameters

*No parameters required.*

---

### `doc_info`

*Profiles: all, anim, assets, core, fx, review, rig*

Get document metadata: width, height, fps, start_time, end_time, duration_frames. Requires a valid doc_id.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `doc_new`

*Profiles: all, core*

Create a new blank document. Returns id, name, dimensions, fps. ONLY call when the user explicitly asked for a new document; otherwise reuse the open document from doc_list.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |
| `fps` | `number` | No | - |

---

### `doc_open`

*Profiles: all, core*

Open an existing project (.sif, .sifz, .sfg). ONLY call when the user explicitly asked to open this file; otherwise build in the currently open document.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file_path` | `string` | Yes | - |

---

### `doc_save`

*Profiles: all, core*

Save document to .sif/.sifz/.sfg. Returns file_path. Pass file_path for a new doc_new document that has no default path.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `file_path` | `any` | No | - |

---

### `doc_close`

*Profiles: all*

Close an open document and unload it from memory.

Returns: Object containing 'closed': true.

Gotcha: Closing without saving changes first with doc_save, unless force=True is passed.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `force` | `boolean` | No | - |

---

### `doc_set_properties`

*Profiles: all*

Update document resolution, fps, time bounds, or name. Returns updated DocumentInfo. end_time must be after start_time.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `name` | `any` | No | - |
| `desc` | `any` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |
| `fps` | `any` | No | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |

---

### `doc_set_time_range`

*Profiles: all, anim*

Set canvas animation playback timeline start time, end time, and framerate.

Returns: Updated DocumentInfo containing 'start_time', 'end_time', and 'fps'.

Gotcha: Setting start_time greater than or equal to end_time.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |
| `fps` | `any` | No | - |

---

## Effect Recipes

### `recipe_list`

*Profiles: all, fx*

List all parameterized anime effects recipes (speed lines, vignette, grain, blur, etc.).

Returns: List of recipe descriptors with category, description, and required native layers.

Gotcha: Check parameter schema using recipe_info before calling recipe_apply.

#### Parameters

*No parameters required.*

---

### `recipe_info`

*Profiles: all, fx*

Get parameter specification, defaults, and usage notes for a named recipe.

Returns: RecipeManifest containing parameters, types, defaults, and notes.

Gotcha: Recipe names are case-insensitive snake_case.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `name` | `string` | Yes | - |

---

### `recipe_apply`

*Profiles: all, fx*

Apply a parameterized visual effect recipe atomically as a single undo step.

Returns: Diff object with created layers and applied parameter values.

Gotcha: Use dry_run=true to preview generated layer tree before mutating document.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `name` | `string` | No | - |
| `params` | `any` | No | - |
| `target_layer_or_group` | `any` | No | - |
| `dry_run` | `boolean` | No | - |

---

## History & Undo

### `history_undo`

*Profiles: all, anim, assets, core, fx, review, rig*

Undo the previous action. One mutating MCP call = one undo step. Returns success (false when the stack is empty).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `history_redo`

*Profiles: all, anim, assets, core, fx, review, rig*

Redo the previously undone action. Returns success. A new mutating action clears the redo stack.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `history_list`

*Profiles: all*

Query current undo and redo stack depths.

Returns: Object with 'undo_count' and 'redo_count'.

Gotcha: Assuming infinite redo after performing a new mutation.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

## Layer Manipulation

### `layer_add`

*Profiles: all, fx*

Add a visual layer (circle, rectangle, star, solid_color, text, PasteCanvas, ...). Returns layer_id, layer_type, depth, diff. Query schema_list_layers for valid types.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_type` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |
| `description` | `any` | No | - |
| `params` | `any` | No | - |

---

### `layer_remove`

*Profiles: all, fx*

Delete a layer from the composition.

Returns: Object with 'removed': bool and 'diff' summary.

Gotcha: Passing a layer index instead of the layer description/id.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_duplicate`

*Profiles: all, fx*

Duplicate an existing layer, creating an identical copy placed directly above the original.

Returns: Details of the newly created duplicate layer.

Gotcha: Targeting a non-existent layer_id.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_reorder`

*Profiles: all, fx*

Move a layer to a specific visual depth (depth 0 is topmost, in front of all other layers).

Returns: Object with 'reordered': bool and new 'depth'.

Gotcha: Assuming depth 0 is bottom (in Synfig, depth 0 is top / closest to camera).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `new_depth` | `integer` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_raise`

*Profiles: all, fx*

Raise a layer by 1 position (closer to camera, depth - 1).

Returns: Object with 'raised': bool.

Gotcha: Calling on a layer that is already at depth 0 (topmost).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_lower`

*Profiles: all, fx*

Lower a layer by 1 position (further from camera, depth + 1).

Returns: Object with 'lowered': bool.

Gotcha: Calling on a layer that is already bottom-most.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_group`

*Profiles: all, fx, rig*

Group multiple layers into a PasteCanvas composite layer.

Returns: Details of the created group layer and list of grouped layers.

Gotcha: Passing empty layer_ids list.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_ids` | `array` | Yes | - |
| `group_name` | `string` | No | - |
| `canvas_path` | `string` | No | - |

---

### `layer_ungroup`

*Profiles: all, fx, rig*

Ungroup a PasteCanvas layer, releasing its children into the parent canvas.

Returns: Object with 'ungrouped_layers': list of released layer IDs.

Gotcha: Calling ungroup on a non-group layer (e.g. a circle).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `import_asset`

*Profiles: all, assets*

Import an external asset file (e.g. .png, .jpg, .svg, .wav, .ogg) into the canvas.

Returns: Layer dictionary for the newly imported image or sound layer.

Gotcha: Verify document ID before invoking.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `file_path` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

## Licensed Assets

### `asset_search`

*Profiles: all, assets*

Search permitted open-license asset providers returning compact text metadata.

Returns: {results: [{id, title, creator, license, provider}], count}.

Gotcha: Returns text only to conserve LLM tokens; use asset_preview to view thumbnail.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `query` | `string` | Yes | - |
| `provider` | `string` | No | - |
| `license_type` | `any` | No | - |
| `page` | `integer` | No | - |

---

### `asset_preview`

*Profiles: all, assets*

Fetch a small thumbnail preview image of an asset in base64.

Returns: {success, asset_id, thumbnail_base64}.

Gotcha: Previews are low-resolution to keep vision token usage below 200 tokens.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `asset_id` | `string` | Yes | - |
| `provider` | `string` | No | - |

---

### `asset_download`

*Profiles: all, assets*

Download and verify licensed asset: evaluates license policy, SSRF checks, sanitizes SVG/raster, hashes SHA-256.

Returns: {success, asset_id, local_path, sha256, attribution}.

Gotcha: Non-commercial (NC) and No-Derivatives (ND) licenses are blocked by default.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `asset_id` | `string` | Yes | - |
| `provider` | `string` | No | - |

---

### `asset_import_local`

*Profiles: all, assets*

Register a local file in the project provenance manifest with mandatory rights declaration.

Returns: {success, asset_id, rights, sha256, local_path}.

Gotcha: Rights must be explicitly declared as 'own', 'licensed', 'cc0', or 'public-domain'.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file_path` | `string` | Yes | - |
| `rights` | `string` | Yes | - |
| `title` | `string` | No | - |
| `creator` | `string` | No | - |
| `license_code` | `string` | No | - |

---

## Other

### `studio_launch`

*Profiles: all*

Launch patched Synfig Studio with the MCP bridge enabled; waits until reachable.

Returns: 'launched', 'pid', 'bridge_ready', or 'already_running'.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `wait_seconds` | `number` | No | - |

---

### `studio_info`

*Profiles: all, anim, assets, core, fx, review, rig*

Inspect connected Studio: versions and open documents with file paths.

Returns: 'backend', 'studio_version', 'docs' [{doc_id, name, file_path}].

#### Parameters

*No parameters required.*

---

### `access_approve`

*Profiles: all, assets, core*

Approve a folder (e.g. Downloads) for file access; remembered across sessions. System/credential/drive roots rejected.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `folder` | `string` | Yes | - |
| `reason` | `string` | No | - |

---

### `access_revoke`

*Profiles: all, assets*

Remove a previously approved folder from file access.

Returns: 'revoked' (bool), 'folder'.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `folder` | `string` | Yes | - |

---

### `access_status`

*Profiles: all, assets*

Show file access policy: approved folders, project dirs, asset/attachment counts.

Returns: JSON describing every source of file authority this session.

#### Parameters

*No parameters required.*

---

### `project_refresh`

*Profiles: all, assets*

Re-read the open project via the native bridge; authorise its dir and imported assets.

Returns: 'registered', 'project_dir', 'file_path', asset counts.

#### Parameters

*No parameters required.*

---

### `rig_bone_add`

*Profiles: all, rig*

Add a bone to a skeleton layer (cut-out rigging). Returns the created bone and diff. Needs Synfig Studio; headless cannot create bones.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `layer_id` | `string` | No | - |
| `time` | `number` | No | - |
| `origin_x` | `number` | No | - |
| `origin_y` | `number` | No | - |
| `angle` | `number` | No | - |
| `width` | `number` | No | - |
| `tip_width` | `number` | No | - |
| `parent_index` | `integer` | No | - |

---

### `rig_sheet_slice`

*Profiles: all, assets, rig*

Cut a rig sheet (one image, many parts) into one transparent PNG per part. Call once without

names to see preview_base64 (numbered boxes), then again with names={"1":"head",...} to export.

Returns parts, manifest, output_dir, preview_base64. Needs transparent/uniform background; name

parts by body role (head, torso, upper_arm_l, ...) so rigs auto-assemble. See synfig_help('characters').

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file_path` | `string` | Yes | - |
| `names` | `any` | No | - |
| `output_dir` | `any` | No | - |
| `min_area` | `any` | No | - |
| `merge_gap` | `integer` | No | - |
| `bg_tolerance` | `integer` | No | - |
| `preview` | `boolean` | No | - |

---

## Parameters & ValueNodes

### `param_get`

*Profiles: all, anim, fx*

Read the typed value of a specific parameter on a layer.

Returns: Tagged union SynfigValue object (e.g. {'type': 'real', 'value': 2.5} or {'type': 'color', 'r': 1.0, ...}).

Gotcha: Misspelling parameter names (e.g. 'pos' vs 'origin'). Use schema_get_layer() to check parameter names.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `param_set`

*Profiles: all, anim, fx*

Set or update the value of a parameter on a layer.

Returns: Object showing 'before' and 'after' values and diff summary.

Gotcha: Passing untagged raw numbers for vector types instead of {'type': 'vector', 'x': 0.0, 'y': 0.0}.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `value` | `any` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `param_convert`

*Profiles: all, fx*

Convert a layer parameter into a linkable ValueNode (e.g. 'linear', 'add', 'subtract', 'scale', 'composite', 'sine', 'duplicate', 'range', 'step', 'absolute').

Returns: Object containing 'layer_id', 'param_name', and converted ValueNode 'type'.

Gotcha: Converting to an incompatible type (numeric parameters accept 'linear'/'add'/'subtract'/'scale'/'sine'; 'composite' only works on vector and color parameters).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `type` | `string` | Yes | - |

---

### `param_export`

*Profiles: all, rig*

Export a parameter's ValueNode to the canvas value node library for sharing across layers.

Returns: Object containing exported 'name' and diff summary.

Gotcha: Exporting under a name that already exists in the document library.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `name` | `string` | Yes | - |

---

### `param_list`

*Profiles: all*

List every parameter of a layer with its current value.

Returns: Array of {name, value} objects.

Gotcha: The list contains the layer's dynamic parameters (including the ones Synfig adds itself).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `param_link`

*Profiles: all, anim, fx, rig*

Link a parameter to an exported ValueNode so it follows the shared value.

Returns: Object containing 'layer_id', 'param_name', 'link_id' and a diff summary.

Gotcha: The value node must be exported first with param_export(); linking an unknown id fails.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `link_id` | `string` | Yes | - |

---

### `param_unexport`

*Profiles: all, rig*

Unexport a previously exported ValueNode from the canvas library.

Returns: Object confirming unexported 'name'.

Gotcha: Attempting to unexport a node that is still referenced by multiple active parameters.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `name` | `string` | Yes | - |

---

## Production Orchestration

### `production_run`

*Profiles: all, rig*

Run a whole production from a structured brief as a dependency-ordered, resumable task

graph: documents, characters, backgrounds, layout, animation, effects, QC, previews,

manifest and report. brief: {title, episodes[].sequences[].shots[], characters[],

backgrounds[], props[], rigs[], style, checkpoints[], root, render_final}. Stages named in

checkpoints pause until production_approve; state is saved after every task so

production_resume can continue. dry_run=true returns the plan without touching anything.

Full brief schema: synfig_help('production'). Returns status, task_states, awaiting_approval.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `brief` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

### `production_resume`

*Profiles: all, rig*

Continue an interrupted production from its last checkpoint. Completed tasks are not

repeated; shot files on disk are re-opened and verified. root defaults to the configured

workspace. Returns the same status/task_states structure as production_run.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `slug` | `string` | Yes | - |
| `root` | `any` | No | - |
| `max_attempts` | `integer` | No | - |

---

### `production_approve`

*Profiles: all, rig*

Approve a human-approval checkpoint (e.g. 'layout', 'animation') so the paused

production can continue. Call production_resume afterwards to run the next stages.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `slug` | `string` | Yes | - |
| `checkpoint` | `string` | Yes | - |
| `root` | `any` | No | - |

---

### `production_status`

*Profiles: all, rig*

Inspect a production: manifest status, per-task states, pending approvals, versions,

registered assets and the latest log events. Read-only.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `slug` | `string` | Yes | - |
| `root` | `any` | No | - |

---

## Render & Preview

### `render_frame`

*Profiles: all, core, review*

Render one frame to an image (PNG, JPEG, BMP, GIF, PPM). Returns success, output_path, time. Sequence encoders like ffmpeg need render_sequence instead.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `output_path` | `string` | Yes | - |
| `time` | `number` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |
| `target` | `string` | No | - |

---

### `render_sequence`

*Profiles: all, review*

Render an image sequence across a time range. Returns list of output frame paths. Pass an output directory, not a file path.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `output_dir` | `string` | Yes | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |
| `fps` | `any` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |
| `target` | `string` | No | - |
| `job_id` | `any` | No | - |

---

### `render_start`

*Profiles: all, review*

Start an async render job; returns job_id immediately with status='running' and output_dir.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `output_dir` | `string` | Yes | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |
| `fps` | `any` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |
| `target` | `string` | No | - |

---

### `render_status`

*Profiles: all, review*

Query an async render job's status/progress. Returns job_id and status (running/completed/cancelled/failed).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `job_id` | `string` | Yes | - |

---

### `render_result`

*Profiles: all, review*

Get final frames of a completed render job. Returns job_id, status, frames (file paths).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `job_id` | `string` | Yes | - |

---

### `render_cancel`

*Profiles: all, review*

Cancel an in-flight render job by job_id. Returns cancelled, job_id, message.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `job_id` | `string` | Yes | - |

---

### `render_video`

*Profiles: all, review*

Render a time range straight to video (.mp4 or .gif). Returns success, output_path.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `output_path` | `string` | Yes | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |
| `fps` | `any` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |

---

### `render_contact_sheet`

*Profiles: all, review*

Render keyframe timestamps into a contact-sheet grid image. Returns success, output_path. cols/rows must be > 0.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `output_path` | `string` | Yes | - |
| `cols` | `integer` | No | - |
| `rows` | `integer` | No | - |
| `width` | `any` | No | - |
| `height` | `any` | No | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |

---

## Schema & Introspection

### `schema_list_layers`

*Profiles: all*

List all layer types supported by the installed Synfig build (e.g. 'circle', 'rectangle', 'star', 'text', 'blur', 'outline').

Returns: Alphabetical list of supported layer type strings.

Gotcha: The list is introspected from the Synfig binary, so it reflects the exact build installed on this machine.

#### Parameters

*No parameters required.*

---

### `schema_get_layer`

*Profiles: all*

Get parameter schemas, default values, and hints for a specific layer type.

Returns: LayerTypeInfo object containing 'name', 'version', 'description', and 'params' dictionary.

Gotcha: Looking for a parameter that belongs to a different layer type.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `layer_type` | `string` | Yes | - |

---

### `schema_list_valuenodes`

*Profiles: all*

List supported valuenode link converter types (e.g. 'composite', 'add', 'sine', 'random').

Returns: List of valuenode type names.

Gotcha: Confusing valuenodes with layer parameters.

#### Parameters

*No parameters required.*

---

### `schema_list_targets`

*Profiles: all*

List supported render output targets (e.g. 'png', 'jpeg', 'bmp', 'gif', 'ffmpeg').

Returns: List of target format strings.

Gotcha: Passing unsupported extensions (e.g. 'webp').

#### Parameters

*No parameters required.*

---

### `schema_list_renderers`

*Profiles: all*

List available rendering engines (e.g. 'software', 'software-draft', 'safe').

Returns: List of renderer names.

Gotcha: Assuming GPU renderer is present when Synfig is using Cobra software renderer.

#### Parameters

*No parameters required.*

---

## Selection

### `selection_get`

*Profiles: all, rig*

Get the list of currently selected layer IDs in Studio.

Returns: Object with 'selected_layers': array of layer IDs.

Gotcha: In headless mode the selection is virtual - it only mirrors what was selected through the MCP.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `selection_set`

*Profiles: all, rig*

Set the active layer selection in Studio.

Returns: Object with 'selected_layers': array of newly selected layer IDs.

Gotcha: Passing non-existent layer IDs.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_ids` | `array` | Yes | - |

---

## Storyboards

### `storyboard_from_script`

*Profiles: all, rig*

Assemble a multi-shot animatic timeline from a structured storyboard script.

Returns: Shot manifest with calculated start/end times, camera moves, and animatic duration.

Gotcha: Establishes non-destructive camera transform layers for every scripted shot.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

## Style Presets

### `style_list`

*Profiles: all, fx*

List all generic anime style presets (shonen_action, dark_fantasy, supernatural_noir, etc.).

Returns: List of style descriptors with palette, contrast, grain, line weight, and recipes.

Gotcha: Adheres to strict IP policy (generic aesthetic traits only, no franchise names).

#### Parameters

*No parameters required.*

---

### `style_get`

*Profiles: all, fx*

Get detailed configuration of a generic style preset.

Returns: Complete StylePreset dictionary with palette, grain, contrast, and default recipe stack.

Gotcha: Style names are generic (e.g. 'shonen_action', 'dark_fantasy').

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `name` | `string` | Yes | - |

---

### `style_apply`

*Profiles: all, fx*

Apply a complete anime aesthetic style stack (grading, grain, vignette, recipes) atomically.

Returns: Summary of applied recipes and color parameters.

Gotcha: Applies all recipes in the style's default stack as atomic scene operations.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `name` | `string` | No | - |
| `dry_run` | `boolean` | No | - |

---

## Visual Review

### `review_frame`

*Profiles: all, review*

Render a single frame paired with objective vision metrics (clipping, safe-area, empty-check, palette).

Returns: {image_base64, metrics: {...}, warnings: [...], rubrics_resource}.

Gotcha: Default 320x240 is token-optimized; use focus_region [x, y, w, h] to inspect details.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `time` | `number` | No | - |
| `focus_region` | `any` | No | - |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |

---

### `review_sequence`

*Profiles: all, review*

Render a sequence of frames compiled into a single contact-sheet image with motion and strobe metrics.

Returns: {contact_sheet_base64, strobe_check, motion_stats, warnings}.

Gotcha: Reduces vision token usage 3-4x compared to multiple individual frame renders.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `start_time` | `number` | No | - |
| `end_time` | `number` | No | - |
| `frame_count` | `integer` | No | - |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |

---

### `review_compare`

*Profiles: all, review*

Compare two animation iterations/frames with side-by-side visual diff heatmap and SSIM score.

Returns: {comparison: {...}, ssim: float, pixel_change_ratio: float, heatmap_composite_base64}.

Gotcha: Quickly verify if an edit produced the intended visual change without rendering videos.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id_a` | `string` | No | - |
| `time_a` | `number` | No | - |
| `doc_id_b` | `string` | No | - |
| `time_b` | `number` | No | - |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |

---
