# Changelog

All notable changes to `synfig-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0-rc2] - 2026-11-09

### Fixed
- **Linux bridge build**: `auth.cpp` now includes the POSIX headers (`<dirent.h>`, `<signal.h>`, `<cerrno>`) required by stale-token cleanup. The previous `v0.8.0-rc1` source failed to compile on Linux.
- **Visual review failures**: review tools now raise a typed `RenderError` with an actionable message when the renderer produces no image, instead of failing later with `FileNotFoundError`.
- **Hermetic review tests**: contract tests use a fake CLI renderer, so they no longer depend on a locally installed `synfig` binary and pass on every CI platform.

### Added
- **Release automation**: tag releases now generate a complete release body with changelog, install instructions, artifact table, and SHA-256 checksums.
- **GHCR container publishing**: every `v*` tag publishes `ghcr.io/anusara-bemal/synfig-mcp` with semver tags.
- **Strict documentation CI**: MkDocs Material builds the full docs tree on pushes and pull requests.
- **Repository hygiene**: Dependabot updates, issue forms, pull request template, code of conduct, editor config, and corrected MCP registry metadata.
- **User-facing README**: badges, platform requirements, quick start, client configuration for Claude Desktop/Claude Code/Cursor/VS Code, Docker usage, configuration reference, security model, and troubleshooting.

### Changed
- **Version**: bumped to `0.8.0-rc2` across the Python package, bridge build stamp, release tooling, and registry manifest.
- **CI hardening**: locked dependency syncs, explicit workflow permissions, concurrency groups, and job timeouts.
- **Metadata**: `server.json` now targets the official MCP registry schema with the correct owner, version, repository, and OCI package.

## [0.8.0-rc1] - 2026-11-09

### Added
- **Declarative Scene Construction (`scene_build`)**: Atomic single-undo-step construction of complex multi-layer scenes, hierarchies, waypoints, keyframes, and render targets via compact JSON specs. Includes `scene_export_spec` and `scene_summary`.
- **Tool Profiles & Token Budget Architecture**: Configurable tool profiles (`core`, `anim`, `fx`, `rig`, `assets`, `review`, `all`) via `SYNFIG_MCP_PROFILE`. Default `core` profile token footprint reduced by 82.8% to 2,658 cl100k tokens, enforced by CI gate.
- **Visual Review Loop ("Render -> Critique -> Fix")**: Closed-loop visual verification tools (`review_frame`, `review_sequence`, `review_compare`) pairing client vision models with objective mathematical analytics: pure PIL/numpy SSIM, safe-area margin checks, boundary clipping, crushed black and blown highlight luminance clipping, dominant palette extraction, WCAG 2.3.1 photosensitivity strobe detection, per-frame motion deltas, and visual difference heatmaps.
- **Anime Effects Recipe Library**: 14 parameterized visual effect stacks composed exclusively from Synfig native layers: `speed_lines`, `radial_blur_burst`, `impact_frame`, `slash_arc`, `energy_aura`, `vignette`, `film_grain`, `chromatic_aberration`, `camera_shake`, `halftone_screentone`, `cel_shade_rim`, `color_grade_stack`, `limited_animation_timing`, and `transition_whip_pan`.
- **Generic Aesthetic Style Presets**: 5 generic style presets with neutral descriptive identifiers: `shonen_action`, `dark_fantasy`, `supernatural_noir`, `cyber_mecha`, and `retro_anime`.
- **Cut-Out Characters & Storyboard Pipeline**: Cut-out character rigging from parts (`character_rig_from_parts`), standard pose presets (`idle`, `walk`, `run`, `punch`, `jump`), looped motion cycles (`character_motion_apply`), and screenplay-to-animatic shot lists (`storyboard_from_script`). Includes 100% original geometry example in `examples/cutout_character_animatic/`.
- **Hardened Licensed Asset Pipeline**: Open media search and download adapter (Openverse API) with strict licensing policy enforcement (`cc0`, `pdm`, opt-in `by`/`by-sa`, blocking `nd`/`nc`, adult filter), DNS-resolved SSRF protection (blocking loopback, private ranges, link-local, and cloud metadata `169.254.169.254`), hardened SVG DOM sanitizer, raster magic-byte validation, and automated attribution tracking (`ATTRIBUTION.md`).
- **Introspection & Feature Coverage Matrix**: Automated coverage generator and regression CI gate tracking 55 native layer types, 455 parameters, 69 valuenodes, and 13 render targets (`docs/COVERAGE.md`).
- **Comprehensive Documentation**: Complete guides for project scope & IP policy (`docs/scope.md`), system architecture (`docs/architecture.md`), MCP tools API reference (`docs/api.md`), effects recipes & styles (`docs/recipes.md`), and licensed asset pipeline (`docs/assets.md`).
- **Performance Benchmarks**: Sub-6ms latency benchmarks across all 10 core mutating and inspection operations (`scripts/benchmark_latency.py`).

### Changed
- **Server Version**: Bumped to `0.8.0rc1` (`v0.8.0-rc1`).
- **Doctor Command**: Added checks for asset pipeline directory and tool profile token budget compliance.

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
