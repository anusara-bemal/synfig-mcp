# Wire Protocol Specification

The native bridge uses newline-delimited JSON-RPC 2.0 over TCP bound strictly to `127.0.0.1`.

---

## 1. Handshake & Authentication

Upon connection, the client must initiate the session:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "hello",
  "params": {
    "protocol_version": "1.0",
    "token": "<per-session-token>"
  }
}
```

The bridge responds:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocol_version": "1.0",
    "studio_version": "1.5.5",
    "capabilities": ["doc", "canvas", "layer", "param", "anim", "undo"]
  }
}
```

---

## 2. Standard Method Namespaces

- `doc.*`: Document lifecycle (`doc.list`, `doc.new`, `doc.open`, `doc.save`, `doc.info`, `doc.set_properties`)
- `canvas.*`: Canvas operations (`canvas.list`, `canvas.create`)
- `layer.*`: Layer CRUD (`layer.add`, `layer.remove`, `layer.update`, `layer.duplicate`, `layer.reorder`, `layer.group`)
- `param.*`: Parameter manipulation (`param.get`, `param.set`, `param.link`, `param.convert`)
- `anim.*`: Keyframes and waypoints (`anim.time_set`, `anim.keyframe_add`, `anim.waypoint_set`)
- `history.*`: Undo and redo (`history.undo`, `history.redo`, `history.list`)
