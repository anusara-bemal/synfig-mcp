# Synfig MCP Tool Reference

> Complete typed reference for all 74 Model Context Protocol (MCP) tools provided by the `synfig-mcp` server.
> Each tool includes typed input schemas, execution semantics, and LLM-targeted guidance.

> Generated from the live tool registry by `scripts/generate_tool_docs.py`.

## Table of Contents

- [Animation & Keyframes](#animation-keyframes) (9 tools)
- [Canvas & Scene](#canvas-scene) (5 tools)
- [Character Rigging](#character-rigging) (3 tools)
- [Core & Diagnostics](#core-diagnostics) (2 tools)
- [Document Management](#document-management) (8 tools)
- [Effect Recipes](#effect-recipes) (3 tools)
- [History & Undo](#history-undo) (3 tools)
- [Layer Manipulation](#layer-manipulation) (9 tools)
- [Licensed Assets](#licensed-assets) (4 tools)
- [Parameters & ValueNodes](#parameters-valuenodes) (6 tools)
- [Render & Preview](#render-preview) (8 tools)
- [Schema & Introspection](#schema-introspection) (5 tools)
- [Selection](#selection) (2 tools)
- [Storyboards](#storyboards) (1 tools)
- [Style Presets](#style-presets) (3 tools)
- [Visual Review](#visual-review) (3 tools)

**Total: 74 tools.**

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

Apply a declarative scene build spec (layers, params, waypoints, groups) atomically as one undo step.

Returns: Compact diff {action: 'scene.build', created: [...], modified: [...]}.

Gotcha: spec.doc_id defaults to the currently selected document; never call doc_new/doc_open first - implement in the open document.

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

## Character Rigging

### `character_rig_from_parts`

*Profiles: all, rig*

Assemble a hierarchical 2D cut-out character puppet from geometric or imported parts.

Returns: Rig summary with character ID, root group, and parts count.

Gotcha: Use dry_run=true to preview hierarchy before assembling.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `spec` | `object` | Yes | - |
| `dry_run` | `boolean` | No | - |

---

### `character_pose_apply`

*Profiles: all, rig*

Apply a named pose preset (idle, punch, jump, walk_contact, walk_passing) to character parts.

Returns: Status with applied bone rotations and active facial slots.

Gotcha: Verify character_id matches the rigged puppet root prefix.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `character_id` | `string` | No | - |
| `pose_name` | `string` | No | - |
| `time` | `number` | No | - |

---

### `character_motion_apply`

*Profiles: all, rig*

Apply a complete motion cycle preset (walk, punch, idle) across keyframe waypoints.

Returns: Applied keyframe sequence, cycle duration, and target character ID.

Gotcha: Automatically sets multi-frame easing waypoints along the timeline.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `character_id` | `string` | No | - |
| `motion_name` | `string` | No | - |
| `start_time` | `number` | No | - |

---

## Core & Diagnostics

### `synfig_help`

*Profiles: all, anim, assets, core, fx, review, rig*

Get detailed guidance on Synfig MCP topics (overview, profiles, declarative_build, animation, review).

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

Import an external asset file (e.g. .png, .jpg, .svg) into the canvas as an image layer.

Returns: Layer dictionary for the newly imported image layer.

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

Render a single frame of the animation to an image file (PNG, JPEG, etc.).

Returns: Object with 'success': bool, 'output_path', 'time', and image dimensions.

Gotcha: Targeting an invalid or unwritable directory path.

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
