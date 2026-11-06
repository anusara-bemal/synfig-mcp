"""
End-to-end integration tests for Live Synfig Studio MCP Bridge (Mutating Path & Undo System).
Validates layer.add, param.set, history.undo, history.redo, anim.time_set,
anim.keyframe_add, layer.reorder, selection.set, and layer.remove.
"""

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from synfig_mcp.protocol.client import BridgeClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BIN_PATH = REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe"
SAMPLE_SIF = REPO_ROOT / "server" / "tests" / "fixtures" / "sample_project.sif"
TEST_PORT = 19995


@pytest.mark.skipif(not BIN_PATH.exists(), reason="Patched Synfig Studio binary not found")
@pytest.mark.asyncio
async def test_live_bridge_mutating_path(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["SYNFIG_MCP_PORT"] = str(TEST_PORT)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token_path = token_dir / "mcp_token"
    if token_path.exists():
        token_path.unlink()

    log_path = tmp_path / "studio_mutate_test.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(BIN_PATH), str(SAMPLE_SIF)],
            env=env,
            stdout=log_file,
            stderr=log_file,
            cwd=str(BIN_PATH.parent),
        )

    try:
        token = ""
        for _ in range(30):
            if token_path.exists():
                try:
                    token = token_path.read_text(encoding="utf-8").strip()
                    if token:
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        assert token, "Session token was not created by Synfig Studio"

        client = BridgeClient(host="127.0.0.1", port=TEST_PORT, token=token, default_timeout=10.0)
        connected = False
        for _ in range(20):
            try:
                await client.connect()
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert connected, "Failed to connect to live bridge"
        assert "layer.write" in client.capabilities
        assert "param.write" in client.capabilities
        assert "history" in client.capabilities

        # 1. layer.add
        add_res = await client.call(
            "layer.add",
            {
                "doc_id": "doc_0",
                "layer_type": "circle",
                "description": "MutateCircle",
                "depth": 0,
                "params": {
                    "radius": {"type": "real", "value": 2.5},
                    "color": {
                        "type": "color",
                        "value": {"r": 0.1, "g": 0.9, "b": 0.2, "a": 1.0},
                    },
                },
            },
        )
        assert add_res["description"] == "MutateCircle"
        assert "MutateCircle" in add_res["diff"]["created"]

        p_res = await client.call(
            "param.get",
            {"doc_id": "doc_0", "layer_id": "MutateCircle", "param_name": "radius"},
        )
        assert abs(p_res["value"]["value"] - 2.5) < 0.01

        # 2. param.set
        set_res = await client.call(
            "param.set",
            {
                "doc_id": "doc_0",
                "layer_id": "MutateCircle",
                "param_name": "radius",
                "value": {"type": "real", "value": 3.75},
            },
        )
        assert abs(set_res["before"]["value"] - 2.5) < 0.01
        assert abs(set_res["after"]["value"] - 3.75) < 0.01

        p_res = await client.call(
            "param.get",
            {"doc_id": "doc_0", "layer_id": "MutateCircle", "param_name": "radius"},
        )
        assert abs(p_res["value"]["value"] - 3.75) < 0.01

        # 3. history.undo
        undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
        assert undo_res["success"] is True

        p_res = await client.call(
            "param.get",
            {"doc_id": "doc_0", "layer_id": "MutateCircle", "param_name": "radius"},
        )
        assert abs(p_res["value"]["value"] - 2.5) < 0.01

        # 4. history.redo
        redo_res = await client.call("history.redo", {"doc_id": "doc_0"})
        assert redo_res["success"] is True

        p_res = await client.call(
            "param.get",
            {"doc_id": "doc_0", "layer_id": "MutateCircle", "param_name": "radius"},
        )
        assert abs(p_res["value"]["value"] - 3.75) < 0.01

        # 5. anim.time_set
        t_res = await client.call("anim.time_set", {"doc_id": "doc_0", "time": 2.0})
        assert abs(t_res["time"]["seconds"] - 2.0) < 0.01

        curr_t = await client.call("anim.time_get", {"doc_id": "doc_0"})
        assert abs(curr_t["time"]["seconds"] - 2.0) < 0.01

        # 6. anim.keyframe_add
        kf_res = await client.call(
            "anim.keyframe_add",
            {"doc_id": "doc_0", "time": 2.0, "description": "MidwayKF"},
        )
        assert kf_res["diff"]["action"] == "anim.keyframe_add"

        # 7. layer.reorder
        reorder_res = await client.call(
            "layer.reorder",
            {"doc_id": "doc_0", "layer_id": "MutateCircle", "new_depth": 1},
        )
        assert reorder_res["depth"] == 1

        # 8. selection.set
        sel_res = await client.call(
            "selection.set",
            {"doc_id": "doc_0", "layer_ids": ["MutateCircle"]},
        )
        assert "MutateCircle" in sel_res["selected_layers"]

        # 9. layer.remove
        del_res = await client.call(
            "layer.remove",
            {"doc_id": "doc_0", "layer_id": "MutateCircle"},
        )
        assert "MutateCircle" in del_res["diff"]["deleted"]

        tree = await client.call("scene.tree", {"doc_id": "doc_0"})
        remaining = [layer.get("desc") for layer in tree["layers"]]
        assert "MutateCircle" not in remaining

        await client.close()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
