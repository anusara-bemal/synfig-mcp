#!/usr/bin/env python3
"""
Benchmark response latency for synfig-mcp:
Measures latency (mean, median, min, max) for top mutating and inspection calls.
Outputs benchmark report.
"""

import asyncio
import statistics
import tempfile
import time

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.schema.scene_spec import SceneBuildSpec, SceneLayerSpec


async def benchmark() -> None:
    print("=== synfig-mcp Latency Benchmark ===")
    with tempfile.TemporaryDirectory():
        backend = HeadlessBackend()

        # Measure 1: Document Creation
        doc_new_latencies: list[float] = []
        doc_id = ""
        for _ in range(10):
            t0 = time.perf_counter()
            d = await backend.doc_new(1920, 1080, 24.0)
            doc_id = d.id
            doc_new_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 2: Document Info (Read)
        doc_info_latencies: list[float] = []
        for _ in range(20):
            t0 = time.perf_counter()
            await backend.doc_info(doc_id)
            doc_info_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 3: Layer Add
        layer_add_latencies: list[float] = []
        layer_ids: list[str] = []
        for i in range(15):
            t0 = time.perf_counter()
            lyr = await backend.layer_add(doc_id, "circle", description=f"Circle_{i}")
            layer_ids.append(lyr["layer_id"])
            layer_add_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 4: Parameter Set
        param_set_latencies: list[float] = []
        for i, lid in enumerate(layer_ids):
            t0 = time.perf_counter()
            await backend.param_set(doc_id, lid, "radius", 50.0 + i)
            param_set_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 5: Parameter Get
        param_get_latencies: list[float] = []
        for lid in layer_ids:
            t0 = time.perf_counter()
            await backend.param_get(doc_id, lid, "radius")
            param_get_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 6: Declarative Scene Build
        scene_build_latencies: list[float] = []
        spec = SceneBuildSpec(
            doc_id=doc_id,
            width=1280,
            height=720,
            fps=24.0,
            layers=[
                SceneLayerSpec(id="bg", type="solid_color", params={"color": {"type": "color", "value": [0.1, 0.1, 0.2, 1.0]}}),
                SceneLayerSpec(id="orb", type="circle", params={"radius": {"type": "real", "value": 60.0}}),
                SceneLayerSpec(id="fx_noise", type="noise", params={"size": {"type": "vector", "value": [4.0, 4.0]}}),
            ],
        )
        for _ in range(10):
            t0 = time.perf_counter()
            await backend.scene_build(spec)
            scene_build_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 7: Scene Export Spec
        export_spec_latencies: list[float] = []
        for _ in range(15):
            t0 = time.perf_counter()
            await backend.scene_export_spec(doc_id)
            export_spec_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 8: Waypoint Add / Set
        waypoint_latencies: list[float] = []
        for i in range(15):
            t0 = time.perf_counter()
            await backend.anim_waypoint_set(doc_id, "orb", "radius", f"{i*0.1:.1f}s", 50.0 + i)
            waypoint_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 9: Undo Action
        undo_latencies: list[float] = []
        for _ in range(10):
            t0 = time.perf_counter()
            await backend.undo(doc_id)
            undo_latencies.append((time.perf_counter() - t0) * 1000)

        # Measure 10: Redo Action
        redo_latencies: list[float] = []
        for _ in range(10):
            t0 = time.perf_counter()
            await backend.redo(doc_id)
            redo_latencies.append((time.perf_counter() - t0) * 1000)

        benchmarks = [
            ("doc_new", doc_new_latencies),
            ("doc_info", doc_info_latencies),
            ("layer_add", layer_add_latencies),
            ("param_set", param_set_latencies),
            ("param_get", param_get_latencies),
            ("scene_build (declarative)", scene_build_latencies),
            ("scene_export_spec", export_spec_latencies),
            ("anim_waypoint_set", waypoint_latencies),
            ("undo", undo_latencies),
            ("redo", redo_latencies),
        ]

        print(f"\n{'Operation':<28} | {'Mean (ms)':<10} | {'Median (ms)':<11} | {'Min (ms)':<9} | {'Max (ms)':<9}")
        print("-" * 76)
        for name, lats in benchmarks:
            mean = statistics.mean(lats)
            median = statistics.median(lats)
            min_v = min(lats)
            max_v = max(lats)
            print(f"{name:<28} | {mean:>9.2f}  | {median:>10.2f}  | {min_v:>8.2f} | {max_v:>8.2f}")

        print("\nAll 10 core operations benchmarked successfully.")


if __name__ == "__main__":
    asyncio.run(benchmark())
