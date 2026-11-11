#!/usr/bin/env python3
"""
Verify that the documents produced by the MCP load cleanly in Synfig.

Runs the full mutation matrix of the headless backend against the *real*
``synfig`` binary and reports every document the engine rejects.  Use it as a
pre-flight check or in CI:

    python scripts/verify_synfig_validity.py
    python scripts/verify_synfig_validity.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "server" / "src"))

from synfig_mcp.backend.headless import HeadlessBackend  # noqa: E402
from synfig_mcp.cli.runner import CliRunner  # noqa: E402
from synfig_mcp.errors import SynfigError  # noqa: E402
from synfig_mcp.validation import find_synfig_binary, validate_document  # noqa: E402


async def _check(
    name: str,
    backend: HeadlessBackend,
    doc_id: str,
    tmp: Path,
    binary: Path,
) -> dict[str, Any]:
    """Save the document and validate it with the real engine."""
    sif = tmp / f"{name}.sif"
    await backend.doc_save(doc_id=doc_id, file_path=str(sif))
    result = await validate_document(sif, binary=binary)
    return {
        "case": name,
        "valid": result.valid,
        "exit_code": result.exit_code,
        "errors": result.errors,
        "warnings": result.warnings,
    }


async def run_all(binary: Path) -> list[dict[str, Any]]:
    """Execute the whole verification matrix."""
    runner = CliRunner(binary)
    layer_types = sorted(await runner.get_layers())
    results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="synfig_verify_") as tmp_dir:
        tmp = Path(tmp_dir)

        # 1. Every layer type
        backend = HeadlessBackend(runner=runner)
        doc = await backend.doc_new(width=320, height=240, fps=24.0)
        for layer_type in layer_types:
            await backend.layer_add(doc_id=doc.id, layer_type=layer_type, params={})
        results.append(await _check("all_layer_types", backend, doc.id, tmp, binary))

        # 2. Parameter values
        backend = HeadlessBackend(runner=runner)
        doc = await backend.doc_new(width=320, height=240, fps=24.0)
        layer = await backend.layer_add(doc_id=doc.id, layer_type="circle", params={})
        for param, value in (
            ("radius", {"type": "real", "value": 3.5}),
            ("color", {"type": "color", "r": 0.1, "g": 0.2, "b": 0.3, "a": 1.0}),
            ("origin", {"type": "vector", "x": 1.0, "y": 2.0}),
            ("invert", {"type": "bool", "value": True}),
        ):
            await backend.param_set(
                doc_id=doc.id, layer_id=layer["layer_id"], param_name=param, value=value
            )
        results.append(await _check("parameter_values", backend, doc.id, tmp, binary))

        # 3. Value node export
        backend = HeadlessBackend(runner=runner)
        doc = await backend.doc_new(width=320, height=240, fps=24.0)
        layer = await backend.layer_add(
            doc_id=doc.id, layer_type="circle", params={"radius": {"type": "real", "value": 2.0}}
        )
        await backend.param_export(
            doc_id=doc.id, layer_id=layer["layer_id"], param_name="radius", name="sharedRadius"
        )
        results.append(await _check("param_export", backend, doc.id, tmp, binary))

        # 4. Value node conversions
        for valuenode in ("linear", "add", "subtract", "scale", "absolute", "duplicate"):
            backend = HeadlessBackend(runner=runner)
            doc = await backend.doc_new(width=320, height=240, fps=24.0)
            layer = await backend.layer_add(
                doc_id=doc.id,
                layer_type="circle",
                params={"radius": {"type": "real", "value": 2.0}},
            )
            await backend.param_convert(
                doc_id=doc.id,
                layer_id=layer["layer_id"],
                param_name="radius",
                type=valuenode,
            )
            results.append(
                await _check(f"param_convert_{valuenode}", backend, doc.id, tmp, binary)
            )

        # 5. Waypoints and interpolations
        for interpolation in ("linear", "constant", "halt", "clamped", "auto", "manual"):
            backend = HeadlessBackend(runner=runner)
            doc = await backend.doc_new(width=320, height=240, fps=24.0)
            layer = await backend.layer_add(doc_id=doc.id, layer_type="circle", params={})
            await backend.anim_waypoint_set(
                doc_id=doc.id,
                layer_id=layer["layer_id"],
                param_name="radius",
                time=0.0,
                value={"type": "real", "value": 1.0},
                interpolation_in=interpolation,
                interpolation_out=interpolation,
            )
            results.append(
                await _check(f"waypoint_{interpolation}", backend, doc.id, tmp, binary)
            )

        # 6. Grouping and keyframes
        backend = HeadlessBackend(runner=runner)
        doc = await backend.doc_new(width=320, height=240, fps=24.0)
        first = await backend.layer_add(doc_id=doc.id, layer_type="circle", params={})
        second = await backend.layer_add(doc_id=doc.id, layer_type="rectangle", params={})
        await backend.layer_group(
            doc_id=doc.id, layer_ids=[first["layer_id"], second["layer_id"]], group_name="G1"
        )
        await backend.anim_keyframe_add(doc_id=doc.id, time=0.5, description="pose")
        results.append(await _check("group_and_keyframe", backend, doc.id, tmp, binary))

        # 7. Declarative scene build
        backend = HeadlessBackend(runner=runner)
        doc = await backend.doc_new(width=320, height=240, fps=24.0)
        await backend.scene_build(
            spec={
                "doc_id": doc.id,
                "layers": [
                    {
                        "id": "hero",
                        "type": "circle",
                        "depth": 0,
                        "params": {"radius": {"type": "real", "value": 2.0}},
                        "waypoints": [
                            {
                                "param": "radius",
                                "time": 0.0,
                                "value": {"type": "real", "value": 1.0},
                                "interpolation": "linear",
                            },
                            {
                                "param": "radius",
                                "time": 1.0,
                                "value": {"type": "real", "value": 3.0},
                                "interpolation": "linear",
                            },
                        ],
                    },
                    {"id": "prop", "type": "rectangle", "depth": 1, "params": {}},
                ],
                "groups": [{"id": "bundle", "layer_ids": ["hero", "prop"]}],
            }
        )
        results.append(await _check("scene_build", backend, doc.id, tmp, binary))

    return results


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine readable output")
    args = parser.parse_args()

    binary = find_synfig_binary()
    if binary is None:
        print("Synfig CLI binary not found; cannot validate documents.")
        return 2

    results = await run_all(binary)
    failures = [r for r in results if not r["valid"]]

    if args.json:
        print(json.dumps({"results": results, "failures": len(failures)}, indent=2))
    else:
        for result in results:
            status = "PASS" if result["valid"] else "FAIL"
            print(f"[{status}] {result['case']}")
            for error in result["errors"]:
                print(f"        {error}")
        print(f"\n{len(results) - len(failures)}/{len(results)} cases produce loadable documents")

    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except SynfigError as exc:  # pragma: no cover - defensive
        print(f"Verification aborted: {exc}")
        sys.exit(2)
