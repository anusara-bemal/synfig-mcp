# Synfig MCP Tools Reference

> Auto-generated reference for all 100+ MCP tools provided by `synfig-mcp`.

## Table of Contents

- [`add_advanced_outline`](#add-advanced-outline)
- [`add_bevel`](#add-bevel)
- [`add_bline`](#add-bline)
- [`add_blur`](#add-blur)
- [`add_checkerboard`](#add-checkerboard)
- [`add_circle`](#add-circle)
- [`add_clamp`](#add-clamp)
- [`add_color_correct`](#add-color-correct)
- [`add_distortions`](#add-distortions)
- [`add_duplicate`](#add-duplicate)
- [`add_gradient`](#add-gradient)
- [`add_halftone`](#add-halftone)
- [`add_image`](#add-image)
- [`add_keyframe`](#add-keyframe)
- [`add_layer`](#add-layer)
- [`add_motion_blur`](#add-motion-blur)
- [`add_noise_gradient`](#add-noise-gradient)
- [`add_outline`](#add-outline)
- [`add_polygon`](#add-polygon)
- [`add_radial_blur`](#add-radial-blur)
- [`add_rectangle`](#add-rectangle)
- [`add_region`](#add-region)
- [`add_rotate`](#add-rotate)
- [`add_shade`](#add-shade)
- [`add_solid_color`](#add-solid-color)
- [`add_star`](#add-star)
- [`add_stretch`](#add-stretch)
- [`add_text`](#add-text)
- [`add_time_offset`](#add-time-offset)
- [`add_translate`](#add-translate)
- [`add_twirl`](#add-twirl)
- [`add_waypoint`](#add-waypoint)
- [`add_zoom`](#add-zoom)
- [`animate_param`](#animate-param)
- [`apply_template`](#apply-template)
- [`bake_animation`](#bake-animation)
- [`batch_operations`](#batch-operations)
- [`bind_skeleton`](#bind-skeleton)
- [`cancel_render`](#cancel-render)
- [`close_project`](#close-project)
- [`convert_param`](#convert-param)
- [`create_bone`](#create-bone)
- [`create_project`](#create-project)
- [`delete_layer`](#delete-layer)
- [`diff_projects`](#diff-projects)
- [`disable_layer`](#disable-layer)
- [`duplicate_layer`](#duplicate-layer)
- [`duplicate_project`](#duplicate-project)
- [`embed_image`](#embed-image)
- [`enable_layer`](#enable-layer)
- [`exclude_from_rendering`](#exclude-from-rendering)
- [`export_json_snapshot`](#export-json-snapshot)
- [`export_value`](#export-value)
- [`get_layer`](#get-layer)
- [`get_layer_param`](#get-layer-param)
- [`get_project_info`](#get-project-info)
- [`get_render_status`](#get-render-status)
- [`group_layers`](#group-layers)
- [`import_asset`](#import-asset)
- [`import_json_snapshot`](#import-json-snapshot)
- [`import_svg`](#import-svg)
- [`install_synfig_plugin`](#install-synfig-plugin)
- [`link_params`](#link-params)
- [`list_assets`](#list-assets)
- [`list_bones`](#list-bones)
- [`list_bones_tool`](#list-bones-tool)
- [`list_exported_values`](#list-exported-values)
- [`list_keyframes`](#list-keyframes)
- [`list_layer_types`](#list-layer-types)
- [`list_layers`](#list-layers)
- [`list_open_projects`](#list-open-projects)
- [`list_render_targets`](#list-render-targets)
- [`lock_layer`](#lock-layer)
- [`move_keyframe`](#move-keyframe)
- [`move_layer`](#move-layer)
- [`open_in_studio`](#open-in-studio)
- [`open_project`](#open-project)
- [`redo`](#redo)
- [`remove_keyframe`](#remove-keyframe)
- [`remove_waypoint`](#remove-waypoint)
- [`rename_layer`](#rename-layer)
- [`render_animation`](#render-animation)
- [`render_frame`](#render-frame)
- [`render_preview`](#render-preview)
- [`render_thumbnail`](#render-thumbnail)
- [`save_project`](#save-project)
- [`save_project_as`](#save-project-as)
- [`set_amount`](#set-amount)
- [`set_blend_method`](#set-blend-method)
- [`set_bone_param`](#set-bone-param)
- [`set_canvas_inline`](#set-canvas-inline)
- [`set_canvas_properties`](#set-canvas-properties)
- [`set_fps`](#set-fps)
- [`set_image_span`](#set-image-span)
- [`set_interpolation`](#set-interpolation)
- [`set_layer_param`](#set-layer-param)
- [`set_time_loop`](#set-time-loop)
- [`set_time_range`](#set-time-range)
- [`set_z_depth`](#set-z-depth)
- [`synfig_doctor`](#synfig-doctor)
- [`synfig_version`](#synfig-version)
- [`undo`](#undo)
- [`ungroup_layers`](#ungroup-layers)
- [`unlink_params`](#unlink-params)
- [`validate_project`](#validate-project)

---

## `add_advanced_outline`

Add an advanced outline (width-profile stroked bline).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `vertices` | `array | null` | No | `null` | — |
| `bline_id` | `string | null` | No | `null` | — |
| `tangents` | `array | null` | No | `null` | — |
| `width` | `number` | No | `0.05` | — |
| `loop` | `boolean` | No | `false` | — |
| `start_tip` | `integer` | No | `0` | — |
| `end_tip` | `integer` | No | `0` | — |
| `color` | `string | array | null` | No | `null` | — |
| `feather` | `number` | No | `0.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_advanced_outline",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_bevel`

Add a bevel filter (fake 3D emboss).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `type` | `integer` | No | `0` | — |
| `color1` | `string | array` | No | `"#ffffff"` | — |
| `color2` | `string | array` | No | `"#000000"` | — |
| `angle` | `number` | No | `45.0` | — |
| `depth` | `number` | No | `0.1` | — |
| `softness` | `number` | No | `0.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_bevel",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_bline`

Create an exported (defs) bline with the given id.

Returns the defs id to reference from region/outline layers via bline_id.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `id` | `string` | Yes | — | — |
| `vertices` | `array[array]` | Yes | — | — |
| `tangents` | `array | null` | No | `null` | — |
| `width` | `number` | No | `1.0` | — |
| `loop` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_bline",
  "arguments": {
    "project_id": "sample_project_id",
    "id": "sample_id",
    "vertices": []
  }
}
```

---

## `add_blur`

Add a blur filter (size in canvas units, type 0/1/2).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `size` | `array | null` | No | `null` | — |
| `type` | `integer` | No | `1` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_blur",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_checkerboard`

Add a checkerboard pattern layer.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `color` | `string | array` | No | `"#808080"` | — |
| `pos` | `array | null` | No | `null` | — |
| `size` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_checkerboard",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_circle`

Add a circle layer (default grey, radius 0.5 units).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `center` | `array | null` | No | `null` | — |
| `radius` | `number` | No | `0.5` | — |
| `color` | `string | array | null` | No | `null` | — |
| `feather` | `number` | No | `0.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_circle",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_clamp`

Add a clamp filter (limits the value range).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `floor` | `number` | No | `0.0` | — |
| `ceiling` | `number` | No | `1.0` | — |
| `invert_negative` | `boolean` | No | `true` | — |
| `clamp_ceiling` | `boolean` | No | `true` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_clamp",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_color_correct`

Add a color correction filter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `hue_adjust` | `number` | No | `0.0` | — |
| `brightness` | `number` | No | `0.0` | — |
| `contrast` | `number` | No | `0.0` | — |
| `exposure` | `number` | No | `0.0` | — |
| `saturation` | `number` | No | `0.0` | — |
| `gamma` | `number` | No | `1.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_color_correct",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_distortions`

Add a noise-based distortion filter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `displacement` | `number` | No | `0.05` | — |
| `size` | `array | null` | No | `null` | — |
| `seed` | `integer` | No | `12345` | — |
| `smooth` | `integer` | No | `4` | — |
| `detail` | `integer` | No | `1` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_distortions",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_duplicate`

Add a duplicate filter (re-renders a layer chosen by index).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `index_source` | `integer` | No | `0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_duplicate",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_gradient`

Add a gradient layer (linear, radial, conical or spiral).

stops: [{"pos": 0..1, "color": "#rrggbb"}, ...] — creates an inline gradient.
gradient_id: reference an existing defs gradient instead of creating one.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `kind` | `string` | No | `"linear"` | — |
| `stops` | `array | null` | No | `null` | — |
| `gradient_id` | `string | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |
| `p1` | `array | null` | No | `null` | — |
| `p2` | `array | null` | No | `null` | — |
| `center` | `array | null` | No | `null` | — |
| `radius` | `number` | No | `1.0` | — |
| `angle` | `number` | No | `0.0` | — |
| `loop` | `boolean` | No | `false` | — |
| `zigzag` | `boolean` | No | `false` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_gradient",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_halftone`

Add a halftone filter (kind: halftone2 or halftone3).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `kind` | `string` | No | `"halftone2"` | — |
| `origin` | `array | null` | No | `null` | — |
| `angle` | `number` | No | `45.0` | — |
| `size` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_halftone",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_image`

Add an imported-image layer. filename must be inside the workspace.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `filename` | `string` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |
| `tl` | `array | null` | No | `null` | — |
| `br` | `array | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_image",
  "arguments": {
    "project_id": "sample_project_id",
    "filename": "sample_filename"
  }
}
```

---

## `add_keyframe`

Add a keyframe (time comment) to the canvas.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `time` | `string` | Yes | — | — |
| `label` | `string` | No | `""` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_keyframe",
  "arguments": {
    "project_id": "sample_project_id",
    "time": "sample_time"
  }
}
```

---

## `add_layer`

Add a layer of any type to the project.

params is a dict like {"radius": 0.5, "center": [0, 0], "color": "#ff8800"}.
index is the paint position (0 = painted first = background).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer_type` | `string` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |
| `params` | `object | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |
| `active` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer_type": "sample_layer_type"
  }
}
```

---

## `add_motion_blur`

Add a motion blur filter (aperture in frames).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `aperture` | `number` | No | `1.0` | — |
| `subsamples_factor` | `number` | No | `1.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_motion_blur",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_noise_gradient`

Add a noise layer (noise-driven gradient fill).

stops defaults to a black→white two-color gradient.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `stops` | `array | null` | No | `null` | — |
| `seed` | `integer` | No | `12345` | — |
| `size` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_noise_gradient",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_outline`

Add an outline (stroked bline).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `vertices` | `array | null` | No | `null` | — |
| `bline_id` | `string | null` | No | `null` | — |
| `tangents` | `array | null` | No | `null` | — |
| `width` | `number` | No | `0.05` | — |
| `loop` | `boolean` | No | `false` | — |
| `color` | `string | array | null` | No | `null` | — |
| `feather` | `number` | No | `0.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_outline",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_polygon`

Add a filled polygon from vertices ([[x, y], ...]).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `vertices` | `array[array]` | Yes | — | — |
| `color` | `string | array | null` | No | `null` | — |
| `origin` | `array | null` | No | `null` | — |
| `feather` | `number` | No | `0.0` | — |
| `winding_style` | `integer` | No | `0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_polygon",
  "arguments": {
    "project_id": "sample_project_id",
    "vertices": []
  }
}
```

---

## `add_radial_blur`

Add a radial blur filter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `origin` | `array | null` | No | `null` | — |
| `size` | `array | null` | No | `null` | — |
| `fade_out` | `boolean` | No | `false` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_radial_blur",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_rectangle`

Add a rectangle layer between two corner points (default 1x1 at origin).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `point1` | `array | null` | No | `null` | — |
| `point2` | `array | null` | No | `null` | — |
| `color` | `string | array | null` | No | `null` | — |
| `expand` | `number` | No | `0.0` | — |
| `bevel` | `number` | No | `0.0` | — |
| `feather_x` | `number` | No | `0.0` | — |
| `feather_y` | `number` | No | `0.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_rectangle",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_region`

Add a filled region (bline spline area).

Pass either vertices (inline bline) or bline_id (reference an exported
bline from defs/add_bline). tangents are per-vertex tangent vectors.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `vertices` | `array | null` | No | `null` | — |
| `bline_id` | `string | null` | No | `null` | — |
| `tangents` | `array | null` | No | `null` | — |
| `width` | `number` | No | `1.0` | — |
| `loop` | `boolean` | No | `true` | — |
| `color` | `string | array | null` | No | `null` | — |
| `feather` | `number` | No | `0.0` | — |
| `winding_style` | `integer` | No | `0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_region",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_rotate`

Add a rotate filter (angle in degrees).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `angle` | `number` | No | `0.0` | — |
| `origin` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_rotate",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_shade`

Add a shadow/shade filter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `color` | `string | array` | No | `"#000000"` | — |
| `origin` | `array | null` | No | `null` | — |
| `size` | `array | null` | No | `null` | — |
| `type` | `integer` | No | `0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_shade",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_solid_color`

Add a solid color layer.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `color` | `string | array` | No | `"#808080"` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_solid_color",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_star`

Add a star (or regular polygon when regular_polygon=True).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `points` | `integer` | No | `5` | — |
| `radius1` | `number` | No | `0.5` | — |
| `radius2` | `number` | No | `0.2` | — |
| `angle` | `number` | No | `90.0` | — |
| `regular_polygon` | `boolean` | No | `false` | — |
| `color` | `string | array | null` | No | `null` | — |
| `origin` | `array | null` | No | `null` | — |
| `feather` | `number` | No | `0.0` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_star",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_stretch`

Add a stretch filter. amount = scale per axis (default [1, 1]).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `amount` | `array | null` | No | `null` | — |
| `center` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_stretch",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_text`

Add a text layer. Text is sanitized (control chars stripped).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `text` | `string` | Yes | — | — |
| `origin` | `array | null` | No | `null` | — |
| `family` | `string` | No | `"sans-serif"` | — |
| `size` | `array | number` | No | `0.6` | — |
| `weight` | `integer` | No | `400` | — |
| `color` | `string | array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_text",
  "arguments": {
    "project_id": "sample_project_id",
    "text": "sample_text"
  }
}
```

---

## `add_time_offset`

Set the time offset of a layer that supports it (e.g. pastecanvas/group).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `time_offset` | `string` | No | `"0f"` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_time_offset",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `add_translate`

Add a translate filter (moves layers by offset in canvas units).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `offset` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_translate",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_twirl`

Add a twirl (swirl distortion) filter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `center` | `array | null` | No | `null` | — |
| `radius` | `number` | No | `1.0` | — |
| `rotations` | `number` | No | `30.0` | — |
| `distort_inside` | `boolean` | No | `true` | — |
| `distort_outside` | `boolean` | No | `true` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_twirl",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `add_waypoint`

Add or replace a single waypoint on an animated parameter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `time` | `string` | Yes | — | — |
| `value` | `any` | Yes | — | — |
| `interpolation` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_waypoint",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "time": "sample_time",
    "value": "value"
  }
}
```

---

## `add_zoom`

Add a zoom filter (amount=1 is identity).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `amount` | `number` | No | `1.0` | — |
| `center` | `array | null` | No | `null` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "add_zoom",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `animate_param`

Animate a parameter with waypoints.

waypoints: [{"time": "0f", "value": 0.0, "before": "linear"?, "after": "linear"?}, ...]
interpolation sets all waypoints' before/after (constant, linear, clamped, tcb, ease, halt).
Re-saving the same time replaces the existing waypoint.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `waypoints` | `array[object]` | Yes | — | — |
| `interpolation` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "animate_param",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "waypoints": []
  }
}
```

---

## `apply_template`

Apply a built-in template.

Templates: 'bouncing-ball', 'title-card', 'logo-reveal'.
Templates create a small, ready-to-render scene using only public
layer parameters; they never overwrite existing layers.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `template` | `string` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "apply_template",
  "arguments": {
    "project_id": "sample_project_id",
    "template": "sample_template"
  }
}
```

---

## `bake_animation`

Bake an animated parameter into dense linear waypoints.

Samples the curve every step_frames frames and rewrites the parameter
with linear-interpolated waypoints. Linear segments are exact; curved
(TCB/ease) segments are resampled — use Synfig Studio's Bake for exact
spline evaluation.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `begin_time` | `string | null` | No | `null` | — |
| `end_time` | `string | null` | No | `null` | — |
| `step_frames` | `integer` | No | `1` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "bake_animation",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param"
  }
}
```

---

## `batch_operations`

Run an ordered list of tool calls atomically.

operations: [{"tool": "add_layer", "arguments": {...}}, ...]
All operations run against the same project (project_id is injected
into each operation that accepts it). On any failure the whole batch
is rolled back (if rollback_on_error=true) and the error reports the
failing operation index. Render tools are not allowed inside a batch.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `operations` | `array[object]` | Yes | — | — |
| `project_id` | `string | null` | No | `null` | — |
| `rollback_on_error` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "batch_operations",
  "arguments": {
    "operations": []
  }
}
```

---

## `bind_skeleton`

Bind a vector/bline_point parameter to bones via boneinfluence.

bones: names/ids/guids of bones created with create_bone. weights:
relative influence per bone (default 1.0 each).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `bones` | `array[string]` | Yes | — | — |
| `weights` | `array | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "bind_skeleton",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "bones": []
  }
}
```

---

## `cancel_render`

Cancel a running render by id.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `render_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "cancel_render",
  "arguments": {
    "render_id": "sample_render_id"
  }
}
```

---

## `close_project`

Close an open project. If save=True the project is saved first.

Unsaved changes are reported as discarded when save=False.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `save` | `boolean` | No | `false` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "close_project",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `convert_param`

Convert a parameter's value node type.

to:
- 'static': freeze an animated parameter to its first waypoint value
- 'animated': wrap a constant parameter in a single waypoint at 0f
- 'linked': link this parameter to another parameter (source_layer/source_param)
- 'exported': move the value into defs under export_name (auto-generated if omitted)

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `to` | `string` | Yes | — | — |
| `source_layer` | `string | integer | null` | No | `null` | — |
| `source_param` | `string | null` | No | `null` | — |
| `export_name` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "convert_param",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "to": "sample_to"
  }
}
```

---

## `create_bone`

Create a bone in the canvas skeleton (<bones> section).

Bones are stored as exported value nodes (Synfig 1.5.x cannot
round-trip a skeleton layer's bones parameter; Studio manages that
side on open). Subsequent list_bones/set_bone_param calls address the
bone by name.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `name` | `string` | Yes | — | — |
| `origin` | `array | null` | No | `null` | — |
| `angle` | `number` | No | `0.0` | — |
| `length` | `number` | No | `1.0` | — |
| `width` | `number` | No | `0.3` | — |
| `tipwidth` | `number` | No | `0.15` | — |
| `parent` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "create_bone",
  "arguments": {
    "project_id": "sample_project_id",
    "name": "sample_name"
  }
}
```

---

## `create_project`

Create a new empty Synfig project.

background: '#rrggbb[aa]' or 'r g b a' (0..1). view_box: [minx, maxy,
maxx, miny] in canvas units. gamma: single value or [r, g, b]. If
save=True the project is written to the workspace immediately.
Returns JSON with project_id and the saved path.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | `string` | Yes | — | — |
| `width` | `integer` | No | `512` | — |
| `height` | `integer` | No | `512` | — |
| `fps` | `number` | No | `24.0` | — |
| `begin_time` | `string` | No | `"0f"` | — |
| `end_time` | `string` | No | `"5s 0f"` | — |
| `background` | `string | null` | No | `null` | — |
| `x_res` | `number` | No | `2834.64591` | — |
| `y_res` | `number` | No | `2834.64591` | — |
| `view_box` | `array | null` | No | `null` | — |
| `gamma` | `array | number | null` | No | `null` | — |
| `antialias` | `integer` | No | `1` | — |
| `path` | `string | null` | No | `null` | — |
| `save` | `boolean` | No | `true` | — |
| `open_in_studio` | `boolean` | No | `false` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "create_project",
  "arguments": {
    "name": "sample_name"
  }
}
```

---

## `delete_layer`

Delete a layer (by index or name).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "delete_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `diff_projects`

Diff two open projects (or files) semantically.

Pass a/b as project_ids, or a_path/b_path as workspace file paths.
Reports canvas property changes, added/removed/changed layers and
parameter-level differences (with a cap on reported changes).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `a` | `string | null` | No | `null` | — |
| `b` | `string | null` | No | `null` | — |
| `a_path` | `string | null` | No | `null` | — |
| `b_path` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "diff_projects",
  "arguments": {
    "a": null
  }
}
```

---

## `disable_layer`

Disable (hide/deactivate) a layer without deleting it.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "disable_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `duplicate_layer`

Duplicate a layer; all GUID attributes in the copy are regenerated.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `new_name` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "duplicate_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `duplicate_project`

Duplicate a project to a new file (and open the copy).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `path` | `string | null` | No | `null` | — |
| `new_name` | `string | null` | No | `null` | — |
| `backup` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "duplicate_project",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `embed_image`

Embed an image into the project as an import layer.

Copies the image into the workspace assets directory (unless already
there) and adds an 'import' layer referencing the copy. tl/br set the
top-left/bottom-right corners in canvas units (default square at origin).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `image_path` | `string` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |
| `copy_to_assets` | `boolean` | No | `true` | — |
| `tl` | `array | null` | No | `null` | — |
| `br` | `array | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "embed_image",
  "arguments": {
    "project_id": "sample_project_id",
    "image_path": "sample_image_path"
  }
}
```

---

## `enable_layer`

Enable (show/activate) a layer.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "enable_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `exclude_from_rendering`

Exclude (or re-include) a layer from rendering.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `excluded` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "exclude_from_rendering",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `export_json_snapshot`

Export a full project snapshot as JSON (includes an opaque base64 restore blob).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "export_json_snapshot",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `export_value`

Export a parameter value into defs under a name (referenced via use=":name").

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `export_name` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "export_value",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "export_name": "sample_export_name"
  }
}
```

---

## `get_layer`

Get one layer's summary (and params) by index or name.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `include_params` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "get_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `get_layer_param`

Read a parameter from a layer (decoded to friendly JSON).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "get_layer_param",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param"
  }
}
```

---

## `get_project_info`

Return detailed info about an open project.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "get_project_info",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `get_render_status`

List recent render jobs (or one job when render_id is given).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `render_id` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "get_render_status",
  "arguments": {
    "render_id": null
  }
}
```

---

## `group_layers`

Group top-level layers into a new 'group' layer (moves them into an inline canvas).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layers` | `array[integer]` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "group_layers",
  "arguments": {
    "project_id": "sample_project_id",
    "layers": []
  }
}
```

---

## `import_asset`

Copy an asset (image/sound/etc.) into the workspace assets directory.

The source must be inside the configured workspace. Returns the new
path; use add_image/embed_image to place it in a project. If the file
is already inside the assets directory it is returned as-is.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path` | `string` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "import_asset",
  "arguments": {
    "path": "sample_path"
  }
}
```

---

## `import_json_snapshot`

Create a project from an export_json_snapshot payload.

snapshot: the JSON string (or object) produced by export_json_snapshot.
The embedded base64 XML is restored verbatim (lossless round trip).
path: optional workspace file to save the restored project to.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `snapshot` | `string | object` | Yes | — | — |
| `new_name` | `string | null` | No | `null` | — |
| `path` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "import_json_snapshot",
  "arguments": {
    "snapshot": "value"
  }
}
```

---

## `import_svg`

Import an SVG as a renderable vector image layer.

The SVG is referenced (not inlined) by an 'import' layer using
Synfig's built-in SVG importer; it renders at full vector quality
but is not editable as Synfig layers. Convert to editable layers in
Studio if you need that.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `svg_path` | `string` | Yes | — | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |
| `amount` | `number | null` | No | `null` | — |
| `blend_method` | `string | integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "import_svg",
  "arguments": {
    "project_id": "sample_project_id",
    "svg_path": "sample_svg_path"
  }
}
```

---

## `install_synfig_plugin`

Install the Synfig MCP Sync plugin into Synfig Studio's user plugins folder.

Adds a 'Synfig MCP: Reload Canvas' menu item under Synfig Studio's Plugins menu
so you can instantly refresh the open window whenever the AI modifies files.

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "install_synfig_plugin",
  "arguments": {}
}
```

---

## `link_params`

Link two parameters (target references source's exported value).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `source_layer` | `string | integer` | Yes | — | — |
| `source_param` | `string` | Yes | — | — |
| `target_layer` | `string | integer` | Yes | — | — |
| `target_param` | `string` | Yes | — | — |
| `export_name` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "link_params",
  "arguments": {
    "project_id": "sample_project_id",
    "source_layer": "value",
    "source_param": "sample_source_param",
    "target_layer": "value",
    "target_param": "sample_target_param"
  }
}
```

---

## `list_assets`

List files in the workspace assets directory.

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_assets",
  "arguments": {}
}
```

---

## `list_bones`

List all bones in the canvas.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_bones",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `list_bones_tool`

Alias for list_bones.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_bones_tool",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `list_exported_values`

List all exported values (defs entries with an id).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_exported_values",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `list_keyframes`

List all keyframes on the canvas.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_keyframes",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `list_layer_types`

List layer types supported by this synfig build.

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_layer_types",
  "arguments": {}
}
```

---

## `list_layers`

List layers as a tree (document order; index 0 painted first).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `include_params` | `boolean` | No | `false` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_layers",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `list_open_projects`

List all projects open in this session.

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_open_projects",
  "arguments": {}
}
```

---

## `list_render_targets`

List render targets supported by this synfig build.

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "list_render_targets",
  "arguments": {}
}
```

---

## `lock_layer`

Lock (hit_locked) a layer so it cannot be selected in Studio.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `locked` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "lock_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `move_keyframe`

Move a keyframe to a new time.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `from_time` | `string` | Yes | — | — |
| `to_time` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "move_keyframe",
  "arguments": {
    "project_id": "sample_project_id",
    "from_time": "sample_from_time",
    "to_time": "sample_to_time"
  }
}
```

---

## `move_layer`

Move a layer in paint order (index/offset) and/or set its z_depth.

index is absolute (0 = painted first). offset moves relative to its
current position (positive = painted later = more visible). If only
z_depth is given, the paint order is unchanged.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `index` | `integer | null` | No | `null` | — |
| `offset` | `integer | null` | No | `null` | — |
| `z_depth` | `number | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "move_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `open_in_studio`

Open a project directly inside the Synfig Studio desktop GUI window.

Saves any dirty in-memory state to disk first and opens the GUI application
with the canvas loaded on screen.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string | null` | No | `null` | — |
| `path` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "open_in_studio",
  "arguments": {
    "project_id": null
  }
}
```

---

## `open_project`

Open an existing .sif/.sifz/.sfg project from the workspace.

If the same file is already open, returns the existing project_id.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "open_project",
  "arguments": {
    "path": "sample_path"
  }
}
```

---

## `redo`

Redo the last undone mutation on this project.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "redo",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `remove_keyframe`

Remove the keyframe at the given time.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `time` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "remove_keyframe",
  "arguments": {
    "project_id": "sample_project_id",
    "time": "sample_time"
  }
}
```

---

## `remove_waypoint`

Remove the waypoint at the given time.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `time` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "remove_waypoint",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "time": "sample_time"
  }
}
```

---

## `rename_layer`

Rename a layer (sets the desc attribute shown in Studio).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `name` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "rename_layer",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "name": "sample_name"
  }
}
```

---

## `render_animation`

Render an animation.

target: gif, ffmpeg (mp4/webm), png (sequence), png-spritesheet, bmp,
jpeg, ppm. Targets not present in this synfig build fail with a
clear error listing what's available. lottie is not supported by
synfig and always fails with an actionable message.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `target` | `string` | No | `"gif"` | — |
| `output` | `string | null` | No | `null` | — |
| `width` | `integer | null` | No | `null` | — |
| `height` | `integer | null` | No | `null` | — |
| `begin_time` | `string | null` | No | `null` | — |
| `end_time` | `string | null` | No | `null` | — |
| `fps` | `number | null` | No | `null` | — |
| `quality` | `string | null` | No | `null` | — |
| `antialias` | `integer | null` | No | `null` | — |
| `video_codec` | `string | null` | No | `null` | — |
| `video_bitrate` | `string | null` | No | `null` | — |
| `sprite_separator` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "render_animation",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `render_frame`

Render a single frame to PNG.

Returns JSON with the output path; if return_image=true the PNG is
also attached as MCP image content. Unsaved changes are rendered from
a temporary snapshot.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `output` | `string | null` | No | `null` | — |
| `width` | `integer | null` | No | `null` | — |
| `height` | `integer | null` | No | `null` | — |
| `time` | `string` | No | `"0f"` | — |
| `quality` | `string | null` | No | `null` | — |
| `antialias` | `integer | null` | No | `null` | — |
| `span` | `number | null` | No | `null` | — |
| `return_image` | `boolean` | No | `true` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "render_frame",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `render_preview`

Fast low-quality preview of a frame (default: current canvas start time).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `time` | `string | null` | No | `null` | — |
| `width` | `integer` | No | `480` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "render_preview",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `render_thumbnail`

Small square-ish thumbnail of the canvas (default 256px wide).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `output` | `string | null` | No | `null` | — |
| `time` | `string | null` | No | `null` | — |
| `size` | `integer` | No | `256` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "render_thumbnail",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `save_project`

Save a project back to disk (.sif, .sifz or .sfg).

If path is omitted, saves to the file the project was opened from
(a newly created, unsaved project is written to the workspace under
its name). Backup creates a .bak copy before overwriting.
If open_in_studio=True, opens the saved project in Synfig Studio GUI.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `path` | `string | null` | No | `null` | — |
| `backup` | `boolean` | No | `true` | — |
| `open_in_studio` | `boolean` | No | `false` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "save_project",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `save_project_as`

Save a project to a new path (.sif, .sifz or .sfg).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `path` | `string` | Yes | — | — |
| `backup` | `boolean` | No | `true` | — |
| `open_in_studio` | `boolean` | No | `false` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "save_project_as",
  "arguments": {
    "project_id": "sample_project_id",
    "path": "sample_path"
  }
}
```

---

## `set_amount`

Set layer opacity/amount (0..1).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `amount` | `number` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_amount",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "amount": 1.0
  }
}
```

---

## `set_blend_method`

Set the blend method (e.g. 'composite', 'multiply', 'add', 'onto').

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `blend_method` | `string | integer` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_blend_method",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "blend_method": "value"
  }
}
```

---

## `set_bone_param`

Set a bone parameter: name, origin, angle, scalelx, scalex, width,
tipwidth, bone_depth, length or parent (parent = name of another bone).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `bone` | `string` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `value` | `any` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_bone_param",
  "arguments": {
    "project_id": "sample_project_id",
    "bone": "sample_bone",
    "param": "sample_param",
    "value": "value"
  }
}
```

---

## `set_canvas_inline`

Inline all references to a defs canvas (use=":id") into the layers.

Every ``<param name="canvas" use="canvas_id"/>`` is replaced with a
deep copy of the defs canvas inline. The defs entry is kept (it may
still be referenced elsewhere); remove it manually with a text edit if
nothing references it afterwards.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `canvas_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_canvas_inline",
  "arguments": {
    "project_id": "sample_project_id",
    "canvas_id": "sample_canvas_id"
  }
}
```

---

## `set_canvas_properties`

Update canvas properties (size, resolution, view-box, AA, background, gamma).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `width` | `integer | null` | No | `null` | — |
| `height` | `integer | null` | No | `null` | — |
| `x_res` | `number | null` | No | `null` | — |
| `y_res` | `number | null` | No | `null` | — |
| `view_box` | `array | null` | No | `null` | — |
| `antialias` | `integer | null` | No | `null` | — |
| `background` | `string | null` | No | `null` | — |
| `gamma` | `array | number | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_canvas_properties",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `set_fps`

Set the canvas frame rate (frames per second).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `fps` | `number` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_fps",
  "arguments": {
    "project_id": "sample_project_id",
    "fps": 1.0
  }
}
```

---

## `set_image_span`

Set the render span (diagonal size of the image window).

Stored as canvas meta 'image_span'; render tools also accept span
directly as a parameter (passed to synfig as --span).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `span` | `number` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_image_span",
  "arguments": {
    "project_id": "sample_project_id",
    "span": 1.0
  }
}
```

---

## `set_interpolation`

Set waypoint interpolation: constant, linear, clamped, tcb, ease, halt, manual.

Pass time to update one waypoint; omit to update all waypoints of the parameter.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `interpolation` | `string` | Yes | — | — |
| `time` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_interpolation",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "interpolation": "sample_interpolation"
  }
}
```

---

## `set_layer_param`

Set any parameter on a layer (friendly values accepted).

Examples: {"color": "#ff8800"}, {"radius": 0.75}, {"center": [0.2, -0.1]},
{"amount": 0.5}, {"blend_method": "multiply"}, {"bline": {...}}.
'type' forces the value type (real, integer, angle, time, bool,
string, color, vector, bline, gradient).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |
| `value` | `any` | Yes | — | — |
| `type` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_layer_param",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param",
    "value": "value"
  }
}
```

---

## `set_time_loop`

Add a timeloop filter layer (loops the layers below it).

duration: how long one loop iteration lasts; link_time: source start offset.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `duration` | `string` | No | `"2s 0f"` | — |
| `link_time` | `string` | No | `"0f"` | — |
| `symmetrical` | `boolean` | No | `false` | — |
| `only_for_positive_duration` | `boolean` | No | `true` | — |
| `name` | `string | null` | No | `null` | — |
| `index` | `integer | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_time_loop",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `set_time_range`

Set the animation time range (e.g. '0f' → '5s 0f').

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `begin_time` | `string` | Yes | — | — |
| `end_time` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_time_range",
  "arguments": {
    "project_id": "sample_project_id",
    "begin_time": "sample_begin_time",
    "end_time": "sample_end_time"
  }
}
```

---

## `set_z_depth`

Set a layer's z_depth (rendering depth; higher = further back).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `z_depth` | `number` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "set_z_depth",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "z_depth": 1.0
  }
}
```

---

## `synfig_doctor`

Diagnose the synfig installation.

Returns JSON with the detected binary path, version, available render
targets/renderers/layers, workspace settings and problems.

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "synfig_doctor",
  "arguments": {}
}
```

---

## `synfig_version`

Print the synfig version (requires the binary).

### Parameters

_None_

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "synfig_version",
  "arguments": {}
}
```

---

## `undo`

Undo the last mutation on this project (in-memory history).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "undo",
  "arguments": {
    "project_id": "sample_project_id"
  }
}
```

---

## `ungroup_layers`

Ungroup a 'group' layer: move its children back to the parent canvas.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "ungroup_layers",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value"
  }
}
```

---

## `unlink_params`

Unlink a parameter (inline a private copy of the referenced value).

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string` | Yes | — | — |
| `layer` | `string | integer` | Yes | — | — |
| `param` | `string` | Yes | — | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "unlink_params",
  "arguments": {
    "project_id": "sample_project_id",
    "layer": "value",
    "param": "sample_param"
  }
}
```

---

## `validate_project`

Validate an open project (or a file) structurally.

Returns errors/warnings with codes and hints; 'valid' is true when
there are no errors.

### Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project_id` | `string | null` | No | `null` | — |
| `path` | `string | null` | No | `null` | — |

### Return Value

Structured JSON string (or MCP `Image` content for frame renders).

### Example Call

```json
{
  "tool": "validate_project",
  "arguments": {
    "project_id": null
  }
}
```

---
