# Changelog

All notable changes to `synfig-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0-rc3] - 2026-11-08

### Added
- **Build-Time Git Commit SHA Injection**: Real commit SHA injected into `bridge_init.cpp`, reported in `hello` response, `synfig-mcp doctor`, About dialog, and Studio main menu.
- **Visible Studio UI Indicator**: Dynamic status indicator in Synfig Studio Tools menu showing bridge status, port, and commit SHA (`MCP Bridge: Active (127.0.0.1:19998 | Commit: ...)`) with checkmark when running, or `MCP Bridge: Off`.
- **Render Job Model**: Asynchronous render management tools (`render_start`, `render_status`, `render_cancel`, `render_result`) decoupling long rendering operations from client JSON-RPC request lifetimes.
- **Untrusted Document String Wrapper**: Standardized `wrap_untrusted` helper attaching `_security_notice` to all tools outputting document-derived strings (`scene_tree`, `doc_info`, `anim_keyframe_list`, `param_get`, `selection_get`, `history_list`).
- **Junction & Symlink Sandbox Hardening**: Filesystem sandbox resolves directory junctions and symlinks, rejecting read/write escapes outside allowed roots.
- **Clean Runner Smoke Test**: Standalone automated smoke test (`bridge/scripts/clean_runner_smoke.py`) verifying app launch, DLL resolution, bridge auth, `doc.new`, `layer.add`, and `render.frame` without MSYS2/build dependencies on Windows and Linux runners.
- **MSYS2 Source Manifest**: Complete manifest (`bridge/MSYS2_SOURCE_MANIFEST.md`) detailing pinned versions, upstream source URLs, and MSYS2 PKGBUILD build recipes for all 49 bundled packages.
- **Shipped Release Verification Test**: Added `server/tests/e2e/test_shipped_release.py` to verify shipped binary releases against GitHub release assets.

### Changed
- **Default Workspace Root**: Scoped exclusively to `~/Documents/SynfigMCP`. Working directory (`cwd`) completely removed from default allowed roots to prevent leaking arbitrary directories.
- **Opt-in Bridge Default**: Bridge defaults to OFF; opt-in via Studio menu toggle, persisted configuration `~/.synfig/mcp_enabled`, or `SYNFIG_MCP_ENABLE=1`.
- **Packaging Reconciliation**: Single source of truth for all 79 packaged DLLs (77 third-party MSYS2 DLLs + 2 Synfig core DLLs).

## [0.7.0-rc2] - 2026-11-08
- Versioning and packaging verification pre-release.

## [0.7.0-rc1] - 2026-11-08
- Initial release candidate for native bridge and headless MCP server.

## [0.1.0] - 2026-11-06
- Initial feasibility prototype and dual-backend monorepo scaffold.
