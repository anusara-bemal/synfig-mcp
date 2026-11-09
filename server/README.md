# synfig-mcp

[![Server CI](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml)
[![PyPI](https://img.shields.io/badge/pypi-synfig--mcp-blue.svg)](https://pypi.org/project/synfig-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/anusara-bemal/synfig-mcp/blob/v1.0.0/LICENSE)

**Model Context Protocol server for Synfig Studio — live canvas automation with a headless fallback.**

This package provides the Python MCP server. It can drive a running patched Synfig Studio over an authenticated local bridge, or operate entirely headless using the `synfig` CLI.

Full documentation, screenshots, client setup, and prebuilt Studio bundles: **[github.com/anusara-bemal/synfig-mcp](https://github.com/anusara-bemal/synfig-mcp)**.

## Install

```bash
uv pip install "synfig-mcp @ https://github.com/anusara-bemal/synfig-mcp/releases/download/v0.8.0-rc2/synfig_mcp-0.8.0rc2-py3-none-any.whl"
```

Or from source:

```bash
uv pip install "git+https://github.com/anusara-bemal/synfig-mcp.git#subdirectory=server"
```

## Use

```bash
synfig-mcp doctor
synfig-mcp
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "synfig": {
      "command": "synfig-mcp",
      "env": {
        "SYNFIG_MCP_PROFILE": "core",
        "SYNFIG_MCP_BACKEND": "auto"
      }
    }
  }
}
```

## Operating modes

| Mode | Backend | Use case |
|---|---|---|
| `auto` | Live if reachable, otherwise headless | Desktop |
| `live` | Patched Synfig Studio | Interactive editing with undo/redo |
| `headless` | SIF engine + `synfig` CLI | Servers, CI, containers |

## Tool profiles

`SYNFIG_MCP_PROFILE` selects the exposed tools:

| Profile | Tools | Approx. tokens |
|---|---:|---:|
| `core` (default) | 12 | ~2,658 |
| `anim` | 14 | ~3,800 |
| `fx` | 21 | ~4,200 |
| `rig` | 12 | ~2,800 |
| `assets` | 10 | ~1,900 |
| `review` | 15 | ~3,900 |
| `all` | 56 | ~18,500 |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SYNFIG_MCP_PROFILE` | `core` | Tool profile |
| `SYNFIG_MCP_BACKEND` | `auto` | `auto`, `live`, or `headless` |
| `SYNFIG_MCP_HOST` / `SYNFIG_MCP_PORT` | `127.0.0.1` / `19998` | Live bridge endpoint |
| `SYNFIG_MCP_TOKEN_PATH` | `~/.synfig/mcp_token` | Bridge token |
| `SYNFIG_MCP_WORKSPACE_ROOTS` | `~/Documents/SynfigMCP` | Sandbox roots |

## Development

```bash
cd server
uv sync --locked --all-extras
uv run poe check
```

## License

The Python server is MIT licensed. The native bridge and patched Studio binaries are GPL-3.0-or-later. See [LICENSE](https://github.com/anusara-bemal/synfig-mcp/blob/v1.0.0/LICENSE) and [docs/gpl-compliance.md](https://github.com/anusara-bemal/synfig-mcp/blob/v1.0.0/docs/gpl-compliance.md).
