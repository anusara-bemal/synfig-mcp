# Changelog

All notable changes to `synfig-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **MCP prompts**: five guided workflows exposed as client slash-commands - `create_animation_scene`, `rig_and_animate_character`, `render_and_review`, `produce_anime_project` and `troubleshoot_connection`. Each walks a model through the correct tool sequence for a common task.
- **MCP resources**: concrete resources at `synfig://index`, `synfig://guide/{topic}`, `synfig://templates/{template}` and `synfig://rubrics/{style}`, plus one enumerable resource per guide topic, scene template and review rubric so `resources/list` is populated.
- **Scene templates**: ready-to-use `scene_build` specs for `bouncing_ball`, `logo_sting` and `lower_third`, readable as MCP resources.
- **Zero-install documentation**: README now leads with `uvx synfig-mcp` and `pipx` install paths and copy-pasteable Claude Desktop, Cursor, VS Code and generic JSON configs.

### Changed
- `LICENSE` is now a clean MIT file so GitHub detects the license correctly; the native bridge's GPL-3.0 notice moved to `LICENSE-BRIDGE`.
- Tool counts in `README.md` and `docs/api.md` corrected to the real total (89 tools).
- The server now advertises `instructions` and registers its prompts and resources on every start.

### Added (continued)
- **Rig sheet to animated scene**: `rig_sheet_slice` finds the parts of a character sheet, returns a numbered preview and writes one transparent PNG per named part. `scene_auto_build` builds a whole shot from a compact spec - background, jointed cut-out characters, props, camera keys, audio, motions - validated up front and applied as one `scene_build` (one round trip, one undo step), with optional save and contact-sheet preview.
- **Real cut-out rigs**: every part gets a rotate joint layer (`<id>_<part>_rot`) nested so that a parent carries its children; hierarchy, pivots and stacking default from body-role names and can be overridden per part. Motion library: walk, run, idle, talk, wave, jump, nod, punch, rest, pose, move, with `move_to` travel.
- `character_pose_apply` accepts explicit joint `angles`; `character_motion_apply` accepts `end_time`, `speed` and `move_to`.

### Fixed
- **Character poses and motions reported success without doing anything**: `character_pose_apply` set an `angle` parameter that the part layers do not have, swallowed the error and listed the bone as applied; `character_motion_apply` "succeeded" on characters that did not exist. Both now write waypoints on real joint layers and fail with a typed error when the character or the joints are missing.
- **Imported character parts used a parameter that does not exist**: image parts were given an `origin` parameter; the `import` layer is placed with `tl` / `br`, which is what the rig writes now.

### Fixed
- **The backend was frozen at startup**: the MCP server chose live or headless once, when the process started. The normal workflow - client first, Studio afterwards - therefore left the server editing an invisible headless document. The auto backend now re-evaluates on every call and switches as soon as Studio appears.
- **Live documents reported a fake size**: the bridge sent only the id, name and path for `doc.list`, so every document looked like 1920x1080 @ 24fps. The real canvas metadata is reported now.
- **Grouped layers were unreachable in headless mode**: the lookup only searched the root canvas, so a layer inside a group returned "Layer not found". It now searches nested canvases like the live bridge.
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
- **Two more wire-format mismatches**: the bridge answered a spline point as `bline_point` and a canvas reference as `canvas`, while the documented format and the Python models use `bline_point_list` and `canvas_ref` - both values failed model validation and were therefore unreadable through the MCP. The bridge now emits the documented spellings, an unset parameter is reported as no value instead of a validation error, and a test compares every type the bridge can emit against the models.
- **The two backends answered `scene_tree` differently**: the live bridge returned a bare layer list with a `desc` key, the headless engine returned the canvas metadata with a `description` key - a client written against one backend broke on the other. Both now report the same document metadata and the same layer keys (`id`, `desc`, `description`, `type`, `active`, `depth`, `params`, `children`), and the live layer id is the description, so a value read from the tree can be used to address the layer.
- **`history_list` and `canvas_list` broke their own contract in Studio**: the bridge answered with the undo/redo *stacks* and with canvas *objects*, while the documented contract (and the headless engine) report the counts and the canvas *paths*. Both tools now answer with the documented shape in either backend.
- **Render targets were over-claimed**: the coverage matrix reported all 13 Synfig output modules as supported. Only 6 of them write a single image for a single frame; the sequence encoders need a filename pattern, `magick++` needs the optional ImageMagick module and the `null` targets write nothing. The capabilities are now classified, verified by rendering with every target, and `render_frame` rejects a target that cannot produce a frame instead of silently reporting failure.
- **Duplicate layer ids**: every new layer of the same type received the same description (`Circle001`, `Circle002`, ... per type), so the first layer of a type became unreachable for every subsequent operation. Generated descriptions are now unique per canvas.

### Added
- **Bone authoring (`rig_bone_add`)**: creates root and child bones with Synfig's own `ValueNodeStaticListInsert` / `ValueDescCreateChildBone` actions - verified live, and the resulting skeleton still loads in the engine.
- **Canvas management**: `canvas_create`, `canvas_rename`, `canvas_delete` and `canvas_set_properties` expose Synfig's sub-canvases (resolution, frame rate, time range, background colour) in both backends.
- **Read-back tools**: `param_list` reports every parameter of a layer with its current value, `anim_waypoint_list` reports the waypoints of an animated parameter.
- **Sound import**: `import_asset` accepts audio files (.wav, .ogg, .mp3, .flac, .au) and creates a Synfig `sound` layer; image formats keep using the `import` layer.
- **15 more value nodes**: `reciprocal`, `derivative`, `reverse`, `vectorlength`, `vectorangle`, `vectorx`, `vectory`, `exp`, `logarithm`, `modulo`, `atan2`, `gradient_rotate`, `map_range`, `stripes` and `twotone` are now creatable - 28 of 69 value nodes, all verified against the Synfig engine.
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

### Performance
- **First layer took 18 seconds**: every `layer_add` re-introspected the layer catalogue, which spawns one `synfig --layer-info` process per layer type (55 processes). The catalogue is now cached in memory and on disk, so the first layer of a session is instant after the first introspection.

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

### Performance
- **First layer took 18 seconds**: every `layer_add` re-introspected the layer catalogue, which spawns one `synfig --layer-info` process per layer type (55 processes). The catalogue is now cached in memory and on disk, so the first layer of a session is instant after the first introspection.

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

### Performance
- **First layer took 18 seconds**: every `layer_add` re-introspected the layer catalogue, which spawns one `synfig --layer-info` process per layer type (55 processes). The catalogue is now cached in memory and on disk, so the first layer of a session is instant after the first introspection.

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

### Performance
- **First layer took 18 seconds**: every `layer_add` re-introspected the layer catalogue, which spawns one `synfig --layer-info` process per layer type (55 processes). The catalogue is now cached in memory and on disk, so the first layer of a session is instant after the first introspection.

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
