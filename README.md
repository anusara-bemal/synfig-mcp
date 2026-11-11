# Synfig MCP

[![Server CI](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml)
[![Bridge Build](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/bridge-build.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/bridge-build.yml)
[![CodeQL](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/codeql.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/codeql.yml)
[![Docs](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/docs.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/docs.yml)
[![Release](https://img.shields.io/github/v/release/anusara-bemal/synfig-mcp?include_prereleases&sort=semver)](https://github.com/anusara-bemal/synfig-mcp/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-compatible-6f42c1.svg)](https://modelcontextprotocol.io)

**Production-grade Model Context Protocol server for [Synfig Studio](https://www.synfig.org/) — live canvas automation, headless rendering, and AI-assisted 2D animation pipelines.**

Synfig MCP connects Claude Desktop, Claude Code, Cursor, VS Code, Codex, and any MCP-compatible client to Synfig Studio. Edits are applied on the GTK main thread as regular `synfigapp` actions, so they appear instantly on the canvas, participate in undo/redo, and coexist safely with manual artist work.

> **Current status: `v0.8.0-rc2` pre-release.** The server API is stable enough for daily use; the tool surface may still evolve before `1.0.0`.

---

## Why Synfig MCP?

| | |
|---|---|
| **Live editing** | Drives a running, patched Synfig Studio through an authenticated local bridge. Every mutation is an undoable Studio action. |
| **Headless fallback** | Works without a GUI through a lossless `.sif` / `.sifz` / `.sfg` engine and the `synfig` CLI. Ideal for CI, containers, and render farms. |
| **Small context footprint** | Tool profiles keep definitions between ~3.0k and ~18.5k tokens; the complete 73-tool surface ships enabled by default and can be narrowed per client. |
| **Visual feedback loop** | Renders frames and returns base64 previews plus objective metrics: SSIM, palette, safe areas, clipping, strobe/photosensitivity, diff heatmaps. |
| **Hardened by default** | Token-authenticated bridge, loopback-only binding, sandboxed file access, SSRF-resistant asset downloads, and SVG sanitization. |
| **Reproducible releases** | Cross-platform Studio bundles, a GPL source bundle, Python wheel/sdist, SHA-256 checksums, and a signed-in-CI GHCR container. |

---

## Contents

- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Connect an MCP client](#connect-an-mcp-client)
- [Operating modes](#operating-modes)
- [Tool profiles](#tool-profiles)
- [Configuration](#configuration)
- [Docker](#docker)
- [Security model](#security-model)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Releases and verification](#releases-and-verification)
- [Documentation](#documentation)
- [License](#license)

---

## Requirements

| Component | Requirement |
|---|---|
| Python server | Python **3.12+**, `uv` recommended |
| Live mode | Patched Synfig Studio from the [Releases](https://github.com/anusara-bemal/synfig-mcp/releases) page |
| Windows | Windows 10/11 x64 (prebuilt Studio bundle) |
| Linux | x64 with X11/GTK runtime; prebuilt Studio bundle targets Ubuntu 22.04+ / glibc 2.35+ |
| macOS | Python server and headless mode only; no prebuilt Studio bridge yet |
| Headless rendering | `synfig` CLI on `PATH`, or the container image (already includes it) |

A stock Synfig Studio installation **cannot** use live mode. The native bridge is compiled into the bundled Studio builds.

---

## Quick start

### 1. Install the Python server

From the latest release wheel:

```bash
uv pip install "synfig-mcp @ https://github.com/anusara-bemal/synfig-mcp/releases/download/v0.8.0-rc2/synfig_mcp-0.8.0rc2-py3-none-any.whl"
```

Or install directly from source:

```bash
git clone https://github.com/anusara-bemal/synfig-mcp.git
cd synfig-mcp
uv pip install "./server[dev]"
```

Verify the installation:

```bash
synfig-mcp doctor
```

`doctor` reports Python version, backend selection, bridge reachability, sandbox roots, and optional CLI availability.

> PyPI publication is prepared in the release workflow and can be enabled with the `PUBLISH_TO_PYPI` repository variable. Until then, use the release wheel or source install — both are fully supported.

### 2. Get the patched Synfig Studio (live mode)

Download the bundle for your platform from [Releases](https://github.com/anusara-bemal/synfig-mcp/releases):

- **Windows:** `synfigstudio-windows-ucrt64-mcp-<sha>.zip`
- **Linux:** `synfigstudio-linux-mcp-<sha>.tar.gz`

Windows:

```powershell
Expand-Archive synfigstudio-windows-ucrt64-mcp-*.zip -DestinationPath .\synfig-mcp-studio
.\synfig-mcp-studio\bin\synfigstudio.exe
```

Linux:

```bash
tar -xzf synfigstudio-linux-mcp-*.tar.gz
cd synfigstudio-linux-mcp-*
LD_LIBRARY_PATH="$PWD/lib" ./bin/synfigstudio
```

Then enable the bridge in **Tools → MCP Bridge**, or launch Studio with `SYNFIG_MCP_ENABLE=1`.

### 3. Run the server

```bash
# stdio transport (default, for MCP clients)
synfig-mcp

# streamable HTTP (for remote/container deployments)
synfig-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --token "$MCP_TOKEN"
```

---

## Connect an MCP client

The server is transport-agnostic. Use stdio for local desktop clients.

### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synfig": {
      "command": "synfig-mcp",
      "env": {
        "SYNFIG_MCP_PROFILE": "all",
        "SYNFIG_MCP_BACKEND": "auto"
      }
    }
  }
}
```

If `synfig-mcp` is not on the GUI application's `PATH`, use an absolute path to the executable or `uvx`:

```json
{
  "mcpServers": {
    "synfig": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/anusara-bemal/synfig-mcp.git#subdirectory=server", "synfig-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add synfig --env SYNFIG_MCP_PROFILE=all -- synfig-mcp
```

### Cursor

Add to `~/.cursor/mcp.json` using the same `mcpServers` block shown above.

### VS Code

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "synfig": {
      "type": "stdio",
      "command": "synfig-mcp",
      "env": {
        "SYNFIG_MCP_PROFILE": "all"
      }
    }
  }
}
```

### Any MCP client (generic JSON)

```json
{
  "mcpServers": {
    "synfig": {
      "command": "/absolute/path/to/synfig-mcp",
      "args": [],
      "env": {
        "SYNFIG_MCP_PROFILE": "all",
        "SYNFIG_MCP_BACKEND": "auto",
        "SYNFIG_MCP_WORKSPACE_ROOTS": "/home/me/Documents/SynfigMCP"
      }
    }
  }
}
```

After connecting, call `health_check` to confirm the active backend and `synfig_help` for in-client guidance.

---

## Operating modes

| Mode | Backend | When to use |
|---|---|---|
| `auto` (default) | Live if reachable, otherwise headless | Normal desktop use |
| `live` | Patched Synfig Studio bridge | Interactive editing, canvas previews, undo/redo |
| `headless` | Pure-Python SIF engine + `synfig` CLI | Servers, CI, containers, render farms |

Live mode uses JSON-RPC over TCP on `127.0.0.1:19998` with a per-session bearer token written to `~/.synfig/mcp_token`. The bridge is opt-in and loopback-only.

Headless mode never needs a GUI. It is fully lossless for SIF documents and delegates raster/video rendering to the `synfig` CLI.

---

## Tool profiles

All 74 tools are exposed by default. Set `SYNFIG_MCP_PROFILE` to expose only the tools a workflow needs.

| Profile | Tools | Approx. tokens (cl100k) | Focus |
|---|---:|---:|---|
| `all` (default) | 74 | ~18,500 | Complete Synfig surface: documents, layers, parameters, animation, FX, rigging, review, assets |
| `core` | 13 | ~2,970 | Scene build/export, inspection, undo/redo, single-frame render |
| `anim` | 19 | ~4,600 | Keyframes, timeline, waypoints, interpolation |
| `fx` | 24 | ~5,600 | Layer hierarchy, effects recipes, style presets |
| `rig` | 17 | ~3,800 | Cut-out rigging, poses, motion cycles, storyboards |
| `assets` | 12 | ~2,700 | Licensed asset search, hardened downloads, attribution |
| `review` | 18 | ~4,900 | Frame/sequence/compare review, objective metrics, jobs |

Examples:

- **Scene assembly:** `core`
- **Rigging a character:** `rig` + `core`
- **Visual QA loop:** `review` + `core`
- **Power-user agent:** `all`

See the [full tool reference](docs/api.md) and the generated [coverage matrix](docs/COVERAGE.md).

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `SYNFIG_MCP_PROFILE` | `all` | Tool profile: `all` (complete surface), `core`, `anim`, `fx`, `rig`, `assets`, `review` |
| `SYNFIG_MCP_BACKEND` | `auto` | `auto`, `live`, or `headless` |
| `SYNFIG_MCP_HOST` | `127.0.0.1` | Bridge host probed by live mode |
| `SYNFIG_MCP_PORT` | `19998` | Bridge TCP port |
| `SYNFIG_MCP_TOKEN_PATH` | `~/.synfig/mcp_token` | Explicit bridge token path |
| `SYNFIG_MCP_WORKSPACE_ROOTS` | `~/Documents/SynfigMCP` | Sandbox roots; `os.pathsep` or comma separated |
| `SYNFIG_MCP_ENABLE` | unset | Set `1` to auto-enable the bridge in patched Studio |
| `SYNFIG_MCP_HTTP_TOKEN` | unset | Bearer token for streamable HTTP transport |

The working directory is **never** an allowed workspace root by default. Add project directories explicitly.

---

## Docker

The container ships the headless backend and the `synfig` CLI.

```bash
docker run --rm -i \
  -v "$PWD/workspace:/workspace" \
  -e SYNFIG_MCP_WORKSPACE_ROOTS=/workspace \
  ghcr.io/anusara-bemal/synfig-mcp:0.8.0-rc2
```

Build locally:

```bash
docker build -t synfig-mcp .
docker run --rm -i -v "$PWD/workspace:/workspace" \
  -e SYNFIG_MCP_WORKSPACE_ROOTS=/workspace synfig-mcp
```

HTTP mode:

```bash
docker run --rm -p 8000:8000 \
  -e SYNFIG_MCP_WORKSPACE_ROOTS=/workspace \
  ghcr.io/anusara-bemal/synfig-mcp:0.8.0-rc2 \
  --transport streamable-http --host 0.0.0.0 --port 8000 --token "$MCP_TOKEN"
```

The image runs as UID 1000. Make mounted directories writable by that user or pass `--user "$(id -u):$(id -g)"`.

---

## Security model

- **Loopback-only bridge.** Live mode binds to `127.0.0.1` and refuses non-loopback interfaces unless an HTTP token is configured.
- **Session tokens.** Studio writes a random token to a user-only file; every bridge request is authenticated.
- **Sandboxed files.** Read/write operations are resolved and constrained to explicit workspace roots, including symlink/junction checks.
- **Untrusted input handling.** Document-derived strings are wrapped with security notices, SVG is DOM-sanitized, raster downloads validate magic bytes, and remote asset URLs are DNS-resolved and blocked against loopback/private/link-local/metadata ranges.
- **No shell execution from tool arguments.** Renders invoke the Synfig CLI with fixed argument shapes.

See [docs/security.md](docs/security.md) and [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

> Never bind HTTP mode to `0.0.0.0` without `--token`, a reverse proxy, and network access controls.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection refused` on port 19998 | Start the patched Studio build and enable **Tools → MCP Bridge**, or set `SYNFIG_MCP_BACKEND=headless`. |
| Client reports JSON parse errors | Ensure nothing writes to stdout. `synfig-mcp` logs to stderr only. |
| `RenderError: Frame render produced no output` | Install the `synfig` CLI, add it to `PATH`, or switch to the container image. |
| File access denied | Add the directory to `SYNFIG_MCP_WORKSPACE_ROOTS`; `cwd` is intentionally not allowed. |
| Studio bundle won't start on Linux | Export `LD_LIBRARY_PATH` to the bundle's `lib` directory and run under X11. |
| Missing settings/plugin warnings on first run | Expected on a clean profile; Synfig creates `~/Synfig` on first launch. |

More fixes: [docs/troubleshooting.md](docs/troubleshooting.md).

---

## Development

```bash
git clone https://github.com/anusara-bemal/synfig-mcp.git
cd synfig-mcp/server
uv sync --locked --all-extras

uv run poe check     # ruff format-check + ruff lint + mypy --strict + pytest
uv run poe live      # real-Studio end-to-end tests (requires patched Studio)
```

Repository tasks from the root:

```bash
uv run poe check
uv run poe test
```

CI runs the same suite on Ubuntu, macOS, and Windows with Python 3.12 and 3.13, plus Docker smoke tests, CodeQL, and a strict documentation build.

Contribution guidelines, commit conventions, and the release checklist live in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Releases and verification

Every `v*` tag builds and publishes:

- patched Synfig Studio bundles for Windows (UCRT64) and Linux,
- a source bundle for GPL compliance,
- the Python wheel and sdist,
- `SHA256SUMS.txt` and per-asset checksums,
- a GHCR container image at `ghcr.io/anusara-bemal/synfig-mcp`.

A tag push is the only event that publishes a release; branch pushes run build and smoke tests but intentionally skip publishing. This keeps every published artifact tied to an immutable tag.

Verify a download:

```bash
sha256sum -c SHA256SUMS.txt
```

Smoke-test a published Windows binary on a clean runner:

```bash
python bridge/scripts/clean_runner_smoke.py path/to/synfigstudio.exe
```

---

## Documentation

| Guide | Description |
|---|---|
| [Tools API](docs/api.md) | Every tool, grouped by profile |
| [Architecture](docs/architecture.md) | Bridge, backends, threading, and data flow |
| [Protocol](docs/protocol.md) | JSON-RPC bridge contract |
| [Security](docs/security.md) | Threat model and hardening |
| [Coverage](docs/COVERAGE.md) | Native layer, parameter, valuenode, and target coverage |
| [Recipes](docs/recipes.md) | 14 native effects and 5 style presets |
| [Assets](docs/assets.md) | Licensed asset pipeline and attribution |
| [Token budget](docs/TOKEN_BUDGET.md) | Profile measurements and optimization |
| [Build: Windows](docs/build-windows.md) / [Linux](docs/build-linux.md) | Compile the patched Studio |
| [Troubleshooting](docs/troubleshooting.md) | Common failures and verified fixes |
| [GPL compliance](docs/gpl-compliance.md) | Source availability and third-party licenses |

---

## License

- `server/` — **MIT License** ([LICENSE](LICENSE)).
- `bridge/` and patched Studio binaries — **GPL-3.0-or-later**, because they are linked with Synfig Studio. The complete corresponding source is published with every binary release.
- Third-party components retain their upstream licenses; see [bridge/THIRD_PARTY_LICENSES.md](bridge/THIRD_PARTY_LICENSES.md).

Synfig Studio is a trademark of the Synfig project. This project is an independent integration and is not affiliated with or endorsed by the Synfig maintainers.

---

<p align="center">
  Built for artists, animators, and agents that need real vector animation tools.
</p>
