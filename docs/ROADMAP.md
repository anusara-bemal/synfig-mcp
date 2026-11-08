# synfig-mcp Roadmap & Implementation Status (v0.6.0)

## Master Plan Phases

| Phase | Description | Status | Verification & Deliverables |
|---|---|---|---|
| **Phase G0** | Feasibility Gate | **DONE** | Pinned Synfig v1.5.5 UCRT64 build; prototype socket hook verified live circle addition + undo in GTK main thread. |
| **Phase P1** | Monorepo Scaffold & Tooling | **DONE** | Dual-backend monorepo (`server/`, `bridge/`, `docs/`, `examples/`), Poe tasks, lint/typecheck pipelines. |
| **Phase P2** | Wire Protocol, Client & Fake Bridge | **DONE** | JSON-RPC 2.0 schemas, Pydantic models, async `BridgeClient`, `FakeBridgeServer`, contract test suite. |
| **Phase P3** | Bridge Read-Only Path | **DONE** | C++ `mcp_bridge` GTK dispatcher, token authentication, `doc.list`, `doc.info`, `scene.tree`, `param.get`, `anim.time_get`, `selection.get`. Verified live against running Studio. |
| **Phase P4** | Bridge Mutating Path & Undo System | **DONE** | C++ mutating actions wrapped in `synfigapp::Action::PassiveGrouper`, structured diffs, `layer.add`, `param.set`, `history.undo`, `history.redo`, timeline seek, keyframes. Verified live against running Studio. |
| **Phase P5** | Headless SIF Engine & CLI Introspection | **DONE** | Pure-Python lossless XML engine (`lxml.etree`), multi-format (`.sif`, `.sifz`, `.sfg`), CLI runner, schema registry with caching, headless undo/redo snapshot stack. 59/59 tests passing. |
| **Phase P6** | Unified MCP Surface & FastMCP Tools | **DONE** | 47 typed MCP tools over `BackendBase` (`MCPServer`, `@mcp.tool()`, `ToolAnnotations`), active backend auto-selection, clean stdio transport, contract tests across both backends. |
| **Phase P7 (Pre-P7 Live Gaps)** | Live E2E Bridge Hardening & Verification | **DONE** | Real `synfigstudio.exe` E2E test suite: core mutations + undo, ACL verification (`icacls`), safe non-blocking dialogs, LIFO ordering (bridge + manual edit), real Studio MCP marker. |
| **Phase P7a** | Core Animation Write Path & ValueNodes | **DONE** | `anim.waypoint_set`, `anim.waypoint_remove`, `anim.animate_param` (bulk waypoints in 1 undo step), `anim.interpolation_set`, `doc.set_time_range`, `param.convert`, `param.export`, `param.unexport`. Verified against live Studio with undo and timeline interpolation. |
| **Phase P7b** | Render / Preview Pipeline & ADR | **DONE** | High-performance frame/sequence/video rendering, contact sheet generation, progress notifications, cancellation, disk cache keyed by state+params. ADR recorded in `docs/decisions/ADR-0004-render-pipeline.md`. |
| **Phase P8** | Packaging, Distribution & Diagnostics | **DONE** | CI artifact packaging (`bridge-build.yml`), GPL-3.0 notice/offer, `synfig-mcp doctor` CLI, Streamable HTTP transport with bearer auth & host filtering, headless Dockerfile, `server.json`, PyPI build dry-run (`uv build`), Windows installation & troubleshooting guides. |
| **Phase P9** | Documentation, Verification & Release Readiness | **IN PROGRESS** | 8-point verification pass: path safety sandboxing (verified), render pipeline tests (verified), empirical benchmark (verified), HTTP transport security (verified), Docker verification (tested: host unavailable), third-party licenses (verified), prompt-injection security model (verified), and Windows CI build / clean-VM install (tracked open). |

---

## LiveBackend Method Support Matrix (Verified against Real Studio)

