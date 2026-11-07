# synfig-mcp Roadmap & Implementation Status

## Master Plan Phases

| Phase | Description | Status | Verification & Deliverables |
|---|---|---|---|
| **Phase G0** | Feasibility Gate | **DONE** | Pinned Synfig v1.5.5 UCRT64 build; prototype socket hook verified live circle addition + undo in GTK main thread. |
| **Phase P1** | Monorepo Scaffold & Tooling | **DONE** | Dual-backend monorepo (`server/`, `bridge/`, `docs/`, `examples/`), Poe tasks, lint/typecheck pipelines. |
| **Phase P2** | Wire Protocol, Client & Fake Bridge | **DONE** | JSON-RPC 2.0 schemas, Pydantic models, async `BridgeClient`, `FakeBridgeServer`, contract test suite. |
| **Phase P3** | Bridge Read-Only Path | **DONE** | C++ `mcp_bridge` GTK dispatcher, token authentication, `doc.list`, `doc.info`, `scene.tree`, `param.get`, `anim.time_get`, `selection.get`. Verified live against running Studio. |
| **Phase P4** | Bridge Mutating Path & Undo System | **DONE** | C++ mutating actions wrapped in `synfigapp::Action::PassiveGrouper`, structured diffs, `layer.add`, `param.set`, `history.undo`, `history.redo`, timeline seek, keyframes. Verified live against running Studio. |
| **Phase P5** | Headless SIF Engine & CLI Introspection | **DONE** | Pure-Python lossless XML engine (`lxml.etree`), multi-format (`.sif`, `.sifz`, `.sfg`), CLI runner, schema registry with caching, headless undo/redo snapshot stack. 42/42 tests passing. |
| **Phase P6** | Unified MCP Surface & FastMCP Tools | **IN PROGRESS** | Typed MCP tools over `BackendBase` (`MCPServer`, `@mcp.tool()`, `ToolAnnotations`), active backend auto-selection, clean stdio transport, comprehensive contract tests. |
| **Phase P7** | End-to-End Live Workflow Verification | **PENDING** | Complex animation scenarios driven live via MCP client, stress testing, undo/redo mixing with manual user edits. |
| **Phase P8** | Claude Desktop Integration, Examples & Packaging | **PENDING** | `claude_desktop_config.json`, sample walkthroughs, PyPI packaging (`uv build`), reproducible MSYS2 build scripts. |

---

## LiveBackend Method Support Matrix

| Method | Wire Protocol | Python Client Wired | C++ Handler Implemented | Verified Live (Real Studio) |
|---|---|---|---|---|
| `hello` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) |
| `doc.list` | Yes | Yes | Yes | **Yes** (`test_live_read.py`) |
| `doc.info` | Yes | Yes | Yes | **Yes** (`test_live_read.py`) |
| `doc.new` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `doc.open` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `doc.save` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `doc.set_properties` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `canvas.list` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `canvas.create` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `scene.tree` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) |
| `layer.add` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `layer.remove` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `layer.duplicate` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `layer.reorder` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `layer.raise` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `layer.lower` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `layer.group` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `layer.ungroup` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `param.get` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) |
| `param.set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `anim.time_get` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) |
| `anim.time_set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `anim.keyframe_add` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `anim.keyframe_remove` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `anim.waypoint_set` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `selection.get` | Yes | Yes | Yes | **Yes** (`test_live_read.py`) |
| `selection.set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `history.undo` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `history.redo` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) |
| `history.list` | Yes | Yes | Yes | Contract test only (Live Studio E2E pending) |
| `render.frame` | Yes | Yes | Yes | Headless / CLI verified |

---

## Tracked Gaps & Technical Debt

1. **Live Studio E2E Coverage for Secondary Mutating Actions**:
   - `doc.new`, `doc.save`, `doc.open`, `doc.set_properties`, `canvas.create`, `layer.duplicate`, `layer.group`, `layer.ungroup`, `anim.waypoint_set`, `history.list` are fully implemented in C++ and Python and validated via `FakeBridge` contract tests, but have not yet been exercised against a live running `synfigstudio.exe` process in an automated E2E test.
2. **Windows Token File ACL Restrictions**:
   - On POSIX, `auth.cpp` invokes `chmod(path, 0600)`. On Windows, the token file is created in `%USERPROFILE%\.synfig\mcp_token` inheriting default user directory ACLs. Explicit Win32 DACL hardening (`SetNamedSecurityInfoW` with single-user SID) is unverified and should be added for production hardening.
