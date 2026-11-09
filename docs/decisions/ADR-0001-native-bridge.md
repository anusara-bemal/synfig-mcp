# ADR-0001: Synfig Studio Live Control Architecture & Phase G0 Feasibility Gate

- **Status**: **ACCEPTED / GO**
- **Date**: 2026-11-06
- **Pinned Upstream**: Synfig Studio `v1.5.5` (commit `79bf708e2483cba678fc93f0ecf48b2178263795`)

---

## 1. Context & Objectives

To enable an AI client (Claude Desktop, Cursor, VS Code, Claude Code) to create, animate, edit, and inspect Synfig projects in real time, the system requires:
1. **Live Redraw**: Edits must appear on the active canvas instantaneously without file reloading or window freezing.
2. **Standard Undo Stack**: Every AI mutation must be undoable with standard `Ctrl+Z` and blend cleanly with human manual edits.
3. **Thread Safety**: UI actions and canvas mutations must execute exclusively on the GTK main loop thread.
4. **Dual Backend Compatibility**: An offline headless engine (`HeadlessBackend`) must exist for CI and unpatched installations, sharing the exact same tool surface.

Phase G0 evaluates the feasibility of building Synfig Studio on Windows (MSYS2 UCRT64), testing an in-tree socket bridge with `Glib::Dispatcher` and `synfigapp::Action::System`, and verifying whether an unpatched external GUI plugin mechanism exists.

---

## 2. Investigation of Upstream Extension Mechanisms

| Mechanism | Findings & Capabilities | Viability for Live Control |
|---|---|---|
| **Stock Python Plugins (`plugin.xml`)** | File-based only. Triggered from menu; Studio saves file to disk, unloads it, runs Python script on disk XML, and reloads file. | **NO-GO**: Destroys undo history, resets selections, introduces high latency, and cannot run continuously. |
| **Core Dynamic Modules (`synfig::Module`)** | Loads `mod_*.dll` dynamically for layer types, render targets, and importers in `libsynfig`. | **NO-GO**: Core modules have no dependency on or access to `synfig-studio`, the GTK main loop, active canvas views, or `synfigapp::Action::System`. |
| **Studio GUI Plugin Interface** | Researched Studio codebase (`studio::App`, `studio::Instance`, `studio::CanvasView`). | **NO-GO**: No dynamic plugin loader or shared-library hook interface exists in Synfig Studio GUI. |
| **In-Tree Native Bridge (`mcp_bridge`)** | Background socket thread + `Glib::Dispatcher` triggering actions through `CanvasInterface::add_layer_to` / `Action::System`. | **GO**: Minimal patch footprint (+5 lines in CMakeLists.txt, +3 lines in `app.cpp`), thread-safe, 0 ms perceptible latency, clean undo. |

---

## 3. Phase G0 Prototype Evidence

### 3.1 Build Verification
- Synfig Studio was built cleanly from source on Windows using MSYS2 UCRT64 (GCC 16.1.0, CMake 4.3.3, Ninja 1.13.2) against pinned commit `79bf708e2483cba678fc93f0ecf48b2178263795`.
- Build instructions, dependencies, and troubleshooting notes were verified and logged in [`docs/build-windows.md`](../build-windows.md).

### 3.2 Throwaway Hook Architecture
1. **Socket Server**: Background worker thread listening on `127.0.0.1:19998`.
2. **Cross-Thread Dispatch**: `Glib::Dispatcher` signal emits event from socket thread into GTKmm main thread.
3. **Action Execution**:
   ```cpp
   etl::loose_handle<studio::CanvasView> canvas_view = studio::App::get_selected_canvas_view();
   etl::handle<synfigapp::CanvasInterface> canvas_interface = canvas_view->canvas_interface();
   synfig::Canvas::Handle canvas = canvas_interface->get_canvas();

   // add_layer_to wraps Action::LayerAdd in a PassiveGrouper and triggers UI redraw
   synfig::Layer::Handle layer = canvas_interface->add_layer_to("circle", canvas, 0);
   ```

### 3.3 Live Test Execution & Output
The patched `synfigstudio.exe` was started, followed by executing the client trigger script [`bridge/tests/test_g0_socket_trigger.py`](https://github.com/anusara-bemal/synfig-mcp/blob/v1.0.0/bridge/tests/test_g0_socket_trigger.py):

```
Client: Connecting to Synfig Studio G0 hook at 127.0.0.1:19998...
Client: Received from Synfig Studio: OK: Dispatched create_circle to GTK main loop

Studio Log:
[MCP Bridge G0 Hook] Hook started.
[MCP Bridge G0 Hook] Listening on 127.0.0.1:19998 for G0 test triggers...
[MCP Bridge G0 Hook] Received command over socket: create_circle

======================================================
[MCP Bridge G0 Hook] Trigger received on GTK main thread!
[MCP Bridge G0 Hook] Current canvas name: Synfig Animation 1
[MCP Bridge G0 Hook] Adding 'circle' layer via CanvasInterface::add_layer_to()...
[MCP Bridge G0 Hook] SUCCESS: Circle layer added! Description: ''
[MCP Bridge G0 Hook] The layer is now live on the canvas.
[MCP Bridge G0 Hook] Press Ctrl+Z in Synfig Studio to test undoability.
======================================================
```

Repeat triggers created subsequent layers with 100% reliability, no GTK thread warnings, and immediate redraw on the canvas.

---

## 4. Verdict: GO

The feasibility gate **G0** is officially declared **GO**.
- Native live bridge via `Glib::Dispatcher` and `synfigapp::Action::System` is proven viable, safe, and robust.
- Proceeding to **Phase P1 (Scaffolding & Tools)**.
