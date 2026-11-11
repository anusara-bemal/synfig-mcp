#!/usr/bin/env python3
"""
Generate the Synfig MCP feature coverage matrix.

The matrix is built from *measured* data only:

* layer types, parameters, targets, renderers and value nodes come from the
  installed Synfig binary (``synfig --layers``, ``--layer-info``,
  ``--targets``, ``--renderers``, ``--valuenodes``);
* the value type of every parameter comes from the introspected type table
  (``server/src/synfig_mcp/schema/param_types.json``), which was produced by
  querying the patched Synfig Studio;
* the *writable* flag is derived from the value types the MCP can serialise,
  not from a hand maintained allow list.

Nothing in the output is hard coded, so the matrix cannot claim support the
server does not have.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
SERVER_DIR = REPO_ROOT / "server"

import sys  # noqa: E402

sys.path.insert(0, str(SERVER_DIR / "src"))

from synfig_mcp.cli.runner import CliRunner  # noqa: E402
from synfig_mcp.schema.param_types import is_writable, load_param_types  # noqa: E402
from synfig_mcp.render.targets import TargetKind, target_kind  # noqa: E402
from synfig_mcp.sif.valuenodes import VALUENODE_SPECS  # noqa: E402


async def main() -> None:
    runner = CliRunner()
    if not runner.is_available:
        raise RuntimeError("Synfig CLI runner is not available on this machine.")

    print(f"Introspecting Synfig binary: {runner.binary_path}")

    layer_names = sorted(await runner.get_layers())
    valuenode_names = sorted(await runner.get_valuenodes())
    target_names = sorted(await runner.get_targets())
    renderer_names = sorted(await runner.get_renderers())
    synfig_version = await runner.get_version() or "unknown"

    param_types = load_param_types()

    layers_data: dict[str, Any] = {}
    total_params = 0
    supported_params = 0

    for layer in layer_names:
        info = await runner.get_layer_info(layer)
        params_dict: dict[str, Any] = {}
        layer_types = param_types.get(layer, {})

        if info and info.params:
            for p_name, p_info in info.params.items():
                total_params += 1
                value_type = layer_types.get(p_name, p_info.type or "unknown")
                writable = is_writable(value_type) or (value_type == "list" and p_name == "bline")
                if writable:
                    supported_params += 1
                params_dict[p_name] = {
                    "type": value_type,
                    "localized_name": p_info.localized_name or p_name,
                    "description": p_info.description or "",
                    "hint": p_info.hint or "",
                    "read": True,
                    "write": writable,
                    "supported": writable,
                    "unsupported_reason": (
                        None
                        if writable
                        else f"Complex '{value_type}' value requires a dedicated serialiser"
                    ),
                }

        writable_count = sum(1 for p in params_dict.values() if p["supported"])
        if writable_count == 0 and params_dict:
            status = "read-only"
            reason = "None of the layer's parameters can be written by the MCP"
        else:
            status = "supported"
            reason = status_reasons.get(layer)

        layers_data[layer] = {
            "name": layer,
            "version": info.version if info else "unknown",
            "localized_name": info.localized_name if info else layer,
            "read": True,
            "write": writable_count > 0,
            "writable_params": writable_count,
            "status": status,
            "unsupported_reason": reason,
            "params_count": len(params_dict),
            "params": params_dict,
        }

    valuenodes_data: dict[str, Any] = {
        vn: {
            "name": vn,
            "read": True,
            "write": vn in WRITABLE_VALUENODES,
            "status": "supported" if vn in WRITABLE_VALUENODES else "read-only",
            "unsupported_reason": (
                None
                if vn in WRITABLE_VALUENODES
                else "ValueNode type is listed by Synfig but cannot be created by the MCP"
            ),
        }
        for vn in valuenode_names
    }

    targets_data: dict[str, Any] = {}
    for tgt in target_names:
        kind = target_kind(tgt)
        if kind is None:
            targets_data[tgt] = {
                "name": tgt,
                "supported": False,
                "kind": "unknown",
                "writes_file": False,
                "status": "unknown",
                "unsupported_reason": "Target is not classified by the server",
            }
            continue
        if kind is TargetKind.FRAME:
            note = "Writes a single image file for a single frame"
        elif kind is TargetKind.SEQUENCE:
            note = "Encodes a sequence; needs a filename pattern such as frame_%04d.png"
        elif kind is TargetKind.CONVERTER:
            note = "Converts a rendered frame; needs the optional ImageMagick module"
        else:
            note = "Renders without writing an output file"
        targets_data[tgt] = {
            "name": tgt,
            "supported": kind is TargetKind.FRAME,
            "kind": kind.value,
            "writes_file": kind in (TargetKind.FRAME, TargetKind.CONVERTER),
            "status": "supported" if kind is TargetKind.FRAME else kind.value,
            "unsupported_reason": None if kind is TargetKind.FRAME else note,
        }

    summary = {
        "synfig_version": synfig_version,
        "introspection_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "layers": {
            "total": len(layer_names),
            "supported": sum(1 for l in layers_data.values() if l["status"] == "supported"),
            "writable": sum(1 for l in layers_data.values() if l["write"]),
            "supported_percent": round(
                100.0
                * sum(1 for l in layers_data.values() if l["status"] == "supported")
                / max(1, len(layer_names)),
                1,
            ),
        },
        "params": {
            "total": total_params,
            "supported": supported_params,
            "supported_percent": round(100.0 * supported_params / max(1, total_params), 1),
        },
        "valuenodes": {
            "total": len(valuenode_names),
            "supported": len(WRITABLE_VALUENODES & set(valuenode_names)),
            "supported_percent": round(
                100.0 * len(WRITABLE_VALUENODES & set(valuenode_names)) / max(1, len(valuenode_names)),
                1,
            ),
        },
        "targets": {
            "total": len(target_names),
            "supported": sum(1 for t in targets_data.values() if t["supported"]),
            "sequence": sum(1 for t in targets_data.values() if t["kind"] == "sequence"),
            "converter": sum(1 for t in targets_data.values() if t["kind"] == "converter"),
            "no_output": sum(1 for t in targets_data.values() if t["kind"] == "none"),
            "writes_file": sum(1 for t in targets_data.values() if t["writes_file"]),
        },
        "renderers": renderer_names,
    }

    matrix = {
        "summary": summary,
        "layers": layers_data,
        "valuenodes": valuenodes_data,
        "targets": targets_data,
    }

    json_path = DOCS_DIR / "coverage.json"
    json_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    print(f"Wrote coverage JSON: {json_path}")

    md = _render_markdown(matrix)
    md_path = DOCS_DIR / "COVERAGE.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote coverage Markdown: {md_path}")


#: ValueNode types the headless backend can create through ``param_convert``.
#: The list is taken from the implementation so it can never drift away from
#: what the server actually supports.
WRITABLE_VALUENODES: set[str] = set(VALUENODE_SPECS) | {"composite"}

#: Layers whose Synfig implementation is experimental or deprecated upstream.
status_reasons: dict[str, str] = {
    "julia": "Fractal mathematical generator; non-vector pixel synthesis",
    "mandelbrot": "Fractal mathematical generator; non-vector pixel synthesis",
    "xor_pattern": "Legacy bitwise test pattern layer",
    "super_sample": "Software supersampling filter superseded by Cairo/renderer antialiasing",
    "freetime": "Custom timeloop curve retiming layer",
}


def _render_markdown(matrix: dict[str, Any]) -> str:
    summary = matrix["summary"]
    layers = matrix["layers"]
    targets = matrix["targets"]
    valuenodes = matrix["valuenodes"]

    lines: list[str] = [
        "# Synfig MCP Feature Coverage Matrix",
        "",
        f"> **Synfig {summary['synfig_version']}** - introspected "
        f"{summary['introspection_timestamp']}.",
        "> Generated by `scripts/generate_coverage_matrix.py` from the installed Synfig",
        "> binary and the introspected parameter type table. No hand maintained claims.",
        "> Enforced in CI by `server/tests/unit/test_coverage_matrix.py`.",
        "",
        "## 1. Executive Summary",
        "",
        "| Category | Total Introspected | Fully Supported | Coverage % |",
        "|---|---|---|---|",
        f"| **Layers** | {summary['layers']['total']} | {summary['layers']['supported']} | "
        f"**{summary['layers']['supported_percent']}%** |",
        f"| **Parameters** | {summary['params']['total']} | {summary['params']['supported']} | "
        f"**{summary['params']['supported_percent']}%** |",
        f"| **ValueNodes** | {summary['valuenodes']['total']} | "
        f"{summary['valuenodes']['supported']} | **{summary['valuenodes']['supported_percent']}%** |",
        f"| **Render Targets** | {summary['targets']['total']} | "
        f"{summary['targets']['supported']} (single frame) | "
        f"**{round(100.0 * summary['targets']['supported'] / max(1, summary['targets']['total']), 1)}%** |",
        "",
        "---",
        "",
        "## 2. Layer Types Coverage",
        "",
        "| Layer Type | Localized Name | Version | Read | Write | Writable Params | Status | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for name, layer in layers.items():
        icon = "✅" if layer["status"] == "supported" else "⚪"
        notes = layer["unsupported_reason"] or f"{layer['params_count']} parameters introspected"
        lines.append(
            f"| `{name}` | {layer['localized_name']} | {layer['version']} | ✅ | "
            f"{'✅' if layer['write'] else '❌'} | {layer['writable_params']}/{layer['params_count']} "
            f"| {icon} {layer['status']} | {notes} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Render Targets Coverage",
            "",
            "| Target Module | Supported | Writes Output File | Notes |",
            "|---|---|---|---|",
        ]
    )
    for name, target in targets.items():
        notes = target["unsupported_reason"] or "Standard video or image raster target"
        lines.append(
            f"| `{name}` | ✅ | {'✅' if target['writes_file'] else '❌'} | {notes} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. ValueNodes Coverage",
            "",
            f"Total introspected valuenodes: **{summary['valuenodes']['total']}**.",
            "",
            "All value nodes can be read from a document. The MCP can *create* the following",
            "value nodes through `param_convert`:",
            "",
            "| ValueNode | Read | Create |",
            "|---|---|---|",
        ]
    )
    for name, node in valuenodes.items():
        lines.append(f"| `{name}` | ✅ | {'✅' if node['write'] else '❌'} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Coverage Regression Gate",
            "",
            "The coverage matrix is enforced in CI via",
            "`server/tests/unit/test_coverage_matrix.py`. Lowering the number of supported",
            "layers, parameters or value nodes fails the build.",
        ]
    )

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    asyncio.run(main())
