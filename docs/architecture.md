# Synfig MCP Architecture

## Overview

`synfig-mcp` is a production-grade Model Context Protocol (MCP) server for **Synfig Studio**, an industrial-strength 2D vector animation suite.

Because Synfig Studio exposes no native HTTP or RPC API, `synfig-mcp` bridges LLM agents and animation workflows through a dual-mode engine:
1. **Lossless Direct XML / Container I/O Engine**: Reads, manipulates, and writes `.sif` (plain XML), `.sifz` (gzip-compressed XML), and `.sfg` (ZIP container) documents directly via `lxml`.
2. **Subprocess CLI Runner Engine**: Interfaces asynchronously with the `synfig` CLI binary (`asyncio.create_subprocess_exec`) to query render targets, inspect layer properties, and execute single-frame or full animation renders with streaming progress reporting.

```
+-------------------------------------------------------------+
|                     LLM Client / Host                       |
|   (Claude Desktop, Cursor, VS Code, Claude Code CLI, etc.)   |
+-------------------------------------------------------------+
                              |
                     MCP Protocol (stdio / streamable HTTP)
                              |
+-----------------------------v-------------------------------+
|                       synfig-mcp Core                       |
|                                                             |
|  +--------------------+  +-------------------------------+  |
|  | FastMCP Server     |  | In-Memory Project Registry    |  |
|  | - 102+ Tools       |  | - ProjectSession              |  |
|  | - 5 Resources      |  | - Asyncio Lock per Project    |  |
|  | - 5 Workflow Prompt|  | - Undo/Redo In-Memory History |  |
|  +--------------------+  +-------------------------------+  |
|                                                             |
|  +--------------------+  +-------------------------------+  |
|  | Parameter Codec    |  | Security & Bounds Engine      |  |
|  | - Real, Vector     |  | - Path Traversal Protection   |  |
|  | - Color (#hex/RGBA)|  | - Workspace Jail              |  |
|  | - BLine, Splines   |  | - Limits (Max Pixels/Frames)  |  |
|  | - Unit Conversions |  | - Safe Subprocess Calls       |  |
|  +--------------------+  +-------------------------------+  |
+-----------------------------+-------------------------------+
               |                              |
      Direct File I/O                  Async Subprocess
      (Lossless XML)                   (Non-blocking CLI)
               |                              |
+--------------v--------------+  +------------v---------------+
| Disk Documents              |  | Synfig CLI Binary Engine   |
| - .sif  (XML)               |  | - synfig.exe / synfig      |
| - .sifz (gzip XML)          |  | - Render targets: PNG, GIF |
| - .sfg  (ZIP container)     |  |   MP4 (ffmpeg), sprites    |
+-----------------------------+  +----------------------------+
```

## Core Modules

### 1. Document Subsystem (`synfig_mcp.document`)
- **`model.py` (`ProjectSession`)**: Manages in-memory document state, XML root elements, layer resolution by index or name/description, dirty flags, history snapshots for undo/redo, and atomic transaction locks.
- **`io.py`**: Handles lossless reading and writing of `.sif`, `.sifz`, and `.sfg` files. Preserves all unknown XML tags and attributes, produces valid Synfig XML definitions, and guarantees atomic file replacement using temporary files followed by atomic replace, with automated `.bak` backups when requested.
- **`canvas.py`**: Reads and updates canvas metadata, dimensions, resolution, frame rates, bounding view boxes, gamma values, background colors, and start/end time markers.
- **`layers.py`**: Provides layer manipulation primitives (add, delete, duplicate, reorder, group, ungroup, blend methods, amount/opacity, z-depth).
- **`params.py`**: Comprehensive typed parameter codec for converting friendly Python/LLM representations (hex colors like `#ff8800`, coordinate pairs `[x, y]`, angles, time strings `2s 12f`) into valid Synfig XML parameter tags (`<real>`, `<vector>`, `<color>`, `<bline>`, etc.).
- **`animation.py` & `keyframes.py`**: Waypoint insertion, interpolation modes (`clamped`, `tcb`, `constant`, `ease`, `linear`), keyframe management, timeline manipulation, and dense animation baking.
- **`bones.py` & `exported_values.py`**: Skeleton rigging, bone hierarchy management, parameter value linking, and defs export/use mechanics.

### 2. Command Line Subsystem (`synfig_mcp.cli`)
- **`binary.py`**: Cross-platform auto-detection of the `synfig` CLI binary across Windows (`C:\Program Files\Synfig\bin\synfig.exe`), macOS (`/Applications/SynfigStudio.app/...`), Linux (`/usr/bin/synfig`, Flatpak, AppImage), and environment overrides (`SYNFIG_BIN`).
- **`runner.py`**: Asynchronous subprocess executor using `asyncio.create_subprocess_exec` with timeouts, structured stdout/stderr parsing, and regex progress percentage tracking. Never uses `shell=True`.
- **`render.py`**: Render arguments builder, target verification, format resolution, and video encoding parameters.
- **`info.py`**: Introspects binary versions, installed target modules, and supported layer types at runtime.

### 3. Security Subsystem (`synfig_mcp.security`)
- **`paths.py`**: Path sanitization, workspace sandboxing, traversal protection (`..`), symlink escape rejection, and extension allowlisting.
- **`limits.py`**: Resource boundaries preventing denial of service, memory exhaustion, or disk exhaustion (layer limits, maximum resolution, frame caps, maximum render pixel volume).

### 4. FastMCP Tool Interface (`synfig_mcp.tools`)
Grouped into modular domains:
- **`system_tools.py`**: `synfig_doctor`, `synfig_version`, `list_render_targets`, `list_layer_types`.
- **`project_tools.py`**: Project lifecycle (create, open, save, close, canvas properties, validate, duplicate).
- **`layer_tools.py`**: Layer tree manipulation, ordering, blending, grouping, and toggling.
- **`shape_tools.py`**: High-level vector creation (circles, rectangles, stars, polygons, blines, text, gradients, outlines, regions).
- **`animation_tools.py`**: Keyframe, waypoint, bone, and timeline rigging tools.
- **`render_tools.py`**: Frame and animation rendering, previews, thumbnails, and job status tracking with progress callbacks.
- **`asset_tools.py`**: External asset importing, SVG conversion, and bitmap embedding.
- **`inspect_tools.py`**: Document querying and JSON introspection.
- **`batch_tools.py`**: Atomic batch execution, undo/redo stack, and diffing.

### 5. Resources and Prompts
- **`project_resources.py`**: Exposes MCP resources (`synfig://projects`, `synfig://project/{id}/info`, `synfig://project/{id}/layers`, `synfig://project/{id}/xml`, `synfig://docs/layer-types`).
- **`workflow_prompts.py`**: Pre-defined LLM prompt templates (`create_logo_animation`, `create_explainer_scene`, `rig_character`, `loop_gif`, `fix_broken_project`).
