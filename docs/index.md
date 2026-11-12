# Synfig MCP Documentation

**Model Context Protocol server for Synfig Studio — live canvas automation, headless rendering, and AI-assisted 2D animation.**

[![Server CI](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/server-ci.yml)
[![Bridge Build](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/bridge-build.yml/badge.svg?branch=v1.0.0)](https://github.com/anusara-bemal/synfig-mcp/actions/workflows/bridge-build.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/anusara-bemal/synfig-mcp/blob/v1.0.0/LICENSE)

## Start here

- **[Installation](install.md)** — one command, from source, wheel or container.
- **[Install on Windows](install-windows.md)** — prebuilt patched Studio bundle and Python server.
- **[Build on Windows](build-windows.md)** / **[Build on Linux](build-linux.md)** — compile the native bridge.
- **[Tools API](api.md)** — every tool grouped by profile.
- **[Demo guide](demo-guide.md)** — an end-to-end animation workflow.

## How it works

```mermaid
graph LR
    C["MCP client"] --> S["synfig-mcp<br/>80 tools"]
    S --> L["LiveBackend<br/>patched Studio"]
    S --> H["HeadlessBackend<br/>SIF DOM"]
    L --> B["mcp_bridge<br/>JSON-RPC · token auth"]
    B --> A["synfigapp actions<br/>one undo step"]
    H --> CLI["synfig CLI"]
    A --> PNG["rendered frames"]

    classDef srv fill:#e8f0fe,stroke:#4285f4,color:#111
    classDef st fill:#fef7e0,stroke:#f9ab00,color:#111
    class S srv
    class B,A st
```

## Explore

| Area | Guides |
|---|---|
| Authoring | [Tools API](api.md), [effects and styles](recipes.md), [feature coverage](COVERAGE.md) |
| Review and QA | [Token budget](TOKEN_BUDGET.md), [assets](assets.md) |
| Internals | [Architecture](architecture.md), [protocol](protocol.md), [security](security.md) |
| Operations | [Troubleshooting](troubleshooting.md), [GPL compliance](gpl-compliance.md) |

## Project links

- [Repository](https://github.com/anusara-bemal/synfig-mcp)
- [Releases](https://github.com/anusara-bemal/synfig-mcp/releases)
- [Issues](https://github.com/anusara-bemal/synfig-mcp/issues)
- [Security policy](https://github.com/anusara-bemal/synfig-mcp/blob/v1.0.0/SECURITY.md)

**Author:** ABM · **License:** MIT (server) / GPL-3.0 (native bridge).

Synfig MCP is an independent integration and is not affiliated with the Synfig project.
