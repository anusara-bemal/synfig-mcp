# Synfig MCP Wire Protocol Specification (v1.0)

This document specifies the exact JSON-RPC 2.0 wire protocol between the Python MCP Server and the Synfig Studio C++ `mcp_bridge`.

---

## 1. Ground Rules & Transport Architecture

1. **Transport**: Newline-delimited UTF-8 JSON-RPC 2.0 over TCP.
2. **Network Binding**: Strictly `127.0.0.1` (loopback only). Remote interfaces are rejected.
3. **Session Authentication**:
   - On startup, the patched Synfig Studio creates a random 256-bit hex token and writes it with `0600` permissions (user read/write only) to:
     - Linux/macOS: `~/.synfig/mcp_token`
     - Windows: `%USERPROFILE%\.synfig\mcp_token`
   - The MCP client must read this token and supply it in the initial `hello` handshake request.
4. **Limits & Timeouts**:
   - Max JSON message size: **10 MB** (messages exceeding this are closed with error `1005: Oversized Message`).
   - Default request timeout: **5.0 seconds** (configurable up to 60.0 seconds for complex renders).
5. **Compatibility Policy**:
   - The handshake negotiates `protocol_version` (`MAJOR.MINOR`).
   - Breaking changes increment `MAJOR` (e.g., `2.0`); backward-compatible additions increment `MINOR` (e.g., `1.1`).
   - The bridge rejects connections with incompatible `MAJOR` versions with code `1003: Incompatible Protocol Version`.

---

## 2. Handshake Lifecycle

Before issuing any document or canvas methods, the client must perform the handshake:

### 2.1 Request (`hello`)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "hello",
  "params": {
    "protocol_version": "1.0",
    "client_name": "synfig-mcp",
    "token": "a1b2c3d4e5f60718293a4b5c6d7e8f90"
  }
}
```

### 2.2 Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocol_version": "1.0",
    "studio_version": "1.5.5",
    "capabilities": [
      "doc",
      "canvas",
      "layer",
      "param",
      "anim",
      "history",
      "selection"
    ],
    "session_id": "sess_42a8b9c1"
  }
}
```

---

## 3. Value Encoding (Tagged Union & Unit Conversions)

Synfig values are strongly typed via `synfig::ValueBase`. In JSON-RPC payloads, every value is encoded as a tagged union object:

| Type Tag | Synfig Type (`base_types.h`) | JSON Schema Structure | Unit & Conversion Rules |
|---|---|---|---|
| `"real"` | `synfig::type_real` | `{"type": "real", "value": 1.25}` | IEEE 754 float / double. |
| `"integer"` | `synfig::type_integer` | `{"type": "integer", "value": 10}` | 32-bit signed integer. |
| `"bool"` | `synfig::type_bool` | `{"type": "bool", "value": true}` | Boolean (`true` / `false`). |
| `"string"` | `synfig::type_string` | `{"type": "string", "value": "text"}` | UTF-8 encoded string. |
| `"angle"` | `synfig::type_angle` | `{"type": "angle", "degrees": 45.0, "radians": 0.785398}` | Degrees canonical (`degrees = radians * 180 / PI`). |
| `"time"` | `synfig::type_time` | `{"type": "time", "seconds": 2.5, "frame": 60, "time_string": "2s 12f"}` | Canonical time in seconds. `frame = seconds * fps`. |
| `"color"` | `synfig::type_color` | `{"type": "color", "r": 1.0, "g": 0.5, "b": 0.0, "a": 1.0}` | Normalized floats `[0.0, 1.0]`. Linear gamma. |
| `"vector"` | `synfig::type_vector` | `{"type": "vector", "x": 0.0, "y": 0.0, "unit": "synfig", "pixel_x": 960.0, "pixel_y": 540.0}` | **Synfig Units vs Pixels** (see below). |
| `"gradient"` | `synfig::type_gradient` | `{"type": "gradient", "cpoints": [{"pos": 0.0, "color": {...}}, {"pos": 1.0, "color": {...}}]}` | Color stops with position `0.0` to `1.0`. |
| `"bline_point"` | `synfig::type_bline_point` | `{"type": "bline_point", "vertex": {...}, "t1": {...}, "t2": {...}, "width": 1.0, "origin": 0.5, "split": false}` | Spline vertex and tangents. |
| `"bline_point_list"` | `synfig::type_list` | `{"type": "bline_point_list", "points": [...]}` | Ordered list of bline points for outlines/regions. |
| `"canvas_ref"` | `synfig::type_canvas` | `{"type": "canvas_ref", "canvas_id": ":root"}` | Canvas path or exported name. |
| `"valuenode_link"` | `synfig::ValueNode` | `{"type": "valuenode_link", "link_id": "name"}` | Exported / linked ValueNode reference. |

