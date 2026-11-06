# ADR-0002: Dual-Backend Architecture (LiveBackend vs. HeadlessBackend)

- **Status**: **ACCEPTED**
- **Date**: 2026-11-06

---

## 1. Context

Synfig users operate in two distinct environments:
1. **Interactive Artist Desktop**: An artist running Synfig Studio who wants real-time visual assistance, undoability, and canvas updates.
2. **Automated Server / CI Pipeline**: Automated build servers, headless containers, or users without compiler toolchains who need to generate or render animations via script.

---

## 2. Decision

Expose a **single unified MCP tool surface** backed by two swappable implementations:
1. **LiveBackend**: Drives a running Synfig Studio through the C++ `mcp_bridge` action system.
2. **HeadlessBackend**: Manipulates `.sif` / `.sifz` XML trees with Python `lxml` and invokes the CLI renderer.

The `auto` mode automatically detects whether the Studio bridge is listening on `127.0.0.1:19998` and seamlessly chooses the live path, falling back to headless otherwise.

---

## 3. Consequences

- **Pros**: Clients write one prompt or tool call that works in both live GUI and headless CI.
- **Cons**: Both backends must maintain behavioral parity verified via shared contract tests.
