# ADR-0004: Rendering Pipeline Architecture: Bridge vs CLI Rendering

## Status
Accepted

## Context
Synfig MCP requires capabilities to render individual preview frames, multi-frame image sequences, compiled animations (MP4/GIF), and contact sheets (storyboards).

Two primary architectural approaches exist for rendering:
1. **In-process GTK/Bridge Rendering**: Synfig Studio's C++ process renders directly to a surface or target file via `synfig::Target_Scanline` or `synfig::Context::render`.
2. **Decoupled Out-of-Process Rendering (Saved Temp SIF + CLI)**: The current document state is serialized or saved to a temporary `.sif` file and rendered via the standalone `synfig` CLI tool (`synfig.exe -t ... -o ...`).

## Evidence & Evaluation

| Dimension | In-Process Bridge Rendering | Out-of-Process CLI Rendering |
| :--- | :--- | :--- |
| **GUI Responsiveness** | Blocks GTK main thread if synchronous, causing Windows "(Not Responding)" dialogs during multi-frame renders. | Non-blocking. Runs in separate OS process with independent CPU/core affinity. |
| **Stability & Memory** | Render crashes or memory exhaustion (e.g., heavy blur/particle nodes) crash the entire Synfig Studio editing session. | Process-isolated. If the renderer segfaults, Studio and the user's unsaved edits remain completely intact. |
| **Cancellation** | Difficult to interrupt cleanly in-process without cooperative yield checks inside Synfig's render kernels. | Instant and deterministic: terminating the child process (`token.cancel()`) immediately frees resources. |
| **Latency for Single Frame** | **15.08 ms median / 59.51 ms p95** (Min: 12.30 ms, Max: 328.32 ms, measured via `benchmarks/bench_render.py` across N=20 runs on Windows 11 AMD64; 22.16x faster than CLI). | **334.29 ms median / 398.57 ms p95** (Min: 307.89 ms, Max: 505.39 ms; includes process creation, library linking, and XML parsing). |
| **Caching Integration** | Document memory state must be hashed or tracked manually. | State hash `(SHA256(sif_xml) + params)` can be computed deterministically to key a persistent disk cache. |

### Benchmark Measurement Details & Methodology

Measurements were gathered using `benchmarks/bench_render.py` (20 consecutive runs, 480x270 resolution, default anti-aliasing):

1. **What CLI Rendering Measures**:
   - Executes `synfig.exe -t png -w 480 -h 270 -o <tmp.png> <project.sif>`.
   - Timing starts immediately before `subprocess.run` and stops after process exit.
   - **Included**: Process creation overhead, dynamic library loading (75+ DLLs on Windows), SIF XML parsing, scanline rendering, and encoding/writing the PNG file to disk.

2. **What In-Process Bridge Measures**:
   - Executes JSON-RPC `canvas.render_frame` over local TCP socket to running Synfig Studio (`doc_id="doc_0"`, `width=480`, `height=270`, `target="png"`).
   - Document is already resident in Studio memory.
   - Timing starts immediately before socket send and stops after receiving the completed response.
   - **Included**: Socket transport, JSON parsing, GTK main thread dispatch, `synfig::Context::render` rasterization at identical 480x270 resolution and AA, and writing the PNG file to disk via `synfig::Target`.

3. **Python Render Cache**:
   - The Python `RenderCache` was **explicitly bypassed** during the benchmark. Every iteration measured raw engine rendering rather than cache hits.

4. **Warm-up Outliers**:
   - **In-Process Bridge**: Run 1 registered a 328.32 ms warm-up outlier (initial render target allocation, tile buffer initialization, and shader setup), immediately dropping to 12.30–18.47 ms for all steady-state runs (median 15.08 ms).
   - **CLI**: Run 1 registered a 505.39 ms warm-up outlier (cold process launch and OS file caching), settling into 310–350 ms for subsequent runs (median 334.29 ms).

## Decision
We adopt a **Hybrid Layered Rendering Architecture**:

1. **Fast Single-Frame Inspection**:
   - `render_frame` calls the Live Bridge's `canvas.render_frame` when connected to Synfig Studio, returning an immediate preview frame without full file export.
2. **Sequence, Video, and Batch Contact Sheet Rendering**:
   - Managed by `RenderPipeline` using a persistent deterministic disk cache (`RenderCache`).
   - Keys each frame by `hash(document_state, time, width, height, target)`.
   - Supports async `CancellationToken` for rapid cancellation.
   - If running in Headless mode or batch processing, leverages CLI rendering or frame-by-frame extraction with ffmpeg video compilation.
3. **Cache Storage**:
   - Stored under user cache dir (`~/.cache/synfig-mcp/render` or system temp), retaining up to 500MB with LRU eviction.

## Consequences
- Single-frame preview remains snappy for AI feedback loops.
- Long animations and video renders never freeze or crash the user's interactive Synfig Studio session.
- Cancel and progress notifications are completely responsive.