| Method | Wire Protocol | Python Client Wired | C++ Handler Implemented | Verified Live (Real Studio) | Undo Restores State |
|---|---|---|---|---|---|
| `hello` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) | N/A (Read) |
| `doc.list` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_mcp_tools.py`) | N/A (Read) |
| `doc.info` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) | N/A (Read) |
| `doc.new` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | N/A (Doc Lifecycle) |
| `doc.open` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | N/A (Doc Lifecycle) |
| `doc.save` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | N/A (Doc Lifecycle) |
| `doc.close` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py` - dirty safe check, error 2004) | N/A (Doc Lifecycle) |
| `scene.tree` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) | N/A (Read) |
| `layer.add` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`, `test_mcp_tools.py`) | **Yes** (`history.undo`) |
| `layer.delete` / `layer.remove` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `layer.duplicate` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `layer.move` / `layer.reorder` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.get` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) | N/A (Read) |
| `param.set` (`real`) | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.set` (`color`) | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.set` (`vector`) | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.set` (`angle`) | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.set` (`bool`) | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.set` (`string`) | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `param.convert` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`, `test_mcp_tools.py`) | **Yes** (`history.undo`) |
| `param.export` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py::test_live_param_export_unexport`) | **Yes** (`history.undo`) |
| `param.unexport` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py::test_live_param_export_unexport`) | **Yes** (`history.undo`) |
| `anim.time.get` / `anim.time_get` | Yes | Yes | Yes | **Yes** (`test_live_read.py`, `test_live_mutate.py`) | N/A (Seek) |
| `anim.time.set` / `anim.time_set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`, `test_mcp_tools.py`) | N/A (Seek) |
| `anim.waypoint_set` / `waypoint.set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`, `test_mcp_tools.py`) | **Yes** (`history.undo`) |
| `anim.waypoint_remove` / `waypoint.remove` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py::test_live_waypoint_remove`) | **Yes** (`history.undo`) |
| `anim.animate_param` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`, `test_mcp_tools.py`) | **Yes** (`history.undo` - 1 single step) |
| `anim.interpolation_set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py::test_live_interpolation_set`) | **Yes** (`history.undo`) |
| `doc.set_time_range` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py::test_live_doc_set_time_range`) | **Yes** (`history.undo`) |
| `keyframe.add` / `anim.keyframe_add` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `keyframe.delete` / `anim.keyframe_remove` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `canvas.render_frame` / `render.frame` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`, `test_mcp_tools.py`) | N/A (Render) |
| `render_sequence` | Yes | Yes | Yes (Pipeline) | **Yes** (`test_live_mutate.py::test_live_render_sequence`) | N/A (Render) |
| `render_sequence` (progress notifications) | Yes | Yes | Yes (Pipeline) | **Yes** (`test_live_mutate.py::test_live_render_progress_notifications`) | N/A (Render) |
| `render_sequence` (cancellation & cleanup) | Yes | Yes | Yes (Pipeline) | **Yes** (`test_live_mutate.py::test_live_render_cancellation`) | N/A (Render) |
| `render_cached_frame` (disk cache) | Yes | Yes | Yes (Pipeline) | **Yes** (`test_live_mutate.py::test_live_render_disk_cache`) | N/A (Render) |
| `render_video` | Yes | Yes | Yes (Pipeline) | **Yes** (`test_live_mutate.py::test_live_render_video`) | N/A (Render) |
| `render_contact_sheet` | Yes | Yes | Yes (Pipeline) | **Yes** (`test_live_mutate.py::test_live_render_contact_sheet`) | N/A (Render) |
| `selection.get` | Yes | Yes | Yes | **Yes** (`test_live_read.py`) | N/A (Read) |
| `selection.set` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | **Yes** (`history.undo`) |
| `history.undo` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py` - AI edit + manual GTK edit LIFO verified) | N/A |
| `history.redo` | Yes | Yes | Yes | **Yes** (`test_live_mutate.py`) | N/A |

---

## Security & Concurrency Verification Summary

1. **Windows Token File ACL**:
   - Implemented in `bridge/src/mcp_bridge/auth.cpp` via Win32 API (`SetNamedSecurityInfoA`).
   - Explicitly removes all inherited permissions using `PROTECTED_DACL_SECURITY_INFORMATION`.
   - Grants `GENERIC_ALL` strictly to current process owner SID.
   - Verified live in `test_live_token_file_acl` via `icacls`, confirming `ANUSARA_BEMAL\anusa:(F)` with zero `(I)` inheritance flags.
2. **GTK Dialog Safe Operations**:
   - `doc.close` checks `inst->get_action_count() > 0`. If dirty and `force=False`, immediately returns error code 2004 without popping GUI modal dialogs.
   - If clean or `force=True`, directly invokes `inst->close()`.
3. **Action Undo Ordering (LIFO)**:
   - Verified interleaving bridge mutations (`layer.add` in `PassiveGrouper`) with direct GTK main thread manual actions (`ci->layer_add_action`).
   - Successive `history.undo` operations roll back the manual GUI action first, followed by the bridge action, preserving exact undo stack integrity.

---

## Phase P9 Verification Items & Open Items Tracking

| Item | Requirement | Status | Verification Evidence / Reason for Open |
|---|---|---|---|
| 1 | Path Safety & Workspace Sandboxing | **VERIFIED** | Enforced across LiveBackend and C++ bridge (`is_safe_bridge_path`, code 1203). Tested via `test_live_tools_path_sandbox_rejection` and `test_bridge_direct_path_safety_rejection` against real Studio. |
| 2 | Render Pipeline Tests | **VERIFIED** | Real Studio tests for progress callback (`test_live_render_progress_notifications`), cancellation & cleanup (`test_live_render_cancellation`), and disk cache hit/miss (`test_live_render_disk_cache`). |
| 3 | Benchmark & ADR-0004 | **VERIFIED** | `benchmarks/bench_render.py` executed (N=20). CLI: 334.29 ms median / 398.57 ms p95. In-Process: 15.08 ms median / 59.51 ms p95 (22.16x preview speedup). ADR-0004 updated with exact figures. |
| 4 | HTTP Transport Security | **VERIFIED** | Official SDK Streamable HTTP transport mounted with `SecurityMiddleware`. Constant-time compare (`secrets.compare_digest`), loopback default `127.0.0.1`, `--allow-remote` required with token for external bind, non-sensitive error bodies. 5/5 tests passing in `test_http_transport.py`. |
| 5 | Docker Verification | **LOCAL UNAVAILABLE / CI AUTOMATED** | Docker daemon is not installed on local host (`The term 'docker' is not recognized`). CI pipeline (`.github/workflows/server-ci.yml`) includes automated `docker-smoke-test` job running `docker build` + `synfig-mcp doctor` + headless render inside container on GitHub Actions Ubuntu runner. |
| 6 | Third-Party Licenses | **VERIFIED** | `bridge/THIRD_PARTY_LICENSES.md` generated by mapping all 75 DLLs in `install/bin` across 48 MSYS2 runtime packages via `pacman -Qo` and `pacman -Qi`, detailing GPL-3.0, LGPL-2.1/3.0, and BSD/MIT terms (including bundled FFmpeg and MLT implications), plus GPL-3.0 Section 6 source offer. |
| 7 | Security Documentation | **VERIFIED** | `docs/security.md` Section 5 details the prompt-injection threat model, untrusted document data model (layer names, canvas titles treated as untrusted strings), and defense-in-depth mitigations. |
| 8 | Windows CI Build & Clean VM | **OPEN (PARTIAL)** | GitHub Actions `bridge-build.yml` (Run [42487747560](https://github.com/anusara-bemal/synfig-mcp/actions/runs/42487747560)) succeeded 100% on both `build-linux` (11m 36s) and `build-windows` (34m 58s)! Clean-VM installation remains unverified without a dedicated clean Windows VM and is explicitly documented as unverified in `docs/install-windows.md`. |
