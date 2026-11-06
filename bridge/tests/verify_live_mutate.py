import os
import sys
import subprocess
import asyncio
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "server" / "src"))

from synfig_mcp.protocol.client import BridgeClient

TEST_PORT = 19996
BIN_PATH = repo_root / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe"
SAMPLE_SIF = repo_root / "server" / "tests" / "fixtures" / "sample_project.sif"

async def main():
    if not BIN_PATH.exists():
        print(f"Error: Binary not found at {BIN_PATH}")
        sys.exit(1)

    env = os.environ.copy()
    env["SYNFIG_MCP_PORT"] = str(TEST_PORT)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

    token_path = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig" / "mcp_token"
    if token_path.exists():
        token_path.unlink()

    log_path = repo_root / "bridge" / "tests" / "studio_mutate_run.log"
    log_file = open(log_path, "w", encoding="utf-8")

    print(f"Starting Synfig Studio from {BIN_PATH}...")
    proc = subprocess.Popen(
        [str(BIN_PATH), str(SAMPLE_SIF)],
        env=env,
        stdout=log_file,
        stderr=log_file,
        cwd=str(BIN_PATH.parent)
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

        assert token, "Session token was not created"
        print(f"Read session token: {token[:8]}...")

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
        print("=== Successfully Connected to Live Synfig Studio! ===")

        # 1. Test layer.add
        print("\n--- 1. Testing layer.add ---")
        add_res = await client.call("layer.add", {
            "doc_id": "doc_0",
            "layer_type": "circle",
            "description": "MutateCircle",
            "depth": 0,
            "params": {
                "radius": {"type": "real", "value": 2.5},
                "color": {"type": "color", "value": {"r": 0.1, "g": 0.9, "b": 0.2, "a": 1.0}}
            }
        })
        print("layer.add result:", add_res)
        assert add_res["description"] == "MutateCircle"
        assert add_res["diff"]["action"] == "layer.add"
        assert "MutateCircle" in add_res["diff"]["created"]

        # Verify parameter was set
        p_res = await client.call("param.get", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle",
            "param_name": "radius"
        })
        print("param.get initial radius:", p_res)
        assert abs(p_res["value"]["value"] - 2.5) < 0.01

        # 2. Test param.set
        print("\n--- 2. Testing param.set ---")
        set_res = await client.call("param.set", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle",
            "param_name": "radius",
            "value": {"type": "real", "value": 3.75}
        })
        print("param.set result:", set_res)
        assert abs(set_res["before"]["value"] - 2.5) < 0.01
        assert abs(set_res["after"]["value"] - 3.75) < 0.01

        p_res = await client.call("param.get", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle",
            "param_name": "radius"
        })
        assert abs(p_res["value"]["value"] - 3.75) < 0.01
        print("✓ Verified param.set changed radius to 3.75")

        # 3. Test history.undo
        print("\n--- 3. Testing history.undo ---")
        undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
        print("history.undo result:", undo_res)
        assert undo_res["success"] is True

        # Radius should be reverted back to 2.5
        p_res = await client.call("param.get", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle",
            "param_name": "radius"
        })
        print("param.get after undo:", p_res)
        assert abs(p_res["value"]["value"] - 2.5) < 0.01
        print("✓ Verified undo reverted radius back to 2.5")

        # 4. Test history.redo
        print("\n--- 4. Testing history.redo ---")
        redo_res = await client.call("history.redo", {"doc_id": "doc_0"})
        print("history.redo result:", redo_res)
        assert redo_res["success"] is True

        # Radius should be 3.75 again
        p_res = await client.call("param.get", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle",
            "param_name": "radius"
        })
        print("param.get after redo:", p_res)
        assert abs(p_res["value"]["value"] - 3.75) < 0.01
        print("✓ Verified redo restored radius to 3.75")

        # 5. Test anim.time_set
        print("\n--- 5. Testing anim.time_set ---")
        t_res = await client.call("anim.time_set", {
            "doc_id": "doc_0",
            "time": 2.0
        })
        print("anim.time_set result:", t_res)
        assert abs(t_res["time"]["seconds"] - 2.0) < 0.01

        curr_t = await client.call("anim.time_get", {"doc_id": "doc_0"})
        assert abs(curr_t["time"]["seconds"] - 2.0) < 0.01
        print("✓ Verified playhead seek to 2.0s")

        # 6. Test anim.keyframe_add
        print("\n--- 6. Testing anim.keyframe_add ---")
        kf_res = await client.call("anim.keyframe_add", {
            "doc_id": "doc_0",
            "time": 2.0,
            "description": "MidwayKF"
        })
        print("anim.keyframe_add result:", kf_res)
        assert kf_res["diff"]["action"] == "anim.keyframe_add"
        print("✓ Verified keyframe added at 2.0s")

        # 7. Test layer.reorder
        print("\n--- 7. Testing layer.reorder ---")
        reorder_res = await client.call("layer.reorder", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle",
            "new_depth": 1
        })
        print("layer.reorder result:", reorder_res)
        assert reorder_res["depth"] == 1

        # 8. Test selection.set
        print("\n--- 8. Testing selection.set ---")
        sel_res = await client.call("selection.set", {
            "doc_id": "doc_0",
            "layer_ids": ["MutateCircle"]
        })
        print("selection.set result:", sel_res)
        assert "MutateCircle" in sel_res["selected_layers"]

        # 9. Test layer.remove
        print("\n--- 9. Testing layer.remove ---")
        del_res = await client.call("layer.remove", {
            "doc_id": "doc_0",
            "layer_id": "MutateCircle"
        })
        print("layer.remove result:", del_res)
        assert "MutateCircle" in del_res["diff"]["deleted"]

        tree = await client.call("scene.tree", {"doc_id": "doc_0"})
        remaining_layers = [l.get("desc") for l in tree["layers"]]
        print("Remaining layers:", remaining_layers)
        assert "MutateCircle" not in remaining_layers
        print("✓ Verified layer.remove deleted MutateCircle")

        await client.close()
        print("\n=== ALL MUTATION & UNDO/REDO VERIFICATIONS PASSED 100% ===")

    finally:
        print("Shutting down Synfig Studio test instance...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        log_file.close()
        print("Studio terminated cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
