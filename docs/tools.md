# Tool Surface Catalog (~45 Typed Tools)

All MCP tools are typed, validated with JSON Schema, and annotated with operational properties (read-only, destructive, idempotent, open-world).

---

## 1. Tool Groups

### System & Health
- `health_check`: Backend status, versions, bridge connectivity.
- `get_capabilities`: Supported features of the active backend.
- `list_layer_types`: Introspected catalog of layer types.
- `describe_layer_type`: Parameter schema for a specific layer type.

### Project & Document
- `doc_list`: Currently active/loaded documents.
- `doc_new`: Create a new animation canvas with dimensions, FPS, and length.
- `doc_open`: Open an existing `.sif` / `.sifz` project.
- `doc_save`: Save changes to disk.
- `doc_set_properties`: Adjust dimensions, FPS, time bounds, or background.

### Layers & Hierarchy
- `scene_tree`: Complete layer tree hierarchy.
- `layer_add`: Insert a new layer (circle, star, outline, spline, etc.).
- `layer_remove`: Delete a layer.
- `layer_reorder`: Adjust depth / z-order in stack.
- `layer_group`: Group layers into a Switch or Group layer.

### Parameters & Animation
- `param_get`: Retrieve parameter value.
- `param_set`: Set parameter value (static or animated).
- `waypoint_set`: Add an animation waypoint at a given time.
- `keyframe_add`: Mark an animation keyframe.

### History & Live Controls
- `undo`: Undo the last operation (one undo step per tool call).
- `redo`: Redo the previous undo.
