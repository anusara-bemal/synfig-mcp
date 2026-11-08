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
| **Latency for Single Frame** | Extremely fast: **14.80 ms median / 45.97 ms p95** (measured via `benchmarks/bench_render.py` across 20 runs, 480p preview; 21.88x faster than CLI). | Significantly higher latency: **323.88 ms median / 399.46 ms p95** (due to process launch, SIF XML serialization, and engine startup). |
| **Caching Integration** | Document memory state must be hashed or tracked manually. | State hash `(SHA256(sif_xml) + params)` can be computed deterministically to key a persistent disk cache. |

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
