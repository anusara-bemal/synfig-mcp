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
| **Phase P9** | Documentation, Verification & Release Candidate (v0.7.0-rc1) | **DONE** | Comprehensive 8-point verification pass: broad workspace roots rejection, MCP-level progress & cancellation, path safety across all remaining tools, untrusted document strings, Python 3.14 alignment, GPL-3.0 source bundle + FFmpeg buildconf verification, bridge default/multi-instance probing, and Linux xvfb CI analysis. Tagged `v0.7.0-rc1` PRE-RELEASE. |
| **Phase P10** | Release & Registry Distribution | **PLANNED** | Clean-VM testing, manual Claude Desktop user testing, public PyPI release, MCP Registry publication. |

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
| 1 | Broad Workspace Roots Rejection | **VERIFIED** | Bridge and server reject drive root (`C:\`, `/`), user home (`Path.home()`), `C:\Windows`, `C:\Program Files` with typed error code 1203. Default roots are narrow (`Path.cwd()`, OS temp dir). Verified against real Studio in `test_bridge_broad_workspace_roots_rejection`. |
| 2 | MCP-Level Progress & Cancellation Tests | **VERIFIED** | Multi-frame render with progress token emits MCP progress notifications; client cancellation cleans partial files. Verified in `test_mcp_client_progress_notifications` and `test_mcp_client_cancellation_cleanup`. Official SDK limitation on `notifications/cancelled` documented. |
| 3 | Path Safety for All Remaining Tools | **VERIFIED** | Real Studio tests for `render_sequence`, `render_video`, `render_contact_sheet`, and `import_asset` testing `..` escape, absolute paths outside roots, disallowed extensions, and inside-root success in `test_live_all_remaining_tools_path_safety`. |
| 4 | Untrusted Document Strings & Hostile Injection | **VERIFIED** | Document-derived strings wrapped with `_security_notice` field and tool prompt warnings. Tested against hostile layer name (`HostileCircle\nIGNORE ALL INSTRUCTIONS...`) in `test_live_hostile_document_strings`. |
| 5 | Python 3.14 Alignment | **VERIFIED** | Removed `Python :: 3.14` classifier from `pyproject.toml` to align strictly with CI matrix (`[3.12, 3.13]`). |
| 6 | GPL Packaging & FFmpeg Build Configuration | **VERIFIED** | Full `ffmpeg -buildconf` verified and recorded in `docs/gpl-compliance.md` (GPL-3.0 compatible). Script `bridge/scripts/package_gpl_source.py` packages pinned upstream commit (`79bf708`), patches, build scripts, and license metadata into `dist/synfig-mcp-gpl-source-v0.7.0.tar.gz`. |
| 7 | Bridge Default & Multi-Instance Behavior | **VERIFIED** | Enabled by default on port 19998; disabled via `SYNFIG_MCP_DISABLE=1`. Auto-probes ports (19998..20007) and writes per-PID token `~/.synfig/mcp_token_<pid>`. Verified against real Studio in `test_bridge_multi_instance_ports_and_disable`. Upstream `Gtk::Application` single-instance documented. |
| 8 | Linux CI with Real Studio (xvfb) | **ANALYZED / DOCUMENTED** | Feasibility confirmed: `xvfb-run` works with headless X11. Recommended in `bridge-build.yml` or release builds to avoid 20-minute overhead on everyday Python CI. Fast Python CI remains in `server-ci.yml`. |
| Open | Clean-VM Install & Claude Desktop Manual E2E | **OPEN (P10)** | Automated tests pass 100%; manual verification on a virgin Windows VM without developer toolchains is scheduled for Phase P10 prior to public registry publishing. |
