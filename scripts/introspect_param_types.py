#!/usr/bin/env python3
"""
Introspect the *live* Synfig Studio to learn the value type of every layer parameter.

The ``synfig --layer-info`` output lists parameter names and descriptions but not
their value types.  The patched Studio does know them: every parameter carries a
typed value which the MCP bridge reports through ``param.get``.

This script launches the patched Studio, creates one layer per layer type, reads
back the type of every parameter and writes the result to
``server/src/synfig_mcp/schema/param_types.json``.

Usage:
    python scripts/introspect_param_types.py [--studio PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "server" / "src"))

from synfig_mcp.cli.runner import CliRunner  # noqa: E402
from synfig_mcp.protocol.client import BridgeClient  # noqa: E402

DEFAULT_STUDIO = REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe"
TEST_PORT = 19993


def studio_env(**overrides: str) -> dict[str, str]:
    """Environment able to launch the installed Studio binary."""
    env = os.environ.copy()
    if not DEFAULT_STUDIO.name.endswith(".exe"):
        root = DEFAULT_STUDIO.parent.parent
        lib_dir = str(root / "lib")
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing}" if existing else lib_dir
        env["SYNFIG_MODULE_DIR"] = str(root / "lib" / "synfig" / "modules")
        env.setdefault("SYNFIG_DATA_DIR", str(root / "share"))
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env.update(overrides)
    return env


async def introspect(studio: Path) -> dict[str, dict[str, str]]:
    """Collect {layer_type: {param_name: value_type}} from the live Studio."""
    runner = CliRunner()
    layer_names = sorted(await runner.get_layers())

    env = studio_env(
        SYNFIG_MCP_ENABLE="1",
        SYNFIG_MCP_PORT=str(TEST_PORT),
        SYNFIG_DISABLE_AUTO_RECOVERY="1",
        SYNFIG_DISABLE_AUTO_SAVE="1",
    )

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    if token_dir.is_dir():
        for tf in token_dir.glob("mcp_token*"):
            with contextlib.suppress(Exception):
                tf.unlink()

    with tempfile.TemporaryDirectory(prefix="synfig_introspect_") as tmp:
        log_path = Path(tmp) / "studio.log"
        with open(log_path, "w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                [str(studio)],
                env=env,
                stdout=log_file,
                stderr=log_file,
                cwd=str(studio.parent),
            )
        client: BridgeClient | None = None
        try:
            token = ""
            for _ in range(40):
                if token_dir.is_dir():
                    for tf in token_dir.glob("mcp_token*"):
                        if tf.is_file() and tf.stat().st_size > 0:
                            with contextlib.suppress(Exception):
                                token = tf.read_text(encoding="utf-8").strip()
                            if token:
                                break
                if token:
                    break
                await asyncio.sleep(0.5)
            if not token:
                raise RuntimeError("Studio did not create a session token")

            client = BridgeClient(
                host="127.0.0.1", port=TEST_PORT, token=token, default_timeout=20.0
            )
            for _ in range(25):
                try:
                    await client.connect()
                    break
                except Exception:
                    await asyncio.sleep(0.5)
            else:
                raise RuntimeError("Could not connect to the MCP bridge")

            for _ in range(20):
                docs = await client.call("doc.list")
                if docs:
                    break
                await asyncio.sleep(0.5)

            doc_id = "doc_0"
            result: dict[str, dict[str, str]] = {}

            for layer_type in layer_names:
                info = await runner.get_layer_info(layer_type)
                if info is None or not info.params:
                    result[layer_type] = {}
                    continue

                add = await client.call(
                    "layer.add",
                    {"doc_id": doc_id, "layer_type": layer_type, "description": "introspect"},
                )
                layer_id = add.get("layer_id") if isinstance(add, dict) else None
                if not layer_id:
                    result[layer_type] = {}
                    continue

                types: dict[str, str] = {}
                for param_name in info.params:
                    try:
                        value = await client.call(
                            "param.get",
                            {"doc_id": doc_id, "layer_id": layer_id, "param_name": param_name},
                        )
                    except Exception:
                        continue
                    if isinstance(value, dict):
                        typed = value.get("value")
                        if isinstance(typed, dict):
                            vtype = typed.get("type")
                            if isinstance(vtype, str) and vtype not in ("any", "unknown"):
                                types[param_name] = vtype
                result[layer_type] = types

                with contextlib.suppress(Exception):
                    await client.call(
                        "layer.remove", {"doc_id": doc_id, "layer_id": layer_id}
                    )
                print(f"{layer_type:24s} {len(types)}/{len(info.params)} params typed")

            return result
        finally:
            if client is not None and client.is_connected:
                await client.close()
            proc.terminate()
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studio", default=str(DEFAULT_STUDIO))
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "server" / "src" / "synfig_mcp" / "schema" / "param_types.json"),
    )
    args = parser.parse_args()

    studio = Path(args.studio)
    if not studio.exists():
        print(f"Studio binary not found: {studio}")
        return 2

    data = asyncio.run(introspect(studio))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    total = sum(len(v) for v in data.values())
    print(f"Wrote {total} parameter types for {len(data)} layer types to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
