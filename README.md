# Synfig MCP

[![Server CI](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml)
[![Bridge Build](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/bridge-build.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/bridge-build.yml)
[![CodeQL](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/codeql.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/codeql.yml)
[![Website](https://img.shields.io/badge/website-live-1e73be.svg)](https://anusara-bemal.github.io/synfig-mcp/)
[![Docs](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/docs.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/docs.yml)
[![Release](https://img.shields.io/github/v/release/anusara-bemal/synfig-mcp?include_prereleases&sort=semver)](https://github.com/anusara-bemal/synfig-mcp/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-compatible-6f42c1.svg)](https://modelcontextprotocol.io)

**Production-grade Model Context Protocol server for [Synfig Studio](https://www.synfig.org/) — live canvas automation, headless rendering, and AI-assisted 2D animation pipelines.**

**Website:** [anusara-bemal.github.io/synfig-mcp](https://anusara-bemal.github.io/synfig-mcp/) · **Author:** ABM · **License:** MIT (server) / GPL-3.0 (native bridge) · **Tools:** 83 · **Profile:** `all` enabled by default

Synfig MCP connects Claude Desktop, Claude Code, Cursor, VS Code, Codex, and any MCP-compatible client to Synfig Studio. Every edit is applied on the GTK main thread as a regular `synfigapp` action, so it appears instantly on the canvas, takes part in undo/redo, and coexists safely with manual artist work.

---

## Table of contents

- [Why Synfig MCP](#why-synfig-mcp)
- [Architecture](#architecture)
- [How an edit reaches the canvas](#how-an-edit-reaches-the-canvas)
- [Requirements](#requirements)
- [Installation](#installation)
- [Connect an MCP client](#connect-an-mcp-client)
- [Operating modes](#operating-modes)
- [Tool profiles](#tool-profiles)
- [What you can do](#what-you-can-do)
- [Configuration](#configuration)
- [Docker](#docker)
- [Security model](#security-model)
- [How we prove it works](#how-we-prove-it-works)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)

---

## Why Synfig MCP?

| | |
|---|---|
| **Live editing** | Drives a running, patched Synfig Studio through an authenticated local bridge. Every mutation is an undoable Studio action. |
| **Headless fallback** | Works without a GUI through a lossless `.sif` / `.sifz` / `.sfg` engine and the `synfig` CLI. Ideal for CI, containers, and render farms. |
| **Complete surface** | All 83 tools ship enabled: every layer type, parameter type, keyframe, value node, render target, effect recipe and review metric. |
| **Rig sheet to scene** | `rig_sheet_slice` cuts a character sheet into parts, `scene_auto_build` assembles jointed characters, background, props, camera and motion (walk, run, wave, jump, ...) in one call and one undo step. See [`docs/characters.md`](docs/characters.md). |
| **Verified output** | Every generated document is loaded by the *real* Synfig engine in CI — a document the engine rejects never passes. |
| **Visual feedback loop** | Renders frames and returns base64 previews plus objective metrics: SSIM, palette, safe areas, clipping, strobe/photosensitivity, diff heatmaps. |
| **Hardened by default** | Token-authenticated bridge, loopback-only binding, sandboxed file access, SSRF-resistant asset downloads, SVG sanitization. |
| **Reproducible releases** | Cross-platform Studio bundles, a GPL source bundle, Python wheel/sdist, SHA-256 checksums, and a CI-published GHCR container. |

---

## Architecture

```mermaid
graph TB
    subgraph clients["MCP clients"]
        CD["Claude Desktop"]
        CC["Claude Code"]
        CU["Cursor / VS Code / Codex"]
        ANY["Any MCP client"]
    end

    subgraph server["synfig-mcp server (Python · MIT)"]
        TOOLS["83 typed MCP tools<br/>profiles: all · core · anim · fx · rig · assets · review"]
        SCHEMA["Schema introspection<br/>layer types · parameters · value nodes · targets"]
        PIPE["Render pipeline<br/>frame · sequence · video · contact sheet"]
        REVIEW["Visual review<br/>SSIM · palette · clipping · strobe"]
        SANDBOX["Security sandbox<br/>workspace roots · path validation"]
    end

    subgraph backends["Backends (auto-selected)"]
        LIVE["LiveBackend<br/>JSON-RPC over TCP"]
        HEAD["HeadlessBackend<br/>lossless SIF DOM"]
    end

    subgraph studio["Synfig Studio 1.5.5 (patched)"]
        BRIDGE["mcp_bridge<br/>token auth · GTK dispatcher"]
        ACTIONS["synfigapp actions<br/>PassiveGrouper · undo stack"]
        ENGINE["Cobra renderer"]
    end

    CLI["synfig CLI<br/>headless render"]

    CD & CC & CU & ANY -->|stdio / streamable HTTP| TOOLS
    TOOLS --> SCHEMA & PIPE & REVIEW & SANDBOX
    TOOLS --> LIVE & HEAD
    LIVE <-->|127.0.0.1:19998 · token| BRIDGE
    BRIDGE --> ACTIONS --> ENGINE
    HEAD --> CLI
    PIPE --> CLI
    ENGINE --> PNG["PNG frames"]

    classDef server fill:#e8f0fe,stroke:#4285f4,color:#111
    classDef studio fill:#fef7e0,stroke:#f9ab00,color:#111
    classDef ext fill:#e6f4ea,stroke:#34a853,color:#111
    class TOOLS,SCHEMA,PIPE,REVIEW,SANDBOX server
    class BRIDGE,ACTIONS,ENGINE studio
    class CLI ext
```

**Two backends, one tool surface.** `auto` mode picks the live bridge when a patched Studio is listening and falls back to the headless engine otherwise — the model never has to know which one is active, and both are held to the same contract tests.

---

## How an edit reaches the canvas

```mermaid
sequenceDiagram
    autonumber
    participant M as MCP client
    participant S as synfig-mcp
    participant B as mcp_bridge (Studio)
    participant G as GTK main thread
    participant A as Synfig action stack

    M->>S: scene_build(spec)
    S->>S: validate spec · resolve doc_id
    S->>B: JSON-RPC "scene.build"
    B->>B: authenticate session token
    B->>G: marshal to main thread
    G->>A: Action::PassiveGrouper
    G->>A: LayerAdd · ValueDescSet · LayerEncapsulate
    A-->>G: one undo step · canvas redraw
    G-->>B: diff {created, modified, deleted}
    B-->>S: result
    S-->>M: diff + security notice
    M->>M: review_frame() → PNG + metrics
```

- **Thread safety** — the bridge never touches Synfig state from the socket thread; a `Glib::Dispatcher` marshals every request onto the GTK main loop.
- **Undo integrity** — all sub-actions of one tool call are grouped, so `history_undo` reverses exactly one MCP call, even when interleaved with manual edits.
- **Fail loudly** — a rejected action returns a typed error instead of a silent no-op.

---

## Requirements

| Component | Requirement |
|---|---|
| Python server | Python **3.12+**, [`uv`](https://docs.astral.sh/uv/) recommended |
| Live mode | Patched Synfig Studio from the [Releases](https://github.com/anusara-bemal/synfig-mcp/releases) page |
| Windows | Windows 10/11 x64 (prebuilt Studio bundle) |
| Linux | x64 with X11/GTK runtime; prebuilt bundle targets Ubuntu 22.04+ / glibc 2.35+ |
| macOS | Python server and headless mode (no prebuilt Studio bridge yet) |
| Headless rendering | `synfig` CLI on `PATH`, or use the container image (it bundles Synfig) |

> A stock Synfig Studio installation **cannot** use live mode — the native bridge is compiled into the bundled Studio builds.

---

## Installation

### Option A — one command (recommended)

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/anusara-bemal/synfig-mcp/main/scripts/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/anusara-bemal/synfig-mcp/main/scripts/install.ps1 | iex
```

The script installs the server with `uv`, verifies the installation with
`synfig-mcp doctor`, and prints the ready-to-paste client configuration.

### Option B — from source

```bash
git clone https://github.com/anusara-bemal/synfig-mcp.git
cd synfig-mcp
cd server && uv sync --all-extras && cd ..
server/.venv/bin/synfig-mcp doctor      # or server\.venv\Scripts\synfig-mcp.exe doctor
```

### Option C — release wheel

```bash
pip install synfig-mcp
synfig-mcp doctor
```

### Run it

```bash
# stdio transport (default, used by MCP clients)
synfig-mcp

# streamable HTTP (remote / container deployments)
synfig-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --token "$SYNFIG_MCP_TOKEN"

# diagnostics
synfig-mcp doctor
```

```mermaid
graph LR
    A["Install"] --> B{"Studio<br/>running?"}
    B -->|yes| C["LiveBackend<br/>live canvas"]
    B -->|no| D["HeadlessBackend<br/>files + CLI"]
    C --> E["SYNFIG_MCP_BACKEND=auto"]
    D --> E
    E --> F["synfig-mcp doctor<br/>reports the active backend"]

    classDef ok fill:#e6f4ea,stroke:#34a853,color:#111
    class C,D,F ok
```

---

## Connect an MCP client

### Claude Desktop

`claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/Library/Application Support/Claude/` on macOS):

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

### Claude Code

```bash
claude mcp add synfig --env SYNFIG_MCP_PROFILE=all -- synfig-mcp
```

### Cursor

```json
{
  "mcpServers": {
    "synfig": {
      "command": "synfig-mcp",
      "env": { "SYNFIG_MCP_PROFILE": "all", "SYNFIG_MCP_BACKEND": "auto" }
    }
  }
}
```

### VS Code

```json
{
  "servers": {
    "synfig": {
      "type": "stdio",
      "command": "synfig-mcp",
      "env": { "SYNFIG_MCP_PROFILE": "all" }
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

---

## Operating modes

```mermaid
flowchart TD
    START["MCP tool call"] --> MODE{"SYNFIG_MCP_BACKEND"}
    MODE -->|auto| PROBE{"Bridge reachable on<br/>127.0.0.1:19998?"}
    PROBE -->|yes| LIVE["LiveBackend<br/>• real canvas redraw<br/>• undoable actions<br/>• GUI selection"]
    PROBE -->|no| HEAD["HeadlessBackend<br/>• .sif / .sifz / .sfg<br/>• CLI rendering<br/>• no GUI needed"]
    MODE -->|live| LIVE
    MODE -->|headless| HEAD
    LIVE --> RES["Unified result"]
    HEAD --> RES

    classDef live fill:#fef7e0,stroke:#f9ab00,color:#111
    classDef head fill:#e8f0fe,stroke:#4285f4,color:#111
    class LIVE live
    class HEAD head
```

| Mode | Use it when | Needs |
|---|---|---|
| `auto` *(default)* | Always — picks the best available | nothing extra |
| `live` | The artist is in front of Studio | patched Studio + bridge enabled |
| `headless` | CI, containers, batch rendering | `synfig` CLI on `PATH` |

> **Tip:** in live mode open the patched Studio, enable **Tools → MCP Bridge**, and the model works on the canvas you have selected. Never call `doc_new`/`doc_open` unless the user asked for it.

---

## Tool profiles

All 83 tools are exposed by default. Narrow the surface when the client has a tight context budget:

| Profile | Tools | ≈ tokens (cl100k) | Focus |
|---|---:|---:|---|
| `all` *(default)* | 80 | ~20,100 | Everything: documents, layers, parameters, animation, FX, rigging, review, assets |
| `core` | 13 | ~2,980 | Scene build/export, inspection, undo/redo, single-frame render |
| `anim` | 21 | ~5,000 | Keyframes, timeline, waypoints, interpolation |
| `fx` | 25 | ~6,000 | Layer hierarchy, effect recipes, style presets |
| `rig` | 25 | ~4,500 | Cut-out rigging, poses, motion cycles, storyboards, canvases |
| `assets` | 13 | ~2,800 | Licensed asset search, hardened downloads, attribution |
| `review` | 18 | ~5,200 | Frame/sequence/compare review, objective metrics, jobs |

```bash
SYNFIG_MCP_PROFILE=core synfig-mcp
```

---

## What you can do

```mermaid
graph LR
    subgraph build["Build"]
        B1["scene_build<br/>atomic, one undo step"]
        B2["layer_add / group / duplicate<br/>55 layer types"]
        B3["param_set / convert / export / link<br/>value nodes"]
    end
    subgraph animate["Animate"]
        A1["anim_animate_param<br/>bulk waypoints"]
        A2["anim_keyframe_add<br/>timeline poses"]
        A3["param_link<br/>shared values"]
    end
    subgraph fx["Look"]
        F1["recipe_apply<br/>14 effect stacks"]
        F2["style_apply<br/>5 aesthetic presets"]
        F3["character_rig_from_parts<br/>cut-out puppets"]
    end
    subgraph ship["Ship"]
        S1["render_frame / sequence / video"]
        S2["review_frame / compare<br/>metrics + heatmaps"]
        S3["doc_save<br/>.sif / .sifz / .sfg"]
    end
    B1 --> A1 --> F1 --> S1
    B2 --> A2 --> F2 --> S2
    B3 --> A3 --> F3 --> S3

    classDef grp fill:#f8f9fa,stroke:#6c757d,color:#111
    class B1,B2,B3,A1,A2,A3,F1,F2,F3,S1,S2,S3 grp
```

- **Every Synfig layer type** — all 55 discovered from the installed binary (`schema_list_layers`), with real parameter names, value types and writability (`schema_get_layer`).
- **Animation** — keyframes, waypoints, every interpolation mode Synfig understands (`linear`, `constant`, `halt`, `clamped`, `auto`, `manual`).
- **Value nodes** — export a value, link another parameter to it, convert a parameter into a procedural node.
- **Effects** — 14 parameterised recipes (speed lines, impact frames, energy auras, film grain, camera shake…) and 5 neutral style presets.
- **Characters** — cut-out puppet assembly, pose presets, motion cycles, storyboard animatics.
- **Rendering** — single frames, sequences, MP4/GIF video, contact sheets, plus the visual review loop.

Full reference: [`docs/tools.md`](docs/tools.md) (all 83 tools) and [`docs/api.md`](docs/api.md).

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `SYNFIG_MCP_PROFILE` | `all` | Tool profile: `all`, `core`, `anim`, `fx`, `rig`, `assets`, `review` |
| `SYNFIG_MCP_BACKEND` | `auto` | `auto`, `live`, or `headless` |
| `SYNFIG_MCP_HOST` | `127.0.0.1` | Bridge host probed in live mode |
| `SYNFIG_MCP_PORT` | `19998` | Bridge TCP port |
| `SYNFIG_MCP_TOKEN_PATH` | `~/.synfig/mcp_token` | Explicit bridge token path |
| `SYNFIG_MCP_WORKSPACE_ROOTS` | `~/Documents/SynfigMCP` | Directories the server may read/write (path-separated) |
| `SYNFIG_MCP_CLI_PATH` | auto-discovered | Explicit path to the `synfig` binary |

---

## Docker

```bash
docker run -i --rm \
  -v "$PWD:/workspace" \
  -e SYNFIG_MCP_WORKSPACE_ROOTS=/workspace \
  ghcr.io/anusara-bemal/synfig-mcp:latest
```

The image ships the Synfig CLI, so headless rendering works out of the box.

---

## Security model

```mermaid
flowchart TB
    subgraph boundary["Trust boundary"]
        TOKEN["Session token<br/>owner-only ACL, 0600"]
        LOOP["Loopback only<br/>remote binding needs --token"]
        SANDBOX["Workspace sandbox<br/>path + junction escape checks"]
        SSRF["SSRF guard<br/>DNS-resolved IP checks"]
        SVG["SVG sanitiser<br/>DOM allow-list"]
        NOTICE["Untrusted-data notice<br/>on every document-derived reply"]
    end
    IN["MCP client"] --> TOKEN --> LOOP --> SANDBOX
    ASSET["Asset downloads"] --> SSRF --> SVG
    OUT["Replies"] --> NOTICE

    classDef s fill:#fce8e6,stroke:#d93025,color:#111
    class TOKEN,LOOP,SANDBOX,SSRF,SVG,NOTICE s
```

- The bridge binds to `127.0.0.1` only and requires a per-session token stored with owner-only permissions.
- File access is restricted to the configured workspace roots; junctions and symlinks that escape them are rejected.
- Remote binding requires an explicit `--token`.
- Document-derived strings are flagged as untrusted so a model never executes instructions embedded in a layer name.

---

## How we prove it works

Correctness is not asserted, it is **measured against the real Synfig engine**:

```mermaid
graph LR
    T1["Every mutation<br/>→ saved → loaded by<br/>the real synfig binary"]
    T2["Every value node<br/>→ engine-verified"]
    T3["Every render target<br/>→ rendered and inspected"]
    T4["Both backends<br/>→ same contract"]
    T5["Live Studio<br/>→ 37 E2E tests"]
    T1 & T2 & T3 & T4 & T5 --> G["CI gate"]

    classDef gate fill:#e6f4ea,stroke:#34a853,color:#111
    class G gate
```

| Gate | What it proves | Where |
|---|---|---|
| Document validity | Every mutation produces a file the Synfig engine loads with zero errors | `server/tests/contract/test_sif_synfig_validity.py` |
| Render targets | Each output module's real behaviour (frame / sequence / converter / none) | `server/tests/contract/test_render_targets.py` |
| Backend parity | Headless and Studio answer with the same shapes and semantics | `server/tests/contract/test_backend_parity.py` |
| Wire format | Every type the bridge emits validates against the Python models | `server/tests/unit/test_protocol_models.py` |
| Live E2E | The patched Studio performs the work, undoable, in one step | `server/tests/e2e/` |
| Coverage | The published matrix is generated from measured capability | `docs/COVERAGE.md` |

```bash
cd server
uv run poe check        # format, lint, mypy, unit + contract
uv run poe live         # against a real patched Synfig Studio
```

Verify your own installation end to end (starts the MCP server as a client
would, speaks the protocol over stdio and drives the running Studio):

```bash
python scripts/smoke_live.py
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Bridge error 2001: Document not found` | No Studio document is open | Open a document in Studio, or create one with `doc_new` |
| Tools fail with "not connected" | Bridge not enabled | Studio → **Tools → MCP Bridge** |
| `render_frame` writes nothing | Target cannot write a single frame | Use `png`, `jpeg`, `bmp`, `gif`, `ppm`, `yuv420p` |
| "Outside the workspace" | Path not under `SYNFIG_MCP_WORKSPACE_ROOTS` | Add the directory, or use the default `~/Documents/SynfigMCP` |
| Slow first layer | Layer catalogue is being introspected | It is cached afterwards; the first run takes ~20 s |

More: [`docs/troubleshooting.md`](docs/troubleshooting.md).

---

## Development

```bash
cd server
uv sync --all-extras
uv run poe check        # format-check, lint, mypy, tests
uv run poe live         # real Studio end-to-end
uv run poe verify-validity   # load every generated document in the real engine
```

Build the patched Studio:

```bash
bash bridge/scripts/build_windows_msys2.sh    # Windows (MSYS2 UCRT64)
bash bridge/scripts/build_linux.sh            # Linux
```

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/tools.md`](docs/tools.md) | All 83 tools with typed parameters |
| [`docs/api.md`](docs/api.md) | Tool surface per profile |
| [`docs/architecture.md`](docs/architecture.md) | Bridge protocol, threading, undo model |
| [`docs/protocol.md`](docs/protocol.md) | JSON-RPC wire format |
| [`docs/COVERAGE.md`](docs/COVERAGE.md) | Measured feature coverage of the Synfig engine |
| [`docs/recipes.md`](docs/recipes.md) | Effect recipes and style presets |
| [`docs/scope.md`](docs/scope.md) | Scope, non-goals and IP policy |
| [`docs/gpl-compliance.md`](docs/gpl-compliance.md) | GPL obligations of the native bridge |

---

## License

**Author: ABM** — with the synfig-mcp contributors.

- The Python **server** (`server/`) is MIT licensed — see [`LICENSE`](LICENSE).
- The native **bridge** (`bridge/`) is compiled into Synfig Studio and is a
  derivative work, therefore **GPL-3.0** — see [`bridge/GPL_NOTICE.txt`](bridge/GPL_NOTICE.txt)
  and [`docs/gpl-compliance.md`](docs/gpl-compliance.md).
- Synfig Studio itself is © the Synfig Project, GPL-3.0.
