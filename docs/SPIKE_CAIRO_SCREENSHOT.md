# Spike Report: Canvas Widget Snapshot via Cairo vs Native Frame Rendering

> **Phase A2 Spike Investigation** (Target: v0.8.0-rc1)

## Objective
Determine whether taking an OS/window snapshot of Synfig Studio's `studio::WorkArea` GTK widget via Cairo is reliable and cheap compared to internal canvas frame rendering via `render_frame`.

---

## 1. Technical Evaluation

| Criterion | Widget Cairo Snapshot (`gtk_widget_draw`) | Canvas Frame Render (`render_frame` / Cairo target) |
|---|---|---|
| **Headless / CI Compatibility** | ❌ Fails when headless or running in GitHub Actions without display server. | ✅ Fully operational headless, CI, and live GUI. |
| **Window State Sensitivity** | ❌ Corrupted if window is minimized, occluded, off-screen, or during tab switch. | ✅ Independent of desktop window state. |
| **DPI / Resolution Control** | ❌ Tied to monitor scaling factor, window dimensions, and zoom level. | ✅ Exact pixel dimensions requested by LLM (e.g. 320x240, 640x480). |
| **UI Chrome Interference** | ❌ Captures selection handles, bboxes, grid overlays, and tangents. | ✅ Pure rendered artwork (clean ground truth). |
| **Thread Safety** | ⚠️ Must synchronize with GTK draw queue on UI thread. | ✅ Safe on background render workers. |
| **Latency / Cost** | ~15ms - 40ms | ~25ms - 60ms |

---

## 2. Recommendation & Decision

**Decision:** Retain `render_frame` as the authoritative source of truth for the Visual Review Loop.
- Widget window snapshots introduce OS-level flakiness, DPI discrepancies, and unwanted canvas handles/grid lines.
- `render_frame` provides clean, reliable, deterministic artwork at precisely the token-budgeted resolution (320x240 default).