### Unit Conversion Rules: Synfig Units vs Pixels
In Synfig Studio:
- The origin `(0, 0)` is at the **center of the canvas**.
- $+X$ points right, $+Y$ points **up**.
- Standard pixel ratio: $\text{ppu} = 60.0$ pixels per Synfig unit (at 72 DPI).
- For a canvas of width $W$ and height $H$:
  $$x_{\text{synfig}} = \frac{x_{\text{pixel}} - W/2}{\text{ppu}}$$
  $$y_{\text{synfig}} = \frac{H/2 - y_{\text{pixel}}}{\text{ppu}}$$
  $$x_{\text{pixel}} = x_{\text{synfig}} \cdot \text{ppu} + W/2$$
  $$y_{\text{pixel}} = H/2 - y_{\text{synfig}} \cdot \text{ppu}$$

---

## 4. Complete Method Set Mapped to Real Synfig APIs

Every method is verified against the real `synfig-studio` and `synfigapp` headers:

| Protocol Method | Parameters | Backing Synfig / Studio C++ API | Status |
|---|---|---|---|
| `doc.list` | `none` | `studio::App::instance_list` | Verified |
| `doc.new` | `width`, `height`, `fps`, `duration` | `studio::App::new_instance()`, `RendDesc` setup | Verified |
| `doc.open` | `file_path` | `studio::App::open(file_path)` | Verified |
| `doc.save` | `doc_id`, `file_path?` | `instance->save()`, `instance->save_as(path)` | Verified |
| `doc.info` | `doc_id` | `instance->get_canvas()->rend_desc()`, `get_name()` | Verified |
| `doc.set_properties`| `doc_id`, `width?`, `height?`, `fps?`, `start_time?`, `end_time?` | `Action::CanvasRendDescSet::create()` | Verified |
| `doc.close` | `doc_id`, `force?` | `studio::Instance::close()` (dirty documents are refused instead of opening a modal dialog) | Verified |
| `scene.tree` | `doc_id` | `canvas->rbegin()..rend()` recursive layer traversal | Verified |
| `scene.build` | `doc_id`, `layers[]`, `groups?` | `canvas_interface->add_layer_to()` + `Action::ValueDescSet` (waypoints) + `Action::LayerEncapsulate` (groups), all inside one `PassiveGrouper` | Verified |
| `schema.list_layers` | none | `synfig::Layer::book()` runtime factory probe | Verified |
| `canvas.list` | `doc_id` | `canvas->children()`, `canvas->get_root()` | Verified |
| `canvas.create` | `doc_id`, `id` | `Action::CanvasAdd::create()` | Verified |
| `canvas.rename` | `doc_id`, `canvas_id`, `name` | `Canvas::set_name()` | Verified |
| `canvas.delete` | `doc_id`, `canvas_id` | `Canvas::remove_child_canvas()` | Verified |
| `canvas.set_properties` | `doc_id`, `canvas_id`, `width?`, `height?`, `fps?`, `start_time?`, `end_time?`, `background_color?` | `Canvas::rend_desc()` | Verified |
| `layer.add` | `doc_id`, `layer_type`, `canvas_path`, `depth?`, `params?` | `canvas_interface->add_layer_to()` (`Action::LayerAdd`) | Verified |
| `layer.remove` | `doc_id`, `layer_id` | `Action::LayerRemove::create()` | Verified |
| `layer.duplicate` | `doc_id`, `layer_id` | `Action::LayerDuplicate::create()` | Verified |
| `layer.reorder` | `doc_id`, `layer_id`, `new_depth` | `Action::LayerMove::create()` | Verified |
| `layer.raise` | `doc_id`, `layer_id` | `Action::LayerRaise::create()` | Verified |
| `layer.lower` | `doc_id`, `layer_id` | `Action::LayerLower::create()` | Verified |
| `layer.group` | `doc_id`, `layer_ids[]`, `group_name` | `Action::LayerEncapsulate::create()` | Verified |
| `layer.ungroup` | `doc_id`, `group_layer_id` | `Action::LayerExtract::create()` | Verified |
| `param.get` | `doc_id`, `layer_id`, `param_name` | `layer->get_param(param_name)` | Verified |
| `param.list` | `doc_id`, `layer_id`, `canvas_path?` | `layer->get_param_list()` | Verified |
| `param.set` | `doc_id`, `layer_id`, `param_name`, `value` | `Action::LayerParamSet::create()` or `canvas_interface->change_value()` | Verified |
| `param.link` | `doc_id`, `layer_id`, `param_name`, `link_id`| `Action::LayerParamConnect::create()` | Verified |
| `rig.bone_add` | `doc_id`, `layer_id`, `time?`, `origin_x?`, `origin_y?`, `angle?`, `width?`, `tipwidth?`, `parent_index?` | `Action::ValueNodeStaticListInsert` (root bone) / `Action::ValueDescCreateChildBone` (child bone) | Verified |
| `param.convert` | `doc_id`, `layer_id`, `param_name`, `type` | `synfigapp::Action::ValueDescConvert::create()` | Verified |
| `param.export` | `doc_id`, `layer_id`, `param_name`, `name` | `synfigapp::Action::ValueDescExport::create()` | Verified |
| `param.unexport` | `doc_id`, `name` | `synfigapp::Action::ValueNodeRemove::create()` | Verified |
| `anim.time_get` | `doc_id` | `canvas_interface->get_time()` | Verified |
| `anim.waypoint_list` | `doc_id`, `layer_id`, `param_name` | `ValueNode_Animated::waypoint_list()` | Verified |
| `anim.keyframe_list` | `doc_id`, `canvas_path?` | `canvas->keyframe_list()` | Verified |
| `anim.time_set` | `doc_id`, `time` | `canvas_interface->seek_time(time)` | Verified |
| `anim.keyframe_add` | `doc_id`, `time`, `description?` | `synfigapp::Action::KeyframeAdd::create()` | Verified |
| `anim.keyframe_remove`| `doc_id`, `time` | `synfigapp::Action::KeyframeRemove::create()` | Verified |
| `anim.waypoint_set` | `doc_id`, `layer_id`, `param_name`, `time`, `value`, `interpolation_in?`, `interpolation_out?` | `synfigapp::Action::ValueDescSet::create()` (animate=true) + `synfigapp::Action::WaypointSet::create()` | Verified |
| `anim.waypoint_remove`| `doc_id`, `layer_id`, `param_name`, `time` | `synfigapp::Action::WaypointRemove::create()` | Verified |
| `anim.animate_param` | `doc_id`, `layer_id`, `param_name`, `waypoints[]` | `synfigapp::Action::PassiveGrouper` wrapping batch `ValueDescSet` + `WaypointSet` (single undo step) | Verified |
| `anim.interpolation_set` | `doc_id`, `interpolation`, `layer_id?`, `param_name?`, `time?` | `synfigapp::Main::set_interpolation()` or `synfigapp::Action::WaypointSet::create()` | Verified |
| `doc.set_time_range` | `doc_id`, `start_time`, `end_time`, `fps?` | `synfigapp::Action::CanvasRendDescSet::create()` | Verified |
| `history.undo` | `doc_id` | `instance->undo()` | Verified |
| `history.redo` | `doc_id` | `instance->redo()` | Verified |
| `history.list` | `doc_id` | `instance->undo_action_stack()`, `redo_action_stack()` | Verified |
| `selection.get` | `doc_id` | `canvas_view->get_selection_manager()->get_selected_layers()` | Verified |
| `selection.set` | `doc_id`, `layer_ids[]` | `canvas_view->get_selection_manager()->set_selected_layers()` | Verified |
| `rig.skeleton_create`| `doc_id`, `name` | `Action::LayerAdd::create("skeleton")` | **Not implemented** (planned) |
| `rig.bone_add` | `doc_id`, `skeleton_layer`, `parent_bone?` | `Action::ValueDescCreateChildBone::create()` | **Not implemented** (planned) |
| `rig.bone_bind` | `doc_id`, `layer_id`, `bone_id` | `Action::ValueDescBoneLink::create()` | **Not implemented** (planned) |
| `render.frame` | `doc_id`, `time`, `width?`, `height?` | Off-thread render via CLI temp save or async renderer | Verified |

