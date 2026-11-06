# ADR-0003: Licensing Architecture & Process Boundaries

- **Status**: **ACCEPTED**
- **Date**: 2026-11-06

---

## 1. Context

Synfig Studio and `libsynfig` are licensed under the **GNU General Public License v3.0 (GPL-3.0)**.
`synfig-mcp` consists of:
1. `bridge/`: C++ code compiled into Synfig Studio.
2. `server/`: Standalone Python MCP server communicating with Studio over a local socket.

---

## 2. Decision

- **Bridge (`bridge/`)**: Statically compiled into and directly linking against Synfig Studio / `libsynfigapp`. It is a derivative work under copyright law and is licensed strictly under **GPL-3.0**.
- **Server (`server/`)**: Runs in an independent OS process, communicates solely across a standard network socket (JSON-RPC over TCP / `127.0.0.1`), and does not link against GPL binaries. It is licensed under **MIT** (or Apache-2.0) to allow broad integration with AI tooling, MCP clients, and commercial IDE extensions.

*(Note: This architectural separation follows standard FSF guidance regarding socket-separated processes, but does not constitute formal legal advice.)*
