# Changelog

All notable changes to `synfig-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Corrupt headless documents (critical)**: `param_export` wrote `<defs><valuenode id=…>`, a shape the Synfig engine rejects ("Unknown ID referenced in parameter", "Unexpected element <valuenode>"), so every exported document failed to load. Exported value nodes are now written as `<defs><real id="…"/></defs>` and the `<defs>` section is placed *before* the layers that reference it, exactly as Synfig does.
- **Corrupt headless documents (critical)**: `param_convert` wrote `<linear>` elements without the mandatory `type` attribute, producing documents the engine refused to load ("Missing attribute \"type\" in <linear>"). Conversions now emit the real linkable ValueNode layout (`linear`, `add`, `subtract`, `scale`, `absolute`, `duplicate`, `step`, `range`, `sine`, `cosine`, `time_loop`, `timed_swap`, `composite`) and reject unsupported combinations with an actionable error.
- **Invalid waypoint interpolation**: `anim_waypoint_set` accepted `"tcb"` (documented as valid) and any other string, producing documents Synfig rejects ("Bad value \"tcb\" in <before>"). Interpolations are now validated against the engine's own set (`linear`, `constant`, `halt`, `clamped`, `auto`, `manual`); `tcb` is accepted as a legacy alias of `auto`.
- **Silent value corruption**: `param_set` stringified unsupported values into the parameter (a Python `repr` inside `<string>`), which Synfig then rejected while the tool reported success. Unsupported values now raise a typed error.
- **Live `scene_build` data loss**: the C++ bridge ignored the `groups` and `waypoints` sections of a scene specification, so live builds silently produced a different document than headless builds. Both are now applied inside the same undo step.
- **Invalid parameter values were ignored**: `layer.add` and `scene.build` skipped parameters whose value could not be parsed instead of reporting the problem. They now fail with a typed error.
- **Video rendering could lie**: `render_video` silently wrote GIF bytes into a file named `.mp4` when ffmpeg was unavailable. It now locates ffmpeg (PATH, Synfig bundle, MSYS2) and fails with an actionable message instead of producing a mislabelled file.
- **Wrong layer versions**: layers were written with a hardcoded `version="0.1"`, which made Synfig warn about outdated layers. The real version from `synfig --layer-info` is used now.
- **Unknown layer types were accepted**: the headless backend created layers with arbitrary type names, producing broken documents. It now rejects them with the list of valid types.
- **Advertised ValueNodes that Synfig does not have**: `param_convert` offered `cosine`, `time_loop` and `stepwise`, which are not ValueNode names in Synfig - converting to them produced documents the engine rejected. The names, link layouts and accepted value types now come from the upstream implementation, every conversion is verified against the real engine, and an unsupported conversion raises instead of writing invalid XML.
- **Gradients were unreadable in Studio**: the bridge answered `param.get` with `{"type": "gradient", "value": [...]}` while the documented wire format and the Python model use `cpoints`, so every gradient parameter failed model validation for MCP clients. The bridge now follows the documented format and additionally accepts gradients on `param.set`, which closes the live/headless gap for gradient layers.
- **Render targets were over-claimed**: the coverage matrix reported all 13 Synfig output modules as supported. Only 6 of them write a single image for a single frame; the sequence encoders need a filename pattern, `magick++` needs the optional ImageMagick module and the `null` targets write nothing. The capabilities are now classified, verified by rendering with every target, and `render_frame` rejects a target that cannot produce a frame instead of silently reporting failure.
- **Duplicate layer ids**: every new layer of the same type received the same description (`Circle001`, `Circle002`, ... per type), so the first layer of a type became unreachable for every subsequent operation. Generated descriptions are now unique per canvas.

### Added
- **Value node linking (`param_link`)**: a parameter can now be linked to an exported value node, so independent properties follow one shared value - the "wheel rotation follows the car translation" rig. Implemented with the native `LayerParamConnect` action in the bridge (`<param use="id"/>` in the headless engine) and verified live in Synfig Studio.
- **Synfig validity gate**: `server/tests/contract/test_sif_synfig_validity.py` performs every mutation, saves the document and requires the *real* `synfig` binary to load and render it without a single error. `synfig_mcp.validation` provides the same check programmatically.
- **Live parity gate**: `server/tests/e2e/test_live_scene_build.py` verifies waypoints, groups, single-step undo and engine-loadability of documents saved through the bridge.
- **Truthful introspection**: the schema tools are now backed by the installed Synfig binary. `schema_list_layers` reports all 55 layer types (was 6), `schema_get_layer` reports the real parameters, versions and value types, `schema_list_targets` reports all 13 targets (was 7), `schema_list_renderers` reports all 8 renderers with correct names (was 3, mangled) and `schema_list_valuenodes` reports all 69 value nodes (was 14).
- **Parameter type table**: `server/src/synfig_mcp/schema/param_types.json` holds the value type of all 454 introspected parameters, produced by `scripts/introspect_param_types.py` from the patched Studio, and validated against the binary in CI.
- **Spline authoring**: `param_set` can now write `bline` spline points as a valid `<bline>` element.
- **Parameter value coercion**: plain JSON values are coerced into the type the parameter expects (`[x, y]` becomes a vector, a number becomes an angle/time/integer when required).
- **Documentation freshness gate**: `server/tests/unit/test_tool_docs.py` fails when `docs/tools.md` does not match the registered tool surface.
- **Backend parity gate**: `server/tests/contract/test_backend_parity.py` runs the same operations against the headless engine and the bridge and compares the results; the fake bridge now mirrors the native bridge (same diff action names, same rejection of unknown layer types).
- **Tool surface report**: `synfig-mcp doctor` reports how many MCP tools the active profile exposes.
- **Protocol documentation gate**: `server/tests/unit/test_protocol_docs.py` checks `docs/protocol.md` against the C++ dispatcher, so a method that is documented but not implemented (or the other way round) fails the build. `param.link`, `rig.skeleton_create`, `rig.bone_add` and `rig.bone_bind` are now correctly marked as not implemented instead of "Verified".

### Changed
- **All tools enabled by default**: the default profile is now `all` (73 tools) so a freshly installed server exposes the complete Synfig feature set. `SYNFIG_MCP_PROFILE=core|anim|fx|rig|assets|review` remains available for token-constrained clients.
- **Truthful coverage matrix**: `docs/COVERAGE.md` is generated from measured capability instead of hardcoded claims. It now reports 55/55 layer types, 440/455 writable parameters, 13/13 render targets and - instead of the previously claimed 100% - the 11 value nodes the MCP can actually create.
- **Regenerated tool reference**: `docs/tools.md` documents all 73 tools (was 47) and is generated from the live registry.
- **Corrected documentation**: README, `docs/api.md` and `docs/TOKEN_BUDGET.md` state the real tool counts, token budgets and the new default profile. The built-in guides (`synfig_help`) now show the parameter value format the server actually accepts - the previous examples used a nested spelling that silently produced zero values.

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
