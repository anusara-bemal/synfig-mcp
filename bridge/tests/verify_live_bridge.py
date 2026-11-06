import os
import sys
import time
import subprocess
import asyncio
from pathlib import Path

# Add server/src to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "server" / "src"))

from synfig_mcp.protocol.client import BridgeClient

TEST_PORT = 19999
BIN_PATH = repo_root / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe"
SAMPLE_SIF = repo_root / "server" / "tests" / "fixtures" / "sample_project.sif"

async def main():
    if not BIN_PATH.exists():
        print(f"Error: Binary not found at {BIN_PATH}")
        sys.exit(1)

    # Set up environment
    env = os.environ.copy()
    env["SYNFIG_MCP_PORT"] = str(TEST_PORT)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

    token_path = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig" / "mcp_token"
    if token_path.exists():
        token_path.unlink()

    log_path = repo_root / "bridge" / "tests" / "studio_run.log"
    log_file = open(log_path, "w", encoding="utf-8")

    print(f"Starting Synfig Studio from {BIN_PATH} with {SAMPLE_SIF}...")
    proc = subprocess.Popen(
        [str(BIN_PATH), str(SAMPLE_SIF)],
        env=env,
        stdout=log_file,
        stderr=log_file,
        cwd=str(BIN_PATH.parent)
    )

    try:
        # Wait for token file
        token_path = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig" / "mcp_token"
        print(f"Waiting for token file at {token_path}...")
        token = ""
        for _ in range(30):
            if token_path.exists():
                try:
                    token = token_path.read_text().strip()
                    if token:
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        if not token:
            print("Failed to read token file within 15 seconds")
            sys.exit(1)

        print(f"Read session token: {token[:8]}...")

        # Connect with BridgeClient
        client = BridgeClient(host="127.0.0.1", port=TEST_PORT, token=token, default_timeout=10.0)
        print("Connecting to live bridge...")
        connected = False
        for attempt in range(20):
            try:
                await client.connect()
                connected = True
                break
            except Exception as e:
                print(f"Connection attempt {attempt+1} failed: {e}, retrying...")
                await asyncio.sleep(0.5)

        if not connected:
            print("Failed to connect to live bridge")
            sys.exit(1)

        print("=== Successfully Connected to Live Synfig Studio! ===")

        # 1. doc.info
        info = await client.call("doc.info", {"doc_id": "doc_0"})
        print("doc.info result:", info)
        assert info["width"] == 1920, f"Expected 1920 width, got {info['width']}"
        assert info["height"] == 1080, f"Expected 1080 height, got {info['height']}"
        assert info["fps"] == 24.0, f"Expected 24 fps, got {info['fps']}"
        print("✓ doc.info verified")

        # 2. doc.list
        docs = await client.call("doc.list", {})
        print("doc.list result:", docs)
        assert len(docs) >= 1, "Expected at least 1 document"
        print("✓ doc.list verified")

        # 3. scene.tree
        tree = await client.call("scene.tree", {"doc_id": "doc_0"})
        print("scene.tree result:", tree)
        assert "layers" in tree, "Tree missing layers"
        layer_names = [l.get("desc") or l.get("type") for l in tree["layers"]]
        print("Layers found:", layer_names)
        assert "Circle001" in layer_names or "circle" in layer_names, "Circle layer not found"
        print("✓ scene.tree verified")

        # 4. param.get (color)
        param_color = await client.call("param.get", {
            "doc_id": "doc_0",
            "layer_id": "Circle001",
            "param_name": "color"
        })
        print("param.get (color) result:", param_color)
        assert param_color["value"]["type"] == "color"
        val = param_color["value"]["value"]
        assert abs(val["r"] - 0.2) < 0.05, f"Unexpected r: {val['r']}"
        assert abs(val["g"] - 0.6) < 0.05, f"Unexpected g: {val['g']}"
        assert abs(val["b"] - 1.0) < 0.05, f"Unexpected b: {val['b']}"
        print("✓ param.get (color) verified")

        # 5. param.get (radius)
        param_radius = await client.call("param.get", {
            "doc_id": "doc_0",
            "layer_id": "Circle001",
            "param_name": "radius"
        })
        print("param.get (radius) result:", param_radius)
        assert param_radius["value"]["type"] == "real"
        assert abs(param_radius["value"]["value"] - 1.5) < 0.01
        print("✓ param.get (radius) verified")

        # 6. anim.time_get
        time_res = await client.call("anim.time_get", {"doc_id": "doc_0"})
        print("anim.time_get result:", time_res)
        assert "time" in time_res
        print("✓ anim.time_get verified")

        # 7. selection.get
        sel_res = await client.call("selection.get", {"doc_id": "doc_0"})
        print("selection.get result:", sel_res)
        assert "selected_layers" in sel_res
        print("✓ selection.get verified")

        await client.close()
        print("=== ALL LIVE BRIDGE VERIFICATIONS PASSED 100% ===")

    finally:
        print("Shutting down Synfig Studio test instance...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("Studio terminated cleanly.")
        log_file.close()

if __name__ == "__main__":
    asyncio.run(main())
