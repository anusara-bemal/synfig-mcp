"""
End-to-end integration tests for Live Synfig Studio MCP Bridge (Read-Only Path).
Launches the patched Synfig Studio executable, connects over TCP with token authentication,
and validates doc.info, doc.list, scene.tree, param.get, anim.time_get, and selection.get.
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
TEST_PORT = 19997


@pytest.mark.skipif(not BIN_PATH.exists(), reason="Patched Synfig Studio binary not found")
@pytest.mark.asyncio
async def test_live_bridge_read_path(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["SYNFIG_MCP_PORT"] = str(TEST_PORT)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token_path = token_dir / "mcp_token"
    if token_path.exists():
        token_path.unlink()

    log_path = tmp_path / "studio_test.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(BIN_PATH), str(SAMPLE_SIF)],
            env=env,
            stdout=log_file,
            stderr=log_file,
            cwd=str(BIN_PATH.parent),
        )

    try:
        # 1. Wait for token file to be generated
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

        # 2. Connect with BridgeClient
        client = BridgeClient(host="127.0.0.1", port=TEST_PORT, token=token, default_timeout=10.0)
        connected = False
        for _ in range(20):
            try:
                await client.connect()
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert connected, "Failed to connect and handshake with live bridge"
        assert "doc.read" in client.capabilities
        assert "param.read" in client.capabilities

        # 3. doc.info
        info = await client.call("doc.info", {"doc_id": "doc_0"})
        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["fps"] == 24.0
        assert info["duration_frames"] == 120
        assert info["name"] == "Test Animation"

        # 4. doc.list
        docs = await client.call("doc.list", {})
        assert isinstance(docs, list)
        assert len(docs) >= 1
        assert docs[0]["doc_id"] == "doc_0"

        # 5. scene.tree
        tree = await client.call("scene.tree", {"doc_id": "doc_0"})
        assert "layers" in tree
        layers = tree["layers"]
        layer_names = [layer.get("desc") or layer.get("type") for layer in layers]
        assert "Circle001" in layer_names
        assert "Rect001" in layer_names

        # 6. param.get (color)
        param_color = await client.call(
            "param.get",
            {"doc_id": "doc_0", "layer_id": "Circle001", "param_name": "color"},
        )
        assert param_color["value"]["type"] == "color"
        c = param_color["value"]["value"]
        assert abs(c["r"] - 0.2) < 0.05
        assert abs(c["g"] - 0.6) < 0.05
        assert abs(c["b"] - 1.0) < 0.05

        # 7. param.get (radius)
        param_radius = await client.call(
            "param.get",
            {"doc_id": "doc_0", "layer_id": "Circle001", "param_name": "radius"},
        )
        assert param_radius["value"]["type"] == "real"
        assert abs(param_radius["value"]["value"] - 1.5) < 0.01

        # 8. anim.time_get
        time_info = await client.call("anim.time_get", {"doc_id": "doc_0"})
        assert "time" in time_info
        assert "seconds" in time_info["time"]

        # 9. selection.get
        sel = await client.call("selection.get", {"doc_id": "doc_0"})
        assert "selected_layers" in sel

        await client.close()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
