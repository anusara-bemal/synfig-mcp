# Synfig MCP Tool Reference

> Complete typed reference for all 104 Model Context Protocol (MCP) tools provided by the `synfig-mcp` server.
> Each tool includes typed input schemas, execution semantics, and LLM-targeted guidance.

> Generated from the live tool registry by `scripts/generate_tool_docs.py`.

## Table of Contents

- [Animation & Keyframes](#animation-keyframes) (10 tools)
- [Canvas & Scene](#canvas-scene) (10 tools)
- [Character Rigging](#character-rigging) (4 tools)
- [Core & Diagnostics](#core-diagnostics) (2 tools)
- [Document Management](#document-management) (8 tools)
- [Effect Recipes](#effect-recipes) (3 tools)
- [History & Undo](#history-undo) (3 tools)
- [Layer Manipulation](#layer-manipulation) (9 tools)
- [Licensed Assets](#licensed-assets) (4 tools)
- [Other](#other) (22 tools)
- [Parameters & ValueNodes](#parameters-valuenodes) (7 tools)
- [Render & Preview](#render-preview) (8 tools)
- [Schema & Introspection](#schema-introspection) (5 tools)
- [Selection](#selection) (2 tools)
- [Storyboards](#storyboards) (1 tools)
- [Style Presets](#style-presets) (3 tools)
- [Visual Review](#visual-review) (3 tools)

**Total: 104 tools.**

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

Apply declarative scene build spec.

Spec: {doc_id, layers: [{id, type, params}], groups}. Layer 'id' required. Image paths host-resolved or via SYNFIG_MCP_PATH_MAPPING.

Returns: Diff {action: 'scene.build', created: [...], modified: [...]}.

Gotcha: Defaults to active document; do not call doc_new/doc_open first.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

### `scene_export_spec`

*Profiles: all, core*

Export current scene state into a declarative SceneBuildSpec JSON.

Returns: Structured SceneBuildSpec dictionary compatible with scene_build.

Gotcha: Filter fields=['params', 'waypoints'] to reduce returned payload tokens.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `scope` | `string` | No | - |
| `fields` | `any` | No | - |

---

### `scene_summary`

*Profiles: all, anim, assets, core, fx, review, rig*

Get a token-bounded structural summary of canvas size, framerate, duration, and layer hierarchy.

Returns: Compact document metadata summary strictly bounded under budget_tokens.

Gotcha: Defaults to the currently selected document; call this first to confirm the target before building.

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

Change the resolution, frame rate, time range or background colour of a canvas.

Returns: Object with the updated canvas properties and a diff summary.

Gotcha: Setting end_time before start_time.

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

Build a whole animated shot in one call: background, rigged cut-out characters, props,

camera moves and audio. One undo step; everything is validated before the document changes.

spec: {width, height, fps, duration, background: {file|color, fit},

characters: [{id, manifest | parts: [{name, file, parent?, pivot?: {fx, fy}, attach?: {fx, fy}, z?}],

position: {x, y}, height, flip, z, actions: [{motion, start, end, move_to: {x, y}, speed}]}],

props: [{id, file, position, height, rotation, z, actions}],

camera: [{time, zoom, center: {x, y}}], audio: {file, delay}, save_path, preview}.

Positions are canvas pixels from the top-left (coords: "units" for Synfig units); a character

stands with its feet on 'position'. Motions: idle, walk, run, talk, breath, crouch,

shake (loop); wave, jump, nod, kick, block, dodge, fall, land, turn, react, stomp,

punch (once); rest, pose, move.

Returns: {doc_id, characters, props, warnings, saved_to, preview: {contact_sheet_base64, ...}}.

Gotcha: Parts named by body role get default joints; other parts need parent + attach.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

## Character Rigging

### `character_rig_from_parts`

*Profiles: all, rig*

Assemble a jointed cut-out character from part images (or primitives) in an open document.

spec: {doc_id, id, manifest | parts: [{name, file, parent?, pivot?: {fx, fy}, attach?: {fx, fy}, z?}],

position: {x, y}, height, flip, layout: "assemble" | "in_place", actions?}.

Every part gets a joint layer <id>_<part>_rot; turning a part carries its children.

Returns: Rig summary with root group, parts, roles and joint layer ids.

Gotcha: Use dry_run=true to preview the hierarchy; pivot/attach are fractions of the image.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

### `character_pose_apply`

*Profiles: all, rig*

Key a pose on a rigged character: a preset (idle, punch, jump, walk_contact, walk_passing)

or explicit joint angles, e.g. angles={"upper_arm_r": 120, "head": -10} (degrees from rest).

Returns: The joint layers that were keyed and the joints the character does not have.

Gotcha: Fails when the character has none of the addressed joints - nothing is keyed silently.

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

Animate a rigged character. Looping motions (run until end_time): idle, walk, run,

talk, breath, crouch, shake. One-shot motions: wave, jump, nod, kick, block, dodge,

fall, land, turn, react, stomp, punch. Special: rest, move.

move_to={x, y} (canvas pixels) travels there by end_time.

Returns: Keyframe times, waypoint count, animated layers and skipped joints.

Gotcha: The character must have been built by character_rig_from_parts or scene_auto_build.

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

### `character_model_sheet`

*Profiles: all, rig*

Auto-generate a labeled model/rig sheet (front, three-quarter, side) for one character.

descriptor: {id, archetype: humanoid|chibi, height, palette, facing, position, z}.

Returns: {success, sheet_doc_id, sheet_group, views, layers}.

Gotcha: the sheet is vector cut-out geometry, not a re-drawn turnaround.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `descriptor` | `object` | Yes | - |
| `style` | `string` | No | - |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |
| `dry_run` | `boolean` | No | - |

---

## Core & Diagnostics

### `synfig_help`

*Profiles: all, anim, assets, core, fx, review, rig*

Get detailed guidance on Synfig MCP topics (overview, profiles, declarative_build, animation, characters, review).

Returns: Markdown guide text and list of available guide topics.

Gotcha: Querying help avoids loading large documentation into the active context.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `topic` | `string` | No | - |

---

### `health_check`

*Profiles: all, anim, assets, core, fx, review, rig*

Check server readiness, active backend ('live' Synfig Studio vs 'headless' pure-Python SIF engine), and connection status.

Returns: JSON object with 'backend' ('live' or 'headless'), 'connected' (bool), 'studio_running' (bool), and 'details'.

Gotcha: In 'auto' mode a blank canvas usually means Studio is open without its MCP bridge. Check 'details.warning' and use the patched Studio build.

#### Parameters

*No parameters required.*

---

## Document Management

### `doc_list`

*Profiles: all, anim, assets, core, fx, review, rig*

List all currently open or loaded animation documents.

Returns: Array of document objects, each containing 'id', 'name', 'width', 'height', 'fps', and 'duration_frames'.

Gotcha: Passing a file path instead of obtaining a valid 'doc_id' from this list.

#### Parameters

*No parameters required.*

---

### `doc_info`

*Profiles: all, anim, assets, core, fx, review, rig*

Get metadata, resolution, framerate, and time bounds for a specific document.

Returns: Document details including 'width', 'height', 'fps', 'start_time', 'end_time', and 'duration_frames'.

Gotcha: Invoking without a valid doc_id from doc_list().

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `doc_new`

*Profiles: all, core*

Create a new blank Synfig animation document with specified resolution and framerate.

Returns: The created DocumentInfo object with generated 'id', 'name', dimensions, and fps.

Gotcha: ONLY call when the user explicitly asked for a new document. Otherwise reuse the currently open document (doc_list) and pass its doc_id.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |
| `fps` | `number` | No | - |

---

### `doc_open`

*Profiles: all, core*

Open an existing Synfig animation project (.sif, .sifz, or .sfg container).

Returns: DocumentInfo representing the loaded project.

Gotcha: ONLY call when the user explicitly asked to open this file. Never use it to 'start fresh'; implement in the currently open document instead.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file_path` | `string` | Yes | - |

---

### `doc_save`

*Profiles: all, core*

Save the document to disk in .sif (XML), .sifz (gzip), or .sfg (ZIP container) format.

Returns: Object containing 'file_path' of the saved file.

Gotcha: Omitting file_path when the document was newly created with doc_new() and has no default path.

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

Update canvas resolution, frame rate, time bounds, or name.

Returns: Updated DocumentInfo object.

Gotcha: Setting end_time less than or equal to start_time.

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

Undo the previous action in Studio or Headless mode. Exactly 1 MCP mutating tool call = 1 undo step.

Returns: Object with 'success': bool.

Gotcha: Calling undo when undo stack is empty (returns success: false).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `history_redo`

*Profiles: all, anim, assets, core, fx, review, rig*

Redo the previously undone action.

Returns: Object with 'success': bool.

Gotcha: Calling redo after a new mutating action was performed (new actions clear redo stack).

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

Add a new visual layer (e.g. 'circle', 'rectangle', 'star', 'solid_color', 'text', 'PasteCanvas') to the canvas.

Returns: Object with 'layer_id', 'layer_type', 'depth', and structured 'diff' summary.

Gotcha: Using invalid layer type names. Query schema_list_layers() first to see all valid types.

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

### `permission_list`

*Profiles: all, anim, assets, core, fx, review, rig*

List the directory roots the user has granted the server read/write access to.

Returns: Object with 'roots' (each: path, read, write, source) and 'default' (the fallback project dir).

Gotcha: A path must be inside one of these roots for any file tool to accept it; grant more with permission_grant.

#### Parameters

*No parameters required.*

---

### `permission_grant`

*Profiles: all, anim, assets, core, fx, review, rig*

Grant the server access to a directory root for this session (the user authorizes a folder).

Args:

path: Absolute or relative path to a directory (or a file inside it) to authorize.

read: Allow reading from the root (default True).

write: Allow creating/overwriting files under the root (default True).

Returns: The resulting grant (path, read, write, source).

Gotcha: The path must exist. Granting a drive root, system folder or the user home root directly is rejected as overly broad.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `path` | `string` | Yes | - |
| `read` | `boolean` | No | - |
| `write` | `boolean` | No | - |

---

### `permission_revoke`

*Profiles: all, anim, assets, core, fx, review, rig*

Revoke a previously granted directory root.

Args:

path: The directory root to remove from the grant list.

Returns: Object with 'revoked' (bool) and the path.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `path` | `string` | Yes | - |

---

### `rig_bone_add`

*Profiles: all, rig*

Add a bone to a skeleton layer (Synfig's cut-out rigging primitive).

Returns: Object describing the created bone and a diff summary.

Gotcha: Bone authoring needs Synfig Studio - the headless engine reports that it cannot create bones.

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

### `rig_sheet_from_image`

*Profiles: all, assets, rig*

Ingest an uploaded image (MCP ImageContent base64, or a local path) and slice it into rig parts.

Give exactly one of image_base64 / file_path. The image is hardened (magic-byte check, 16MP

cap, EXIF stripped) and written into an authorized directory, then sliced like rig_sheet_slice.

Args:

image_base64: The data field of an ImageContent block (raw base64 or a data: URL).

file_path: A local image the server may already read (alternative to image_base64).

names: Optional {part number -> name} mapping from the numbered preview, e.g. {"1": "head"}.

output_dir: Directory for the PNGs and manifest (defaults to the first granted root).

filename: Base name for the written sheet when image_base64 is used.

mime_type: Declared mime type of the uploaded block (informational).

reconstruct: Best-effort occlusion fill of enclosed gaps in each part.

Returns: {sheet, parts: [{index, name, file, bbox, role, parent, pivot, z, transparency,

confidence}], manifest, rig_compatibility, reconstruction, requires_approval, preview_base64}.

Gotcha: Look at preview_base64 first, then call again with names to label the parts by body role.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `image_base64` | `any` | No | - |
| `file_path` | `any` | No | - |
| `names` | `any` | No | - |
| `output_dir` | `any` | No | - |
| `filename` | `string` | No | - |
| `mime_type` | `any` | No | - |
| `min_area` | `any` | No | - |
| `merge_gap` | `integer` | No | - |
| `bg_tolerance` | `integer` | No | - |
| `reconstruct` | `boolean` | No | - |
| `preview` | `boolean` | No | - |

---

### `rig_sheet_slice`

*Profiles: all, assets, rig*

Cut a character rig sheet (one image, many body parts) into one transparent PNG per part.

Call once without names and look at preview_base64 (numbered boxes), then call again with

names={"1": "head", "2": "torso", "3": "upper_arm_l", ...} to export only the real parts.

Returns: {parts: [{index, name, file, bbox}], manifest, output_dir, preview_base64}.

Gotcha: Needs a transparent or uniform background. Name parts by body role (head, torso,

upper_arm_l, forearm_l, hand_l, upper_leg_r, lower_leg_r, foot_r) so rigs assemble themselves.

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

### `produce_anime_project`

*Profiles: all*

Build a whole anime-style project from one brief: storyboard, rigged characters,

assets, assembled scene, style stack, render and review.

brief: {title, style, width, height, fps, duration, seed, shots[], characters[],

assets[], background, camera[], render{}, output_dir, save_path}. Call

synfig_help('production') for the full brief shape, styles and motion names.

Returns: {success, doc_id, total_shots, duration_seconds, stages[], artifacts, warnings}.

Gotcha: rendering needs the Synfig CLI on PATH; without it the document is still saved

and the render/review stages report "skipped". A run writes pipeline_state.json into the

output directory; re-running the same brief (resume=True) reopens the saved document and

continues from where it stopped instead of rebuilding. Pass resume=False for a clean run.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `brief` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |
| `stages` | `any` | No | - |
| `resume_from` | `any` | No | - |
| `resume` | `boolean` | No | - |

---

### `production_plan`

*Profiles: all*

Dry-run the production pipeline: report the stages and layer counts without building.

brief: same shape as produce_anime_project (see synfig_help('production')).

Returns: the ProductionReport for the dry run; no document is created.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `brief` | `object` | Yes | - |

---

### `procedural_asset_list`

*Profiles: all, assets*

List the built-in procedural asset generators (offline, IP-safe).

Returns: {background: [...], prop: [...], texture: [...]} to pass as

asset "procedural": {generator: <name>}.

#### Parameters

*No parameters required.*

---

### `procedural_asset_generate`

*Profiles: all, assets*

Generate one procedural vector asset and add it to a document.

kind: background | prop | texture; generator: see procedural_asset_list.

position/height are canvas pixels (props only). Returns: {success, created, dry_run}.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `kind` | `string` | No | - |
| `generator` | `string` | No | - |
| `seed` | `integer` | No | - |
| `position` | `any` | No | - |
| `height` | `any` | No | - |
| `style` | `any` | No | - |
| `dry_run` | `boolean` | No | - |

---

### `sprite_slice`

*Profiles: all, assets, rig*

Slice a sprite sheet or layered raster into named, rig-ready transparent part PNGs.

strategy: grid (rows x cols), alpha (connected components) or trim (tight alpha boxes);

pass rectangles [{name, x, y, width, height}] for exact control.

Returns: {success, detected_parts, parts: [{name, file, bbox}], output_dir}.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `source` | `string` | Yes | - |
| `output_dir` | `string` | Yes | - |
| `strategy` | `string` | No | - |
| `rows` | `integer` | No | - |
| `cols` | `integer` | No | - |
| `rectangles` | `any` | No | - |
| `bg_tolerance` | `integer` | No | - |
| `padding` | `integer` | No | - |
| `dry_run` | `boolean` | No | - |

---

### `capability_search`

*Profiles: all, anim, assets, core, fx, review, rig*

Search the capability registry (server tools + bridge methods) by keyword.

Args:

query: Free-text query, e.g. 'render', 'bone', 'layer add'.

domain: Optional domain filter, e.g. 'rendering', 'animation', 'layer_operations'.

limit: Maximum results (default 20).

Returns: {count, capabilities: [{id, domain, summary, required, permission}]}.

Gotcha: Prefer this over reading all tool schemas; then call capability_inspect for the one you need.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `query` | `string` | Yes | - |
| `domain` | `any` | No | - |
| `limit` | `integer` | No | - |

---

### `capability_list`

*Profiles: all*

List every capability, optionally filtered to one domain, as compact summaries.

Returns: {count, domains: [...], capabilities: [{id, domain, summary, required, permission}]}.

Gotcha: The full surface is large; use capability_search when you already know roughly what you want.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `domain` | `any` | No | - |

---

### `capability_inspect`

*Profiles: all, anim, assets, core, fx, review, rig*

Return the full descriptor (params, schemas, permission, error codes, undo, verification) for one capability.

Args:

capability_id: The capability id, e.g. 'render_frame' or a bridge method like 'rig.bone_add'.

Returns: The complete Capability object, or {error} if unknown.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `capability_id` | `string` | Yes | - |

---

### `capability_validate`

*Profiles: all*

Validate arguments against a capability's input schema without executing it.

Args:

capability_id: The capability id to validate against.

args: The arguments you intend to pass.

Returns: {valid, missing, unexpected, error?}.

Gotcha: Cheap pre-flight check to avoid a failed capability_execute round-trip.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `capability_id` | `string` | Yes | - |
| `args` | `object` | Yes | - |

---

### `capability_execute`

*Profiles: all, anim, assets, core, fx, review, rig*

Invoke any registered capability by id with keyword arguments (the compact alternative to per-tool calls).

Args:

capability_id: The capability id to run, e.g. 'doc_new'.

args: Keyword arguments for the capability (see capability_inspect).

Returns: {capability, result} on success.

Gotcha: Only server tools (kind 'tool') are executable; bridge methods are introspected, not dispatched here.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `capability_id` | `string` | Yes | - |
| `args` | `any` | No | - |

---

### `capability_batch_execute`

*Profiles: all*

Run several capabilities in sequence, stopping early on the first failure unless disabled.

Args:

operations: List of {capability, args} objects.

stop_on_error: Stop at the first error (default True).

Returns: {completed, failed, results: [{capability, ok, result|error}]}.

Gotcha: Steps share no implicit state; thread ids through explicitly.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `operations` | `array` | Yes | - |
| `stop_on_error` | `boolean` | No | - |

---

### `capability_discover`

*Profiles: all, anim, assets, core, fx, review, rig*

Report what the server can currently do: live backend, domains, counts, and ready-made workflows.

Returns: {backend, domains, tool_count, protocol_count, workflows: [{id, name, description}]}.

Gotcha: Call this first in a fresh session to see the real (honest) surface before planning.

#### Parameters

*No parameters required.*

---

### `capability_load_profile`

*Profiles: all*

Register additional tools for a profile at runtime, on top of those already active.

Args:

profile: One of core, anim, fx, rig, assets, review, all.

Returns: {profile, added: [...], already_active: [...], active_count}.

Gotcha: Loading 'all' exposes the full surface and raises the tools/list token cost.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `profile` | `string` | Yes | - |

---

### `capability_unload_profile`

*Profiles: all*

Unregister tools that belong to a profile, shrinking the active surface.

Args:

profile: One of core, anim, fx, rig, assets, review, all.

Returns: {profile, removed: [...], active_count}.

Gotcha: Never removes the capability_* meta-tools themselves.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `profile` | `string` | Yes | - |

---

### `capability_workflow_execute`

*Profiles: all*

Run a built-in multi-step workflow by id (see capability_discover for the list).

Args:

workflow_id: The workflow id, e.g. 'new_document' or 'build_scene'.

run_id: Optional run id for later resume (defaults to the workflow id).

Returns: {status, run_id, context, results} or a failure with the failing step.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `workflow_id` | `string` | Yes | - |
| `run_id` | `any` | No | - |

---

### `capability_workflow_resume`

*Profiles: all*

Resume a previously failed workflow run from its last saved step.

Args:

run_id: The run id returned by capability_workflow_execute.

Returns: {status, run_id, context, results}.

Gotcha: Requires that the earlier run persisted state (it does on any failure).

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `run_id` | `string` | Yes | - |

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

## Render & Preview

### `render_frame`

*Profiles: all, core, review*

Render a single frame of the animation to an image file (PNG, JPEG, BMP, GIF, PPM).

Returns: Object with 'success': bool, 'output_path', 'time', and image dimensions.

Gotcha: Sequence encoders such as 'ffmpeg' need render_sequence, not render_frame.

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

Render an image sequence across an animation time range using the rendering pipeline.

Returns: List of generated output frame file paths.

Gotcha: Passing a file path instead of an output directory.

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

Start an asynchronous animation render job and immediately return a job_id.

Returns: Dictionary with 'job_id', 'status': 'running', and 'output_dir'.

Gotcha: Verify document ID before invoking.

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

Query the execution status and progress of an asynchronous render job.

Returns: Dictionary with 'job_id', 'status' ('running', 'completed', 'cancelled', 'failed'),

Gotcha: Verify document ID before invoking.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `job_id` | `string` | Yes | - |

---

### `render_result`

*Profiles: all, review*

Retrieve final output frames for a completed render job.

Returns: Dictionary with 'job_id', 'status': 'completed', and 'frames': list of file paths.

Gotcha: Verify document ID before invoking.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `job_id` | `string` | Yes | - |

---

### `render_cancel`

*Profiles: all, review*

Cancel an active in-flight render job by its job_id.

Returns: Dictionary with 'cancelled': True, 'job_id': str, and status message.

Gotcha: Verify document ID before invoking.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `job_id` | `string` | Yes | - |

---

### `render_video`

*Profiles: all, review*

Render an animation time range and compile directly to a video file (.mp4 or .gif).

Returns: Object containing 'success': bool and 'output_path'.

Gotcha: Targeting an invalid extension (use .mp4 or .gif).

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

Render selected keyframe timestamps into a visual contact sheet / storyboard grid image.

Returns: Object containing 'success': bool and 'output_path'.

Gotcha: Setting cols or rows to 0.

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