> [!WARNING]
> **Identified P3/P4 Risks**:
> `rig.bone_add` and `rig.bone_bind`: While `ValueDescCreateChildBone` and `ValueDescBoneLink` exist in `synfigapp/actions`, their parameter dictionaries require exact internal GUID/ValueNode structure. They are therefore listed as *not implemented* until they are probed with golden project files.

> The table is checked against the C++ dispatcher by `server/tests/unit/test_protocol_docs.py`: a method that is documented but missing from the bridge (or the other way round) fails the build.

---

## 5. Server-to-Client Notifications

Notifications emit when the active document state changes (e.g., manual artist edit):
- `event.selection_changed`: `{"doc_id": "...", "selected_layers": ["circle001"]}`
- `event.time_changed`: `{"doc_id": "...", "time": 2.5}`
- `event.document_changed`: `{"doc_id": "...", "action": "LayerAdd", "layer_id": "rect001"}`
- `event.document_closed`: `{"doc_id": "..."}`

---

## 6. Stable Numeric Error Codes

| Code | Name | Description |
|---|---|---|
| `1001` | `BridgeConnectionError` | Socket connection failed or refused. |
| `1002` | `BridgeAuthError` | Bad or missing authentication token. |
| `1003` | `ProtocolMismatchError` | Incompatible major protocol version. |
| `1004` | `RequestTimeout` | Bridge operation timed out. |
| `1005` | `OversizedMessage` | Received message exceeds 10 MB limit. |
| `1101` | `DocumentNotFound` | Specified `doc_id` is not open. |
| `1102` | `LayerNotFound` | Layer not found in canvas hierarchy. |
| `1103` | `ParamNotFound` | Parameter does not exist on layer. |
| `1201` | `ValidationError` | Parameters failed JSON Schema validation. |
| `1202` | `SecuritySandboxError` | File path outside allowed workspace roots. |
| `1301` | `ActionExecutionError` | `synfigapp::Action::System` returned false. |
| `1302` | `RenderError` | Frame or sequence rendering failed. |
