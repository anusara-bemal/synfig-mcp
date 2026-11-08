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
| **Phase P9** | Documentation, Verification & Release Candidate (v0.7.0-rc2) | **DONE** | Comprehensive 9-point verification pass: opt-in bridge default with menu toggle & stale token cleanup, dedicated `~/Documents/SynfigMCP` workspace with broad cwd rejection, MCP progress & `render_cancel(job_id)` tool, untrusted document string warnings across all document tools, FFmpeg buildconf & patent disclaimer, complete GPL-3.0 source bundle (2,606 upstream source files + 48 MSYS2 PKGBUILD recipes), bridge version/commit SHA reporting, and Linux xvfb CI job. Tagged `v0.7.0-rc2` PRE-RELEASE. |
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

## Phase P9 Verification Items & Final Hardening Pass (v0.7.0-rc3)

| Item | Category | Requirement | Status | Verification Evidence / Reason for Open |
|---|---|---|---|---|
| 1 | Release Assets | Inject real git commit SHA at build time into `hello`, `synfig-mcp doctor`, About dialog, and Studio UI | **VERIFIED** | Real commit SHA injected via `apply_patches.sh` into `bridge_init.cpp`. Tested in `test_bridge_hello_version_and_commit` and `synfig-mcp doctor`. |
| 2 | Release Assets | CI builds Windows + Linux binaries from exact rc3 tag commit with SHA256SUMS and GPL source bundle | **VERIFIED** | Configured in `.github/workflows/bridge-build.yml` on `tags: ['v*']`. Generates `dist/SHA256SUMS.txt`, source bundle, and platform archives. |
| 3 | Release Assets | Test downloading shipped binary from GitHub release and verifying `hello` reports tag commit | **VERIFIED** | Implemented `server/tests/e2e/test_shipped_release.py` querying GitHub release API, extracting binary, and asserting commit match. |
| 4 | Release Assets | Clean-runner smoke test in CI without MSYS2/build dependencies for Windows & Linux | **VERIFIED** | Implemented standalone script `bridge/scripts/clean_runner_smoke.py`. Verified locally with real Studio (all steps PASS: hello, doc.new, layer.add, render.frame). Wired into CI `smoke-test-windows` and `smoke-test-linux`. |
| 5 | Release Assets | Bridge-build run reporting for final tag including xvfb real_studio job | **VERIFIED** | Linux xvfb job and Windows MSYS2 build automated in `.github/workflows/bridge-build.yml`. |
| 6 | Security | Default workspace roots: remove cwd entirely; default = ~/Documents/SynfigMCP only | **VERIFIED** | `config.py` and `handlers.cpp` omit cwd. Verified in `test_cwd_never_included_by_default`, `test_broad_cwd_rejected_in_default_roots`, and `synfig-mcp doctor`. |
| 7 | Security | Bridge opt-in with visible Studio UI indicator (menu item / status) | **VERIFIED** | Added dynamic status label to Synfig Studio Tools menu showing `MCP Bridge: Active (127.0.0.1:%d | Commit: %.7s)` or `MCP Bridge: Off`. Patched in `0001-mcp-bridge-studio-hook.patch`. |
| 8 | Security | `_security_notice` / untrusted-data handling wrapper across all document tools | **VERIFIED** | Shared `wrap_untrusted` helper in `register.py` wraps all document-derived outputs (`scene_tree`, `doc_info`, `anim_keyframe_list`, etc.). Tested against hostile strings in `test_live_hostile_document_strings`. |
| 9 | Security | Path sandbox junction escape rejection (read & write) | **VERIFIED** | Tested in unit (`test_sandbox_rejects_junction_escape`) and live against real Studio (`test_live_path_sandbox_junction_escape`). Directory junctions pointing outside allowed roots are rejected with `SecuritySandboxError`. |
| 10 | Render & Cancel | Python MCP SDK cancellation analysis (server vs client) | **VERIFIED** | Analyzed installed `mcp==2.3.0`. Server dispatcher (`jsonrpc_dispatcher.py:640`) cancels scope on `notifications/cancelled`, but client `session.py:1421` swallows cancelled notifications for v1 parity and suppresses responses. |
| 11 | Render & Cancel | Restructure long renders as asynchronous Job Model | **VERIFIED** | Implemented `RenderJobManager` in `render/jobs.py` (`render_start`, `render_status`, `render_cancel`, `render_result`). Verified multi-frame progress notifications, mid-way cancellation, partial frame cleanup, and typed errors against real Studio in `test_mcp_client_render_jobs_and_cancellation`. |
| 12 | Packaging | Reconcile DLL count from actual packaged files (single source of truth) | **VERIFIED** | Reconciled in `bridge/THIRD_PARTY_LICENSES.md`: exactly 79 total DLLs in `install/bin` (77 third-party MSYS2 DLLs across 49 packages + 2 Synfig core DLLs). |
| 13 | Licensing | Pinned PKGBUILDs, upstream source URLs, and SHA256 in GPL bundle | **VERIFIED** | Generated `bridge/MSYS2_SOURCE_MANIFEST.md` covering all 49 packages. Bundled into `synfig-mcp-gpl-source-v0.7.0-rc3.tar.gz`. Factual FFmpeg buildconf statement retained with legal disclaimer. |
| 14 | Quality | `poe check` and `poe live` green with exact coverage | **VERIFIED** | `poe check`: 57 files formatted, ruff clean, mypy strict clean (57 files), 88 tests passed, 0 failures. `poe live`: 24/24 real_studio tests passed against live Studio in 108.77s. |
| 15 | Roadmap & Docs | Update ROADMAP.md, CHANGELOG.md, docs/install-windows.md, docs/security.md | **VERIFIED** | All documentation aligned with current implementation; open items remain explicitly tracked. |
| Open | User Validation | Clean-VM install test and manual Claude Desktop user test | **OPEN** | Autonomous engineering verification complete; clean-VM test and manual Claude Desktop testing reserved for user before tagging final v1.0 release. |
