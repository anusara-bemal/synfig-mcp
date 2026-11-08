# Synfig MCP Tool Reference

> Complete typed reference for all 47 Model Context Protocol (MCP) tools provided by the `synfig-mcp` server.
> Each tool includes typed input schemas, execution semantics, and LLM-targeted guidance.

## Table of Contents

- [Animation & Keyframes](#animation-keyframes) (9 tools)
- [Canvas & Hierarchy](#canvas-hierarchy) (2 tools)
- [Core & Diagnostic](#core-diagnostic) (1 tools)
- [Document Management](#document-management) (8 tools)
- [History & Undo](#history-undo) (3 tools)
- [Layer Manipulation](#layer-manipulation) (8 tools)
- [Parameters & ValueNodes](#parameters-valuenodes) (5 tools)
- [Render & Preview](#render-preview) (4 tools)
- [Schema & Introspection](#schema-introspection) (5 tools)
- [Selection](#selection) (2 tools)

## Animation & Keyframes

### `anim_time_get`

Get the current timeline cursor / playhead position in seconds.

When to use:

Use to check the active frame/time before inserting keyframes or editing animated properties.

Returns:

Object with 'time': float in seconds.

Common mistakes:

Confusing frame numbers with seconds. Synfig time is in seconds (frame = seconds * fps).

Example:

anim_time_get(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `anim_time_set`

Seek the timeline cursor / playhead to a specific time in seconds.

When to use:

Use before setting keyframed values at different points in time.

Returns:

Object with 'time': float in seconds.

Common mistakes:

Passing negative time.

Example:

anim_time_set(doc_id="doc_0", time=2.5)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `time` | `number` | Yes | - |

---

### `anim_keyframe_list`

List all keyframes defined on the timeline.

When to use:

Use to inspect the timeline structure and existing keyframe positions.

Returns:

Array of keyframe objects, each with 'time', 'time_string', 'description', and 'active'.

Common mistakes:

Assuming keyframes are automatically created without calling anim_keyframe_add.

Example:

anim_keyframe_list(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_path` | `string` | No | - |

---

### `anim_keyframe_add`

Add a keyframe at the specified time to lock parameter values into an animation pose.

When to use:

Use when creating keyframe poses across the animation timeline.

Returns:

Object with 'time', 'description', 'active', and 'diff'.

Common mistakes:

Adding duplicate keyframes at the exact same time timestamp.

Example:

anim_keyframe_add(doc_id="doc_0", time=1.0, description="Jump Peak")

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

Delete a keyframe at the specified time.

When to use:

Use to remove unwanted keyframe poses.

Returns:

Object with 'removed': bool.

Common mistakes:

Specifying a time where no keyframe exists.

Example:

anim_keyframe_remove(doc_id="doc_0", time=1.0)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `time` | `number` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `anim_waypoint_set`

Insert or update a waypoint for a layer parameter at a specific timeline timestamp.

When to use:

Use to animate a parameter smoothly across time (e.g. moving an origin, fading opacity, morphing color).

Returns:

Dictionary containing 'waypoint' details and 'interpolated_value'.

Common mistakes:

Passing invalid interpolation strings (valid: 'linear', 'constant', 'halt', 'clamped', 'tcb').

Example:

anim_waypoint_set(doc_id="doc_0", layer_id="Circle001", param_name="origin", time=2.0, value=[3.0, 0.0], interpolation_in="linear", interpolation_out="linear")

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

Remove a waypoint from a layer parameter at a given time.

When to use:

Use to delete an animation key/waypoint without deleting the parameter itself.

Returns:

Object with 'removed': bool.

Common mistakes:

Providing a time that does not match an existing waypoint.

Example:

anim_waypoint_remove(doc_id="doc_0", layer_id="Circle001", param_name="origin", time=2.0)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `time` | `number` | Yes | - |

---

### `anim_animate_param`

Define a full parameter animation trajectory using a batch of waypoints in ONE single undo step.

When to use:

Use whenever setting multiple animation keys for a property to ensure the user can undo the entire motion path in a single action.

Returns:

Object containing 'count': number of waypoints applied.

Common mistakes:

Omitting 'time' or 'value' from waypoint dictionary items.

Example:

anim_animate_param(doc_id="doc_0", layer_id="Circle001", param_name="origin", waypoints=[{"time": 0.0, "value": [0.0, 0.0]}, {"time": 2.0, "value": [3.0, 0.0]}])

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `waypoints` | `array` | Yes | - |

---

### `anim_interpolation_set`

Set default canvas waypoint interpolation or change interpolation on existing waypoints.

When to use:

Use to configure interpolation style ('linear', 'constant', 'halt', 'clamped', 'tcb') globally or on a parameter.

Returns:

Object with 'success': bool and 'interpolation'.

Common mistakes:

Using unsupported interpolation types.

Example:

anim_interpolation_set(doc_id="doc_0", interpolation="linear")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `interpolation` | `string` | Yes | - |
| `layer_id` | `any` | No | - |
| `param_name` | `any` | No | - |

---

## Canvas & Hierarchy

### `canvas_list`

List all canvas paths in the document (root canvas and nested group/subcanvases).

When to use:

Use before adding layers into specific groups or when working with exported canvases.

Returns:

Object containing 'canvases': array of path strings (e.g. ['/', '/CharacterGroup']).

Common mistakes:

Assuming only the root canvas exists when layers are inside nested groups.

Example:

canvas_list(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `scene_tree`

Get the full visual hierarchy of layers in depth order (topmost layer at index 0).

When to use:

Use to inspect layer IDs, descriptions, types, active status, depth, and parameter values.

Returns:

Hierarchical layer tree with child layers for PasteCanvas groups.

Common mistakes:

Looking for a layer ID without checking nested 'children' inside group layers.

Example:

scene_tree(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `canvas_path` | `string` | No | - |

---

## Core & Diagnostic

### `health_check`

Check server readiness, active backend ('live' Synfig Studio vs 'headless' pure-Python SIF engine), and connection status.

When to use:

Call this first at session start or after connection issues to verify whether Synfig Studio is connected live or if commands will run headless.

Returns:

JSON object with 'backend' ('live' or 'headless'), 'connected' (bool), 'studio_running' (bool), and 'details'.

Common mistakes:

Assuming Studio is running without checking 'connected' or 'studio_running'.

Example:

health_check()

#### Parameters

*No parameters required.*

---

## Document Management

### `doc_list`

List all currently open or loaded animation documents.

When to use:

Use to discover available doc_ids before querying layers or modifying parameters.

Returns:

Array of document objects, each containing 'id', 'name', 'width', 'height', 'fps', and 'duration_frames'.

Common mistakes:

Passing a file path instead of obtaining a valid 'doc_id' from this list.

Example:

doc_list()

#### Parameters

*No parameters required.*

---

### `doc_info`

Get metadata, resolution, framerate, and time bounds for a specific document.

When to use:

Use before rendering or keyframing to inspect canvas dimensions and timeline bounds.

Returns:

Document details including 'width', 'height', 'fps', 'start_time', 'end_time', and 'duration_frames'.

Common mistakes:

Invoking without a valid doc_id from doc_list().

Example:

doc_info(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `doc_new`

Create a new blank Synfig animation document with specified resolution and framerate.

When to use:

Use when starting a fresh animation project from scratch.

Returns:

The created DocumentInfo object with generated 'id', 'name', dimensions, and fps.

Common mistakes:

Supplying non-positive dimensions or frame rate.

Example:

doc_new(width=1920, height=1080, fps=24.0)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `width` | `integer` | No | - |
| `height` | `integer` | No | - |
| `fps` | `number` | No | - |

---

### `doc_open`

Open an existing Synfig animation project (.sif, .sifz, or .sfg container).

When to use:

Use to load an existing project file from disk for editing or rendering.

Returns:

DocumentInfo representing the loaded project.

Common mistakes:

Providing a non-existent or relative file path outside the allowed workspace.

Example:

doc_open(file_path="C:/Projects/Animation/intro.sifz")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file_path` | `string` | Yes | - |

---

### `doc_save`

Save the document to disk in .sif (XML), .sifz (gzip), or .sfg (ZIP container) format.

When to use:

Use after modifying layers or keyframes to persist changes to disk.

Returns:

Object containing 'file_path' of the saved file.

Common mistakes:

Omitting file_path when the document was newly created with doc_new() and has no default path.

Example:

doc_save(doc_id="doc_0", file_path="C:/Projects/Animation/output.sifz")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `file_path` | `any` | No | - |

---

### `doc_close`

Close an open document and unload it from memory.

When to use:

Use when finished working on a document to free memory.

Returns:

Object containing 'closed': true.

Common mistakes:

Closing without saving changes first with doc_save, unless force=True is passed.

Example:

doc_close(doc_id="doc_0", force=False)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `force` | `boolean` | No | - |

---

### `doc_set_properties`

Update canvas resolution, frame rate, time bounds, or name.

When to use:

Use to resize the canvas, change FPS, or extend animation duration.

Returns:

Updated DocumentInfo object.

Common mistakes:

Setting end_time less than or equal to start_time.

Example:

doc_set_properties(doc_id="doc_0", width=1280, height=720, fps=30.0, end_time=10.0)

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

Set canvas animation playback timeline start time, end time, and framerate.

When to use:

Use to lengthen or shorten the animation timeline or adjust frames per second.

Returns:

Updated DocumentInfo containing 'start_time', 'end_time', and 'fps'.

Common mistakes:

Setting start_time greater than or equal to end_time.

Example:

doc_set_time_range(doc_id="doc_0", start_time=0.0, end_time=10.0, fps=30.0)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |
| `start_time` | `any` | No | - |
| `end_time` | `any` | No | - |
| `fps` | `any` | No | - |

---

## History & Undo

### `history_undo`

Undo the previous action in Studio or Headless mode. Exactly 1 MCP mutating tool call = 1 undo step.

When to use:

Use to revert any unwanted edit, layer addition, or parameter change.

Returns:

Object with 'success': bool.

Common mistakes:

Calling undo when undo stack is empty (returns success: false).

Example:

history_undo(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `history_redo`

Redo the previously undone action.

When to use:

Use to re-apply an action that was undone with history_undo.

Returns:

Object with 'success': bool.

Common mistakes:

Calling redo after a new mutating action was performed (new actions clear redo stack).

Example:

history_redo(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `history_list`

Query current undo and redo stack depths.

When to use:

Use to check how many actions can be undone or redone.

Returns:

Object with 'undo_count' and 'redo_count'.

Common mistakes:

Assuming infinite redo after performing a new mutation.

Example:

history_list(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

## Layer Manipulation

### `layer_add`

Add a new visual layer (e.g. 'circle', 'rectangle', 'star', 'solid_color', 'text', 'PasteCanvas') to the canvas.

When to use:

Use to create visual shapes, backgrounds, text elements, or groups in the scene.

Returns:

Object with 'layer_id', 'layer_type', 'depth', and structured 'diff' summary.

Common mistakes:

Using invalid layer type names. Query schema_list_layers() first to see all valid types.

Example:

layer_add(doc_id="doc_0", layer_type="circle", params={"radius": {"type": "real", "value": 2.0}, "color": {"type": "color", "r": 0.2, "g": 0.7, "b": 1.0, "a": 1.0}})

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

Delete a layer from the composition.

When to use:

Use to remove unwanted shapes or groups. This action is atomic and undoable with history_undo.

Returns:

Object with 'removed': bool and 'diff' summary.

Common mistakes:

Passing a layer index instead of the layer description/id.

Example:

layer_remove(doc_id="doc_0", layer_id="Circle001")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_duplicate`

Duplicate an existing layer, creating an identical copy placed directly above the original.

When to use:

Use to duplicate complex shapes or groups without re-specifying all their parameters.

Returns:

Details of the newly created duplicate layer.

Common mistakes:

Targeting a non-existent layer_id.

Example:

layer_duplicate(doc_id="doc_0", layer_id="Star001")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_reorder`

Move a layer to a specific visual depth (depth 0 is topmost, in front of all other layers).

When to use:

Use to adjust stacking order of layers so shapes render in front of or behind others.

Returns:

Object with 'reordered': bool and new 'depth'.

Common mistakes:

Assuming depth 0 is bottom (in Synfig, depth 0 is top / closest to camera).

Example:

layer_reorder(doc_id="doc_0", layer_id="BackgroundSolid", new_depth=10)

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `new_depth` | `integer` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_raise`

Raise a layer by 1 position (closer to camera, depth - 1).

When to use:

Use for quick relative reordering of adjacent layers.

Returns:

Object with 'raised': bool.

Common mistakes:

Calling on a layer that is already at depth 0 (topmost).

Example:

layer_raise(doc_id="doc_0", layer_id="Circle001")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_lower`

Lower a layer by 1 position (further from camera, depth + 1).

When to use:

Use for quick relative reordering of adjacent layers.

Returns:

Object with 'lowered': bool.

Common mistakes:

Calling on a layer that is already bottom-most.

Example:

layer_lower(doc_id="doc_0", layer_id="Circle001")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `layer_group`

Group multiple layers into a PasteCanvas composite layer.

When to use:

Use to encapsulate related shapes (e.g. limbs, characters, complex icons) so they can be transformed together.

Returns:

Details of the created group layer and list of grouped layers.

Common mistakes:

Passing empty layer_ids list.

Example:

layer_group(doc_id="doc_0", layer_ids=["EyeLeft", "EyeRight"], group_name="EyesGroup")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_ids` | `array` | Yes | - |
| `group_name` | `string` | No | - |
| `canvas_path` | `string` | No | - |

---

### `layer_ungroup`

Ungroup a PasteCanvas layer, releasing its children into the parent canvas.

When to use:

Use to dissolve a group container and extract its contained layers.

Returns:

Object with 'ungrouped_layers': list of released layer IDs.

Common mistakes:

Calling ungroup on a non-group layer (e.g. a circle).

Example:

layer_ungroup(doc_id="doc_0", layer_id="EyesGroup")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

## Parameters & ValueNodes

### `param_get`

Read the typed value of a specific parameter on a layer.

When to use:

Use to inspect current values (e.g. radius, color, origin, opacity) before animating or modifying them.

Returns:

Tagged union SynfigValue object (e.g. {'type': 'real', 'value': 2.5} or {'type': 'color', 'r': 1.0, ...}).

Common mistakes:

Misspelling parameter names (e.g. 'pos' vs 'origin'). Use schema_get_layer() to check parameter names.

Example:

param_get(doc_id="doc_0", layer_id="Circle001", param_name="radius")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `canvas_path` | `string` | No | - |

---

### `param_set`

Set or update the value of a parameter on a layer.

When to use:

Use to change shape properties (e.g. color, size, radius, position, opacity).

Returns:

Object showing 'before' and 'after' values and diff summary.

Common mistakes:

Passing untagged raw numbers for vector types instead of {'type': 'vector', 'x': 0.0, 'y': 0.0}.

Example:

param_set(doc_id="doc_0", layer_id="Circle001", param_name="radius", value={"type": "real", "value": 3.5})

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

Convert a layer parameter into a linkable ValueNode (e.g. 'composite', 'scale', 'add', 'sine', 'linear', 'timeloop').

When to use:

Use when a parameter needs to be driven by a math expression, separated into sub-components, or looped over time.

Returns:

Object containing 'layer_id', 'param_name', and converted ValueNode 'type'.

Common mistakes:

Converting to an incompatible type (e.g. converting a Real number to 'composite').

Example:

param_convert(doc_id="doc_0", layer_id="Circle001", param_name="origin", type="composite")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `type` | `string` | Yes | - |

---

### `param_export`

Export a parameter's ValueNode to the canvas value node library for sharing across layers.

When to use:

Use to publish a value (like a shared color or origin) so multiple layers can link to it.

Returns:

Object containing exported 'name' and diff summary.

Common mistakes:

Exporting under a name that already exists in the document library.

Example:

param_export(doc_id="doc_0", layer_id="Circle001", param_name="radius", name="SharedRadius")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_id` | `string` | Yes | - |
| `param_name` | `string` | Yes | - |
| `name` | `string` | Yes | - |

---

### `param_unexport`

Unexport a previously exported ValueNode from the canvas library.

When to use:

Use when a shared ValueNode is no longer needed in the project library.

Returns:

Object confirming unexported 'name'.

Common mistakes:

Attempting to unexport a node that is still referenced by multiple active parameters.

Example:

param_unexport(doc_id="doc_0", name="SharedRadius")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `name` | `string` | Yes | - |

---

## Render & Preview

### `render_frame`

Render a single frame of the animation to an image file (PNG, JPEG, etc.).

When to use:

Use to preview the visual output of the scene or inspect rendering results.

Returns:

Object with 'success': bool, 'output_path', 'time', and image dimensions.

Common mistakes:

Targeting an invalid or unwritable directory path.

Example:

render_frame(doc_id="doc_0", output_path="C:/Temp/preview.png", time=1.5, width=640, height=360)

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

Render an image sequence across an animation time range using the rendering pipeline.

When to use:

Use to produce a sequence of frame images for review or video compilation.

Returns:

List of generated output frame file paths.

Common mistakes:

Passing a file path instead of an output directory.

Example:

render_sequence(doc_id="doc_0", output_dir="C:/Temp/frames", start_time=0.0, end_time=2.0, fps=24.0)

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

### `render_video`

Render an animation time range and compile directly to a video file (.mp4 or .gif).

When to use:

Use to produce a playable video or animated GIF preview of the animation.

Returns:

Object containing 'success': bool and 'output_path'.

Common mistakes:

Targeting an invalid extension (use .mp4 or .gif).

Example:

render_video(doc_id="doc_0", output_path="C:/Temp/preview.mp4", start_time=0.0, end_time=2.0, fps=24.0)

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

Render selected keyframe timestamps into a visual contact sheet / storyboard grid image.

When to use:

Use for rapid visual inspection of an animation's key poses on a single overview image.

Returns:

Object containing 'success': bool and 'output_path'.

Common mistakes:

Setting cols or rows to 0.

Example:

render_contact_sheet(doc_id="doc_0", output_path="C:/Temp/storyboard.png", cols=4, rows=2)

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

List all layer types supported by Synfig (e.g. 'circle', 'rectangle', 'star', 'text', 'blur', 'outline').

When to use:

Use to verify which layer types are available before invoking layer_add.

Returns:

Alphabetical list of supported layer type strings.

Common mistakes:

Guessing layer names without consulting this list.

Example:

schema_list_layers()

#### Parameters

*No parameters required.*

---

### `schema_get_layer`

Get parameter schemas, default values, and hints for a specific layer type.

When to use:

Use before adding or setting parameters on a layer to inspect expected parameter names and types.

Returns:

LayerTypeInfo object containing 'name', 'category', 'description', and 'params' dictionary.

Common mistakes:

Looking for a parameter that belongs to a different layer type.

Example:

schema_get_layer(layer_type="star")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `layer_type` | `string` | Yes | - |

---

### `schema_list_valuenodes`

List supported valuenode link converter types (e.g. 'composite', 'add', 'sine', 'random').

When to use:

Use when building procedural or linked value expressions.

Returns:

List of valuenode type names.

Common mistakes:

Confusing valuenodes with layer parameters.

Example:

schema_list_valuenodes()

#### Parameters

*No parameters required.*

---

### `schema_list_targets`

List supported render output targets (e.g. 'png', 'jpeg', 'bmp', 'gif', 'ffmpeg').

When to use:

Use to determine valid formats for render_frame and render_sequence.

Returns:

List of target format strings.

Common mistakes:

Passing unsupported extensions (e.g. 'webp').

Example:

schema_list_targets()

#### Parameters

*No parameters required.*

---

### `schema_list_renderers`

List available rendering engines (e.g. 'software', 'software-draft', 'safe').

When to use:

Use to select rendering quality or engine mode.

Returns:

List of renderer names.

Common mistakes:

Assuming GPU renderer is present when Synfig is using Cobra software renderer.

Example:

schema_list_renderers()

#### Parameters

*No parameters required.*

---

## Selection

### `selection_get`

Get the list of currently selected layer IDs in Studio.

When to use:

Use in live mode to coordinate with the user's manual selections in the GUI.

Returns:

Object with 'selected_layers': array of layer IDs.

Common mistakes:

Relying on selection in headless mode (headless selection is virtual).

Example:

selection_get(doc_id="doc_0")

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | No | - |

---

### `selection_set`

Set the active layer selection in Studio.

When to use:

Use to highlight specific layers in the Studio GUI for the user.

Returns:

Object with 'selected_layers': array of newly selected layer IDs.

Common mistakes:

Passing non-existent layer IDs.

Example:

selection_set(doc_id="doc_0", layer_ids=["Circle001", "Rect001"])

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `doc_id` | `string` | Yes | - |
| `layer_ids` | `array` | Yes | - |

---
