# synfig-mcp

<p align="center">
  <a href="https://github.com/AnusaraBemal/synfig-mcp/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/AnusaraBemal/synfig-mcp/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/synfig-mcp/"><img alt="PyPI" src="https://img.shields.io/pypi/v/synfig-mcp"></a>
  <img alt="Python versions" src="https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13-blue">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey">
</p>

**synfig-mcp** is a production-grade [Model Context Protocol](https://modelcontextprotocol.io) server that gives AI agents full control over [Synfig Studio](https://www.synfig.org) (2D vector animation): creating and editing `.sif`/`.sifz`/`.sfg` documents, animating parameters with waypoints and keyframes, building rigs with bones, and rendering via the local Synfig CLI — all from MCP tools, resources and prompts. No GUI required.

## Features

- **Full document model** — parses, edits and writes Synfig files with **lossless round-trip** of unknown tags/attributes; atomic saves with `.bak` backups; valid GUIDs; `.sif`, `.sifz` (gzip) and `.sfg` (zip) support
- **100+ tools** — project lifecycle, layers (create/reorder/group/lock), shapes (circle/rect/polygon/star/region/outline/blines), filters (blur/twirl/colorcorrect/halftone/…), animation (waypoints, TCB/linear/clamped interpolation, keyframes, baking), bones & skeleton binding, exported values and parameter linking
- **Real rendering** — renders through your local Synfig binary (`synfig`): single frames, animations (GIF, MP4 via ffmpeg, PNG sequences, sprite sheets), previews, thumbnails; render jobs are non-blocking, concurrency-bounded, cancellable and progress-streamed
- **Friendly inputs** — colors as `#ff8800`, vectors as `[x, y]` in units or pixels (configurable), gradients as `{pos, color}` stops, times as `2s 12f`, degrees for angles
- **Batch operations** — run many tools atomically with automatic rollback on failure; full undo/redo history
- **Security built-in** — all paths confined to a configurable workspace (no traversal/symlink escapes), file-size/resolution/frame/layer caps, no shell execution, sanitized text, stderr-only logging
- **Smart errors** — actionable messages with "did you mean" hints instead of raw stack traces
- **Self-diagnosing** — `synfig_doctor` reports binary path/version, render targets, layer types and config problems

## Demo

Ask your agent:

> Create a 5-second bouncing ball animation with a squash-and-stretch feel, then render it as a GIF.

It will call `create_project` → `add_circle` → `animate_param` (TCB easing) → `add_keyframe` → `render_animation(target="gif")` — and hand you back the file path (and inline PNG frames).

See [`examples/bouncing_ball.py`](examples/bouncing_ball.py) for the same scene driven programmatically, and [`examples/prompts.md`](examples/prompts.md) for more prompts.

## Install

```bash
pip install synfig-mcp
# or
uvx synfig-mcp
```

**Prerequisites:** Python ≥ 3.10 and a Synfig Studio installation (the `synfig` CLI). Synfig is not bundled — install it for your OS:

| OS | How to install Synfig |
|----|-----------------------|
| Windows | Download the installer from [synfig.org](https://www.synfig.org/download/) (defaults to `C:\Program Files\Synfig\bin\synfig.exe`, auto-detected) |
| macOS | `brew install --cask synfigstudio`, or the official `.dmg` from synfig.org |
| Debian/Ubuntu | `sudo apt install synfig synfigstudio` |
| Fedora | `sudo dnf install synfig synfigstudio` |
| Arch | `sudo pacman -S synfigstudio` |
| Flatpak | `flatpak install flathub org.synfig.SynfigStudio` then set `SYNFIG_BIN=/var/lib/flatpak/exports/bin/org.synfig.SynfigStudio` |

Verify the setup with the `synfig_doctor` tool (or `synfig-mcp --version`).

## Client configuration

### Claude Desktop

Add to `claude_desktop_config.json` (see [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json)):

```json
{
  "mcpServers": {
    "synfig": {
      "command": "uvx",
      "args": ["synfig-mcp"],
      "env": {
        "SYNFIG_MCP_WORKSPACE": "D:\\Projects\\synfig-workspace"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add synfig -- uvx synfig-mcp
claude mcp add synfig -e SYNFIG_MCP_WORKSPACE=/path/to/workspace -- uvx synfig-mcp
```

### Cursor

`.cursor/mcp.json` (or global MCP settings):

```json
{
  "mcpServers": {
    "synfig": {
      "command": "uvx",
      "args": ["synfig-mcp"],
      "env": { "SYNFIG_MCP_WORKSPACE": "/path/to/workspace" }
    }
  }
}
```

### VS Code

`.vscode/mcp.json`:

```json
{
  "servers": {
    "synfig": {
      "type": "stdio",
      "command": "uvx",
      "args": ["synfig-mcp"],
      "env": { "SYNFIG_MCP_WORKSPACE": "/path/to/workspace" }
    }
  }
}
```

Transports: stdio is the default; a Streamable HTTP endpoint is available via `synfig-mcp --transport http --host 127.0.0.1 --port 8000`.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNFIG_BIN` | auto-detected | Full path to the `synfig` executable |
| `SYNFIG_MCP_WORKSPACE` | current directory | Only paths inside this directory can be read/written |
| `SYNFIG_MCP_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (stderr only) |
| `SYNFIG_MCP_RENDER_TIMEOUT` | `300` | Seconds before a render is killed |
| `SYNFIG_MCP_MAX_FRAMES` | `20000` | Cap on total frames per render / bake |
| `SYNFIG_MCP_MAX_RESOLUTION` | `8192` | Max width/height in pixels |
| `SYNFIG_MCP_MAX_LAYERS` | `5000` | Max layer count per project |
| `SYNFIG_MCP_MAX_FILE_MB` | `256` | Max project/asset file size |
| `SYNFIG_MCP_UNIT_PX` | `60` | Pixels per Synfig unit (canvas PPU) |
| `SYNFIG_MCP_UNIT_SYSTEM` | `units` | `units` or `pixels` for vector input/output |
| `SYNFIG_MCP_HISTORY_DEPTH` | `50` | Undo/redo depth per open project |
| `SYNFIG_MCP_RENDER_WORKERS` | `2` | Max concurrent renders (bounded queue) |
| `SYNFIG_MCP_AUTOSAVE` | `false` | Auto-save project to disk after each mutation |

An optional `synfig-mcp.toml` in the workspace provides the same keys (e.g. `synfig_bin = "/usr/bin/synfig"`). Precedence: environment variable > `synfig-mcp.toml` > default. See [.env.example](.env.example).

## Tools

<details>
<summary><b>System</b> — synfig_doctor, synfig_version, list_render_targets, list_layer_types</summary>

- `synfig_doctor` — full diagnostic: binary, version, targets, layers, config, problems
- `synfig_version` — binary version string
- `list_render_targets` — render targets available in this build (e.g. png, gif, ffmpeg, bmp, jpeg…)
- `list_layer_types` — layer types available in this build
</details>

<details>
<summary><b>Project</b> — create/open/save/save_as/close/list/info/properties/time-range/fps/image-span/duplicate/validate</summary>

`create_project`, `open_project`, `save_project`, `save_project_as`, `close_project` (optionally `save=true`), `list_open_projects`, `get_project_info`, `set_canvas_properties` (width/height/resolution/view-box/antialias/background/gamma), `set_time_range`, `set_fps`, `set_image_span`, `duplicate_project`, `validate_project`
</details>

<details>
<summary><b>Layers</b> — add/delete/duplicate/move/rename/params/list/group/lock/exclude</summary>

`add_layer` (any type, with did-you-mean hints), `delete_layer`, `duplicate_layer`, `move_layer` (index/offset/z_depth), `rename_layer`, `set_layer_param`, `get_layer_param`, `list_layers` (tree with indices), `get_layer`, `enable_layer`/`disable_layer`, `set_blend_method`, `set_amount`, `set_z_depth`, `group_layers`, `ungroup_layers`, `lock_layer`, `exclude_from_rendering`
</details>

<details>
<summary><b>Shapes & content</b> — circle, rectangle, polygon, star, bline, gradients, text, image</summary>

`add_circle`, `add_rectangle`, `add_polygon`, `add_star`, `add_outline`, `add_advanced_outline`, `add_region`, `add_text`, `add_gradient` (linear/radial/conical/spiral), `add_image`, `add_solid_color`, `add_checkerboard`, `add_noise_gradient`, `add_bline`
</details>

<details>
<summary><b>Filters & effects</b></summary>

`add_blur`, `add_motion_blur`, `add_color_correct`, `add_halftone`, `add_clamp`, `add_stretch`, `add_rotate`, `add_translate`, `add_zoom`, `add_twirl`, `add_bevel`, `add_shade`, `add_radial_blur`, `add_distortions`, `add_duplicate`
</details>

<details>
<summary><b>Animation</b> — waypoints, keyframes, baking, interpolation</summary>

`animate_param`, `add_waypoint`, `remove_waypoint`, `set_interpolation` (constant/linear/clamped/tcb/ease/halt/manual), `add_keyframe`, `remove_keyframe`, `move_keyframe`, `list_keyframes`, `set_time_loop`, `convert_param` (static/animated/linked/exported), `add_time_offset`, `bake_animation`
</details>

<details>
<summary><b>Linking, exported values & bones</b></summary>

`export_value`, `list_exported_values`, `link_params`, `unlink_params`, `create_bone`, `list_bones_tool` (list_bones in docs), `set_bone_param`, `bind_skeleton`
</details>

<details>
<summary><b>Assets</b></summary>

`import_asset`, `list_assets`, `embed_image`, `set_canvas_inline`, `import_svg`
</details>

<details>
<summary><b>Render & export</b></summary>

`render_frame` (PNG, returns the image inline + path), `render_animation` (gif/ffmpeg/png sequence/spritesheet), `render_preview`, `render_thumbnail`, `get_render_status`, `cancel_render` — all with width/height/quality/antialias/time-range/fps parameters
</details>

<details>
<summary><b>Batch & utility</b></summary>

`batch_operations` (atomic, auto-rollback), `undo`, `redo`, `diff_projects`, `export_json_snapshot`, `import_json_snapshot`, `apply_template`
</details>

**MCP resources:** `synfig://projects`, `synfig://project/{id}/info`, `synfig://project/{id}/layers`, `synfig://project/{id}/xml`, `synfig://docs/layer-types`

**MCP prompts:** `create_logo_animation`, `create_explainer_scene`, `rig_character`, `loop_gif`, `fix_broken_project`

Full reference with parameters and examples: [docs/tools-reference.md](docs/tools-reference.md).

## Examples

- [`examples/bouncing_ball.py`](examples/bouncing_ball.py) — builds and renders a complete bouncing-ball animation through the tools
- [`examples/prompts.md`](examples/prompts.md) — natural-language prompts to try
- [`docs/claude-desktop-setup.md`](docs/claude-desktop-setup.md) — step-by-step client setups
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — fixes for common failures
- [`docs/architecture.md`](docs/architecture.md) — how the document model works
- [`docs/sif-format-notes.md`](docs/sif-format-notes.md) — the `.sif` format, verified against Synfig 1.5.5
- [`Dockerfile`](Dockerfile) — slim image with Synfig preinstalled, runs as non-root, mounts `/workspace`

## Security

- Every path argument is resolved and confined to `SYNFIG_MCP_WORKSPACE`; `..` traversal and symlink escapes are rejected
- Renders run without a shell (`asyncio.create_subprocess_exec`); arguments are never string-interpolated
- Project/asset files are size-capped (`SYNFIG_MCP_MAX_FILE_MB`); rendered resolution/frame counts are capped; layer counts are capped on load
- SVG/XML input is parsed with `lxml` (no external entity resolution); text layers are sanitized
- Secrets are never read, logged or written — the server only passes your environment to child processes and never logs it
- Structured logs go to **stderr** only (stdout is reserved for the MCP stdio protocol)
- See [SECURITY.md](SECURITY.md) to report vulnerabilities

## Roadmap

- v0.2 — streaming render progress to clients (MCP progress notifications), richer bake (`bake_animation` with full TCB sampling)
- v0.3 — SFG bundler with external asset collection on save; icon-set generation helpers
- v0.4 — experimental WebP/Lottie target detection when Synfig gains them; batch bake for whole timelines
- Not planned — modifying Synfig itself, or network operations of any kind

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). In short: fork, branch, `pytest`, `ruff check`, `mypy --strict`, PR.

## License

MIT — see [LICENSE](LICENSE).

---

Created and maintained by Anusara Bemal (ABM) — MIT License
