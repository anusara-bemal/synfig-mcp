"""
Comprehensive End-to-End integration tests for Live Synfig Studio MCP Bridge.
Exercises the real synfigstudio.exe process (no fakes).

Covers all Phase P7 re-scoped requirements:
A. Live E2E coverage for:
   - layer.set_param for all 6 core types (real, color, vector, angle, bool, string) + undo
   - layer.delete (layer.remove) + undo
   - layer.move (layer.reorder) + undo
   - layer.duplicate + undo
   - keyframe.add & keyframe.delete + undo
   - anim.time.set
   - canvas.render_frame (real file generation with PNG magic bytes)
   - doc.new, doc.save, doc.close, doc.open
   - Interleaving AI edit then simulated manual action on GTK thread then two undos (proving order)
B. Investigation: doc.close on unsaved changes returns error immediately without blocking on GTK modal dialog.
C. Windows token file ACL validation: owner-only permissions with inheritance stripped via icacls.
"""

import asyncio
import os
import shutil
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.errors import SecurityError, SecuritySandboxError, SynfigError
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.render.cache import RenderCache
from synfig_mcp.render.pipeline import CancellationToken, RenderPipeline

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BIN_PATH = REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe"
SAMPLE_SIF = REPO_ROOT / "server" / "tests" / "fixtures" / "sample_project.sif"
TEST_PORT = 19992


@pytest_asyncio.fixture
async def live_studio(tmp_path: Path) -> AsyncIterator[BridgeClient]:
    """Launches real synfigstudio.exe, connects over TCP with token authentication, and yields the client."""
    if not BIN_PATH.exists():
        pytest.skip("Patched Synfig Studio binary not found")

    env = os.environ.copy()
    env["SYNFIG_MCP_PORT"] = str(TEST_PORT)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token_path = token_dir / "mcp_token"
    if token_path.exists():
        token_path.unlink()

    log_path = tmp_path / "studio_e2e.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(BIN_PATH), str(SAMPLE_SIF)],
            env=env,
            stdout=log_file,
            stderr=log_file,
            cwd=str(BIN_PATH.parent),
        )

    client: BridgeClient | None = None
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
        for _ in range(25):
            try:
                await client.connect()
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert connected, "Failed to connect to live bridge"

        # Wait for Studio document initialization
        for _ in range(20):
            doc_list = await client.call("doc.list")
            if doc_list:
                break
            await asyncio.sleep(0.5)

        yield client

    finally:
        if client and client.is_connected:
            await client.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_scenario_only(live_studio: BridgeClient, tmp_path: Path) -> None:
    client = live_studio
    circle_add = await client.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "ScenarioCircle"}
    )
    circle_id = circle_add.get("layer_id", "ScenarioCircle")

    anim_res = await client.call(
        "anim.animate_param",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "waypoints": [
                {
                    "time": 0.0,
                    "value": {"type": "vector", "value": {"x": 0.0, "y": 0.0}},
                    "interpolation": "linear",
                },
                {
                    "time": 2.0,
                    "value": {"type": "vector", "value": {"x": 3.0, "y": 0.0}},
                    "interpolation": "linear",
                },
            ],
        },
    )
    assert anim_res.get("waypoint_count") == 2

    def get_vec(p_val: dict[str, Any]) -> tuple[float, float]:
        v = p_val.get("value", {})
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        if isinstance(v, dict):
            return float(v.get("x", 0.0)), float(v.get("y", 0.0))
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            return float(v[0]), float(v[1])
        return 0.0, 0.0

    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 0.0})
    p0 = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx0, vy0 = get_vec(p0)
    assert abs(vx0 - 0.0) < 0.05

    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 1.0})
    p1 = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx1, vy1 = get_vec(p1)
    print("SCENARIO ONLY P1:", p1, "vx1:", vx1)
    assert abs(vx1 - 1.5) < 0.1

    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 2.0})
    p2 = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx2, vy2 = get_vec(p2)
    assert abs(vx2 - 3.0) < 0.05

    # Render 3 frames
    for idx, t_frame in enumerate([0.0, 1.0, 2.0]):
        frame_png = tmp_path / f"scenario_frame_{idx}.png"
        r_res = await client.call(
            "canvas.render_frame",
            {
                "doc_id": "doc_0",
                "output_path": str(frame_png),
                "time": t_frame,
                "width": 160,
                "height": 120,
            },
        )
        assert r_res["success"] is True
        assert frame_png.exists()
        assert frame_png.stat().st_size > 100

    # Undo whole animation in 1 step
    undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_res["success"] is True

    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 2.0})
    p_undone = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx_u, vy_u = get_vec(p_undone)
    assert abs(vx_u - 0.0) < 0.05


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_bridge_full_suite(live_studio: BridgeClient, tmp_path: Path) -> None:
    """
    Executes the complete verification suite against a live running synfigstudio.exe.
    Guarantees consistent execution across all P7 re-scoped requirements.
    """
    client = live_studio

    # -------------------------------------------------------------
    # 1. Requirement C: Token file permissions (owner-only Win32 ACL)
    # -------------------------------------------------------------
    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token_path = token_dir / "mcp_token"
    assert token_path.exists(), "Token file must exist"
    if os.name == "nt":
        res = subprocess.run(
            ["icacls", str(token_path)], capture_output=True, text=True, check=True
        )
        assert "(I)" not in res.stdout, f"Inherited ACEs should be stripped, got:\n{res.stdout}"
        assert ":(F)" in res.stdout, f"Owner should have full control (F), got:\n{res.stdout}"

    # -------------------------------------------------------------
    # 2. Requirement A: layer.set_param for 6 core types + undo
    # -------------------------------------------------------------
    # Circle for real, color, vector, bool
    await client.call(
        "layer.add",
        {
            "doc_id": "doc_0",
            "layer_type": "circle",
            "description": "ParamTestCircle",
            "depth": 0,
            "params": {
                "radius": {"type": "real", "value": 2.0},
                "color": {"type": "color", "value": {"r": 0.0, "g": 0.0, "b": 1.0, "a": 1.0}},
                "origin": {"type": "vector", "value": {"x": 0.0, "y": 0.0}},
                "invert": {"type": "bool", "value": False},
            },
        },
    )

    # Real
    await client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": "ParamTestCircle",
            "param_name": "radius",
            "value": {"type": "real", "value": 4.5},
        },
    )
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "radius"}
    )
    assert abs(p["value"]["value"] - 4.5) < 0.01
    await client.call("history.undo", {"doc_id": "doc_0"})
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "radius"}
    )
    assert abs(p["value"]["value"] - 2.0) < 0.01

    # Color
    await client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": "ParamTestCircle",
            "param_name": "color",
            "value": {"type": "color", "value": {"r": 0.9, "g": 0.1, "b": 0.2, "a": 1.0}},
        },
    )
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "color"}
    )
    assert abs(p["value"]["value"]["r"] - 0.9) < 0.01
    await client.call("history.undo", {"doc_id": "doc_0"})
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "color"}
    )
    assert abs(p["value"]["value"]["r"] - 0.0) < 0.01

    # Vector
    await client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": "ParamTestCircle",
            "param_name": "origin",
            "value": {"type": "vector", "value": {"x": 3.0, "y": -1.5}},
        },
    )
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "origin"}
    )
    assert abs(p["value"]["value"]["x"] - 3.0) < 0.01
    assert abs(p["value"]["value"]["y"] - -1.5) < 0.01
    await client.call("history.undo", {"doc_id": "doc_0"})
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "origin"}
    )
    assert abs(p["value"]["value"]["x"] - 0.0) < 0.01

    # Bool
    await client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": "ParamTestCircle",
            "param_name": "invert",
            "value": {"type": "bool", "value": True},
        },
    )
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "invert"}
    )
    assert p["value"]["value"] is True
    await client.call("history.undo", {"doc_id": "doc_0"})
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestCircle", "param_name": "invert"}
    )
    assert p["value"]["value"] is False

    # Rotate layer for angle
    await client.call(
        "layer.add",
        {
            "doc_id": "doc_0",
            "layer_type": "rotate",
            "description": "ParamTestRotate",
            "depth": 0,
            "params": {"amount": {"type": "angle", "value": {"degrees": 0.0}}},
        },
    )
    await client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": "ParamTestRotate",
            "param_name": "amount",
            "value": {"type": "angle", "value": {"degrees": 45.0}},
        },
    )
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestRotate", "param_name": "amount"}
    )
    assert abs(p["value"]["value"]["degrees"] - 45.0) < 0.1
    await client.call("history.undo", {"doc_id": "doc_0"})
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "ParamTestRotate", "param_name": "amount"}
    )
    assert abs(p["value"]["value"]["degrees"] - 0.0) < 0.1

    # Text layer for string
    text_res = await client.call(
        "layer.add",
        {
            "doc_id": "doc_0",
            "layer_type": "text",
            "depth": 0,
            "params": {"text": {"type": "string", "value": "OriginalText"}},
        },
    )
    text_layer_id = text_res["layer_id"]
    await client.call(
        "param.set",
        {
            "doc_id": "doc_0",
            "layer_id": text_layer_id,
            "param_name": "text",
            "value": {"type": "string", "value": "UpdatedSynfigText"},
        },
    )
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "UpdatedSynfigText", "param_name": "text"}
    )
    assert p["value"]["value"] == "UpdatedSynfigText"
    await client.call("history.undo", {"doc_id": "doc_0"})
    p = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": "OriginalText", "param_name": "text"}
    )
    assert p["value"]["value"] == "OriginalText"

    # -------------------------------------------------------------
    # 3. Requirement A: layer.duplicate + undo
    # -------------------------------------------------------------
    tree_before = await client.call("scene.tree", {"doc_id": "doc_0"})
    before_count = [lyr.get("desc") for lyr in tree_before.get("layers", [])].count(
        "ParamTestCircle"
    )

    dup_res = await client.call(
        "layer.duplicate", {"doc_id": "doc_0", "layer_id": "ParamTestCircle"}
    )
    assert dup_res["layer_id"] != ""

    tree_after = await client.call("scene.tree", {"doc_id": "doc_0"})
    after_count = [lyr.get("desc") for lyr in tree_after.get("layers", [])].count("ParamTestCircle")
    assert after_count == before_count + 1

    # Undo removes the duplicated layer
    await client.call("history.undo", {"doc_id": "doc_0"})
    tree_undone = await client.call("scene.tree", {"doc_id": "doc_0"})
    undone_count = [lyr.get("desc") for lyr in tree_undone.get("layers", [])].count(
        "ParamTestCircle"
    )
    assert undone_count == before_count

    # -------------------------------------------------------------
    # 4. Requirement A: layer.move / layer.reorder + undo
    # -------------------------------------------------------------
    tree_before = await client.call("scene.tree", {"doc_id": "doc_0"})
    orig_idx = next(
        i
        for i, lyr in enumerate(tree_before.get("layers", []))
        if lyr.get("desc") == "ParamTestRotate"
    )

    target_depth = 0 if orig_idx != 0 else 1
    await client.call(
        "layer.move", {"doc_id": "doc_0", "layer_id": "ParamTestRotate", "new_depth": target_depth}
    )
    tree_moved = await client.call("scene.tree", {"doc_id": "doc_0"})
    moved_idx = next(
        i
        for i, lyr in enumerate(tree_moved.get("layers", []))
        if lyr.get("desc") == "ParamTestRotate"
    )
    assert moved_idx != orig_idx

    # Undo restores original depth
    await client.call("history.undo", {"doc_id": "doc_0"})
    tree_restored = await client.call("scene.tree", {"doc_id": "doc_0"})
    restored_idx = next(
        i
        for i, lyr in enumerate(tree_restored.get("layers", []))
        if lyr.get("desc") == "ParamTestRotate"
    )
    assert restored_idx == orig_idx

    # -------------------------------------------------------------
    # 5. Requirement A: layer.delete (layer.remove) + undo
    # -------------------------------------------------------------
    await client.call("layer.delete", {"doc_id": "doc_0", "layer_id": "ParamTestRotate"})
    tree = await client.call("scene.tree", {"doc_id": "doc_0"})
    layer_names = [lyr.get("desc") for lyr in tree.get("layers", [])]
    assert "ParamTestRotate" not in layer_names
    await client.call("history.undo", {"doc_id": "doc_0"})
    tree = await client.call("scene.tree", {"doc_id": "doc_0"})
    layer_names = [lyr.get("desc") for lyr in tree.get("layers", [])]
    assert "ParamTestRotate" in layer_names

    # -------------------------------------------------------------
    # 6. Requirement A: keyframe.add & keyframe.delete + undo
    # -------------------------------------------------------------
    await client.call("keyframe.add", {"doc_id": "doc_0", "time": 1.5, "description": "LiveE2EKF"})
    kf_res = await client.call("anim.keyframe_list", {"doc_id": "doc_0"})
    kfs = kf_res.get("keyframes", [])
    assert any(abs(kf["time"] - 1.5) < 0.01 for kf in kfs)

    await client.call("history.undo", {"doc_id": "doc_0"})
    kf_res = await client.call("anim.keyframe_list", {"doc_id": "doc_0"})
    assert not any(abs(kf["time"] - 1.5) < 0.01 for kf in kf_res.get("keyframes", []))

    await client.call("history.redo", {"doc_id": "doc_0"})
    kf_res = await client.call("anim.keyframe_list", {"doc_id": "doc_0"})
    assert any(abs(kf["time"] - 1.5) < 0.01 for kf in kf_res.get("keyframes", []))

    await client.call("keyframe.delete", {"doc_id": "doc_0", "time": 1.5})
    kf_res = await client.call("anim.keyframe_list", {"doc_id": "doc_0"})
    assert not any(abs(kf["time"] - 1.5) < 0.01 for kf in kf_res.get("keyframes", []))

    await client.call("history.undo", {"doc_id": "doc_0"})
    kf_res = await client.call("anim.keyframe_list", {"doc_id": "doc_0"})
    assert any(abs(kf["time"] - 1.5) < 0.01 for kf in kf_res.get("keyframes", []))

    # Clean up test keyframe so subsequent animation is not locked by keyframe
    await client.call("keyframe.delete", {"doc_id": "doc_0", "time": 1.5})

    # -------------------------------------------------------------
    # 7. Requirement A: anim.time.set
    # -------------------------------------------------------------
    t_res = await client.call("anim.time.set", {"doc_id": "doc_0", "time": 2.25})
    assert abs(t_res["time"]["seconds"] - 2.25) < 0.01
    curr = await client.call("anim.time.get", {"doc_id": "doc_0"})
    assert abs(curr["time"]["seconds"] - 2.25) < 0.01
    # Reset timeline back to 0.0s
    await client.call("anim.time.set", {"doc_id": "doc_0", "time": 0.0})

    # -------------------------------------------------------------
    # 8. Requirement A: canvas.render_frame to real PNG file
    # -------------------------------------------------------------
    out_png = tmp_path / "live_rendered_frame.png"
    render_res = await client.call(
        "canvas.render_frame",
        {"doc_id": "doc_0", "output_path": str(out_png), "time": 0.0, "width": 320, "height": 240},
    )
    assert render_res["success"] is True
    assert out_png.exists()
    assert out_png.stat().st_size > 100
    assert out_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    # -------------------------------------------------------------
    # 9. Requirements A & B: Document lifecycle & GTK dialog safety
    # -------------------------------------------------------------
    new_doc = await client.call("doc.new", {"width": 800, "height": 600, "fps": 24.0})
    new_id = new_doc["doc_id"]
    assert new_id != ""

    # Mutate to make it dirty
    await client.call(
        "layer.add", {"doc_id": new_id, "layer_type": "circle", "description": "DirtyCircle"}
    )

    # Verify doc.close(force=False) fails fast with error 2004 without blocking on modal dialog
    close_err: dict[str, Any] = {}
    try:
        await client.call("doc.close", {"doc_id": new_id, "force": False})
    except Exception as e:
        close_err["error"] = str(e)
    assert "unsaved changes" in close_err.get("error", "").lower()

    # Save to disk
    save_path = tmp_path / "lifecycle_doc.sifz"
    save_res = await client.call("doc.save", {"doc_id": new_id, "file_path": str(save_path)})
    assert save_res["success"] is True
    assert save_path.exists()

    # Close with force=True
    close_res = await client.call("doc.close", {"doc_id": new_id, "force": True})
    assert close_res["closed"] is True

    # Reopen saved document
    open_res = await client.call("doc.open", {"file_path": str(save_path)})
    reopened_id = open_res["doc_id"]
    assert reopened_id != ""
    await client.call("doc.close", {"doc_id": reopened_id, "force": True})

    # -------------------------------------------------------------
    # 10. Requirement A: Interleaved AI edit & GTK manual action undo order
    # -------------------------------------------------------------
    # AI Edit #1
    await client.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "AI_Circle"}
    )
    tree = await client.call("scene.tree", {"doc_id": "doc_0"})
    assert "AI_Circle" in [lyr.get("desc") for lyr in tree.get("layers", [])]

    # Manual Edit #2 on GTK thread directly
    manual_res = await client.call("test.manual_action", {"doc_id": "doc_0"})
    assert manual_res["manual"] is True

    # Undo 1 pops Manual Edit #2; AI_Circle MUST remain
    await client.call("history.undo", {"doc_id": "doc_0"})
    tree = await client.call("scene.tree", {"doc_id": "doc_0"})
    assert "AI_Circle" in [lyr.get("desc") for lyr in tree.get("layers", [])]

    # Undo 2 pops AI Edit #1; AI_Circle MUST be removed
    await client.call("history.undo", {"doc_id": "doc_0"})
    tree = await client.call("scene.tree", {"doc_id": "doc_0"})
    assert "AI_Circle" not in [lyr.get("desc") for lyr in tree.get("layers", [])]

    # -------------------------------------------------------------
    # 11. Phase P7a Core Animation Scenario:
    #     - Create circle
    #     - Animate origin (0,0) -> (3,0) over 2s via anim.animate_param
    #     - Verify via anim.time_set at 0/1/2s that interpolated values are correct
    #     - Render 3 frames
    #     - Undo the whole animation in ONE step
    #     - Test ValueNode param.convert and undo
    # -------------------------------------------------------------
    # Step 1: Create circle
    circle_add = await client.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "MotionCircle"}
    )
    circle_id = circle_add.get("layer_id", "Circle001")

    # Step 2: Animate origin from (0,0) to (3,0) over 2s in 1 single undo action
    anim_res = await client.call(
        "anim.animate_param",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "waypoints": [
                {
                    "time": 0.0,
                    "value": {"type": "vector", "value": {"x": 0.0, "y": 0.0}},
                    "interpolation": "linear",
                },
                {
                    "time": 2.0,
                    "value": {"type": "vector", "value": {"x": 3.0, "y": 0.0}},
                    "interpolation": "linear",
                },
            ],
        },
    )
    assert anim_res.get("waypoint_count") == 2 or anim_res.get("count") == 2
    print("DEBUG ANIM_RES:", anim_res)

    def get_vec(p_val: dict[str, Any]) -> tuple[float, float]:
        v = p_val.get("value", {})
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        if isinstance(v, dict):
            return float(v.get("x", 0.0)), float(v.get("y", 0.0))
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            return float(v[0]), float(v[1])
        return 0.0, 0.0

    # Step 3: Verify interpolated values at 0s, 1s, 2s
    # At 0.0s -> (0, 0)
    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 0.0})
    p0 = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx0, vy0 = get_vec(p0)
    assert abs(vx0 - 0.0) < 0.05
    assert abs(vy0 - 0.0) < 0.05

    # At 1.0s -> (1.5, 0) interpolated
    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 1.0})
    p1 = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx1, vy1 = get_vec(p1)
    assert abs(vx1 - 1.5) < 0.1
    assert abs(vy1 - 0.0) < 0.05

    # At 2.0s -> (3.0, 0)
    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 2.0})
    p2 = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx2, vy2 = get_vec(p2)
    assert abs(vx2 - 3.0) < 0.05
    assert abs(vy2 - 0.0) < 0.05

    # Step 4: Render 3 frames
    for idx, t_frame in enumerate([0.0, 1.0, 2.0]):
        frame_png = tmp_path / f"scenario_frame_{idx}.png"
        r_res = await client.call(
            "canvas.render_frame",
            {
                "doc_id": "doc_0",
                "output_path": str(frame_png),
                "time": t_frame,
                "width": 160,
                "height": 120,
            },
        )
        assert r_res["success"] is True
        assert frame_png.exists()
        assert frame_png.stat().st_size > 100

    # Step 5: Undo the WHOLE animation in ONE step
    undo_anim = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_anim["success"] is True

    # Verify origin at 2.0s is reverted back to static (0, 0)
    await client.call("anim.time_set", {"doc_id": "doc_0", "time": 2.0})
    p_undone = await client.call(
        "param.get", {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin"}
    )
    vx_undone, vy_undone = get_vec(p_undone)
    assert abs(vx_undone - 0.0) < 0.05
    assert abs(vy_undone - 0.0) < 0.05

    # Step 6: Test ValueNode param.convert and undo
    conv_res = await client.call(
        "param.convert",
        {"doc_id": "doc_0", "layer_id": circle_id, "param_name": "origin", "type": "composite"},
    )
    assert conv_res.get("type") == "composite"

    undo_conv = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_conv["success"] is True

    # Clean up circle
    await client.call("layer.remove", {"doc_id": "doc_0", "layer_id": circle_id})


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_waypoint_remove(live_studio: BridgeClient) -> None:
    """Requirement 1: anim.waypoint_remove against real Studio with undo asserted."""
    client = live_studio
    circle = await client.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "WpCircle"}
    )
    circle_id = circle.get("layer_id", "WpCircle")

    # Add waypoints at 0s and 2s
    await client.call(
        "anim.waypoint_set",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "time": 0.0,
            "value": {"type": "vector", "value": {"x": 0.0, "y": 0.0}},
            "interpolation": "linear",
        },
    )
    await client.call(
        "anim.waypoint_set",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "time": 2.0,
            "value": {"type": "vector", "value": {"x": 4.0, "y": 0.0}},
            "interpolation": "linear",
        },
    )

    # Remove waypoint at 2.0s
    rem_res = await client.call(
        "anim.waypoint_remove",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "time": 2.0,
        },
    )
    assert rem_res.get("param_name") == "origin"

    # Undo waypoint removal
    undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_res["success"] is True

    await client.call("layer.remove", {"doc_id": "doc_0", "layer_id": circle_id})


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_interpolation_set(live_studio: BridgeClient) -> None:
    """Requirement 1: anim.interpolation_set against real Studio with undo asserted."""
    client = live_studio
    circle = await client.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "InterpCircle"}
    )
    circle_id = circle.get("layer_id", "InterpCircle")

    await client.call(
        "anim.waypoint_set",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "time": 0.0,
            "value": {"type": "vector", "value": {"x": 0.0, "y": 0.0}},
            "interpolation": "linear",
        },
    )
    res = await client.call(
        "anim.interpolation_set",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "origin",
            "interpolation": "constant",
        },
    )
    assert res.get("interpolation") == "constant"

    undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_res["success"] is True

    await client.call("layer.remove", {"doc_id": "doc_0", "layer_id": circle_id})


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_param_export_unexport(live_studio: BridgeClient) -> None:
    """Requirement 1: param.export and param.unexport against real Studio with undo asserted."""
    client = live_studio
    circle = await client.call(
        "layer.add", {"doc_id": "doc_0", "layer_type": "circle", "description": "ExportCircle"}
    )
    circle_id = circle.get("layer_id", "ExportCircle")

    exp_res = await client.call(
        "param.export",
        {
            "doc_id": "doc_0",
            "layer_id": circle_id,
            "param_name": "radius",
            "name": "LiveExportedRadius",
        },
    )
    assert exp_res.get("name") == "LiveExportedRadius"

    unexp_res = await client.call(
        "param.unexport",
        {
            "doc_id": "doc_0",
            "name": "LiveExportedRadius",
        },
    )
    assert unexp_res.get("name") == "LiveExportedRadius"

    undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_res["success"] is True

    await client.call("layer.remove", {"doc_id": "doc_0", "layer_id": circle_id})


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_doc_set_time_range(live_studio: BridgeClient) -> None:
    """Requirement 1: doc.set_time_range against real Studio with undo asserted."""
    client = live_studio
    res = await client.call(
        "doc.set_time_range",
        {
            "doc_id": "doc_0",
            "start_time": 1.0,
            "end_time": 4.5,
            "fps": 30.0,
        },
    )
    assert abs(res["start_time"] - 1.0) < 0.05
    assert abs(res["end_time"] - 4.5) < 0.05
    assert abs(res["fps"] - 30.0) < 0.05

    undo_res = await client.call("history.undo", {"doc_id": "doc_0"})
    assert undo_res["success"] is True


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_render_sequence(live_studio: BridgeClient, tmp_path: Path) -> None:
    """Requirement 1: render_sequence against real Studio."""
    backend = LiveBackend(client=live_studio)
    seq_dir = tmp_path / "seq_live"
    frames = await backend.render_sequence(
        doc_id="doc_0",
        output_dir=str(seq_dir),
        start_time=0.0,
        end_time=0.5,
        fps=2.0,
        width=160,
        height=120,
    )
    assert len(frames) >= 2
    for f in frames:
        p = Path(f)
        assert p.exists()
        assert p.stat().st_size > 100


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_render_video(live_studio: BridgeClient, tmp_path: Path) -> None:
    """Requirement 1: render_video against real Studio (if ffmpeg present, else skip)."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not found on PATH")
    backend = LiveBackend(client=live_studio)
    video_path = tmp_path / "live_video.mp4"
    ok = await backend.render_video(
        doc_id="doc_0",
        output_path=str(video_path),
        start_time=0.0,
        end_time=0.5,
        fps=2.0,
        width=160,
        height=120,
    )
    assert ok is True
    assert video_path.exists()
    assert video_path.stat().st_size > 500


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_render_contact_sheet(live_studio: BridgeClient, tmp_path: Path) -> None:
    """Requirement 1: render_contact_sheet against real Studio."""
    backend = LiveBackend(client=live_studio)
    sheet_path = tmp_path / "live_sheet.png"
    ok = await backend.render_contact_sheet(
        doc_id="doc_0",
        output_path=str(sheet_path),
        cols=2,
        rows=1,
        width=160,
        height=120,
        start_time=0.0,
        end_time=0.5,
    )
    assert ok is True
    assert sheet_path.exists()
    assert sheet_path.stat().st_size > 100


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_render_progress_notifications(
    live_studio: BridgeClient, tmp_path: Path
) -> None:
    """Requirement 2: Hermetic progress test with cold cache asserting monotonic progress with N >= 5 frames."""
    backend = LiveBackend(client=live_studio)
    cold_cache = RenderCache(cache_dir=tmp_path / "cold_cache")
    pipeline = RenderPipeline(backend=backend, cache=cold_cache)
    events: list[tuple[int, int, float]] = []

    def on_progress(current: int, total: int, pct: float) -> None:
        events.append((current, total, pct))

    out_dir = tmp_path / "live_progress_seq"
    frames = await pipeline.render_sequence(
        doc_id="doc_0",
        output_dir=str(out_dir),
        start_time=0.0,
        end_time=1.0,
        fps=5.0,  # 6 frames (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
        width=160,
        height=120,
        progress_cb=on_progress,
    )
    assert len(frames) >= 5, f"Expected N >= 5 frames, got {len(frames)}"
    assert len(events) >= 5, f"Expected N >= 5 progress events, got {len(events)}"

    # Assert monotonic progress
    for i in range(1, len(events)):
        prev_curr, prev_tot, prev_pct = events[i - 1]
        curr_curr, curr_tot, curr_pct = events[i]
        assert curr_curr >= prev_curr, f"Non-monotonic frame count: {curr_curr} < {prev_curr}"
        assert curr_pct >= prev_pct, f"Non-monotonic percentage: {curr_pct} < {prev_pct}"
        assert curr_tot == len(frames)

    assert events[-1][0] == len(frames)
    assert events[-1][2] == 100.0


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_render_cancellation(live_studio: BridgeClient, tmp_path: Path) -> None:
    """Requirement 2: Cancellation test with long render mid-way, asserting partial output cleanup and reporting."""
    backend = LiveBackend(client=live_studio)
    cancel_cache = RenderCache(cache_dir=tmp_path / "cancel_cache")
    pipeline = RenderPipeline(backend=backend, cache=cancel_cache)

    # 1. With cleanup_on_cancel=True
    token1 = CancellationToken()

    def on_progress_cancel(current: int, _total: int, _pct: float) -> None:
        if current >= 2:
            token1.cancel()

    out_dir_cleanup = tmp_path / "live_cancel_cleaned"
    with pytest.raises(SynfigError, match="cancelled by user"):
        await pipeline.render_sequence(
            doc_id="doc_0",
            output_dir=str(out_dir_cleanup),
            start_time=0.0,
            end_time=1.0,
            fps=5.0,  # 6 frames total
            width=160,
            height=120,
            progress_cb=on_progress_cancel,
            cancel_token=token1,
            cleanup_on_cancel=True,
        )

    # Partial files should be cleaned up
    remaining = list(out_dir_cleanup.glob("*.png"))
    assert len(remaining) == 0, f"Expected 0 remaining files after cleanup, found {remaining}"

    # 2. With cleanup_on_cancel=False: assert fewer frames than requested were produced
    token2 = CancellationToken()

    def on_progress_cancel2(current: int, _total: int, _pct: float) -> None:
        if current >= 2:
            token2.cancel()

    out_dir_kept = tmp_path / "live_cancel_kept"
    with pytest.raises(SynfigError, match="cancelled by user"):
        await pipeline.render_sequence(
            doc_id="doc_0",
            output_dir=str(out_dir_kept),
            start_time=0.0,
            end_time=1.0,
            fps=5.0,  # 6 frames requested
            width=160,
            height=120,
            progress_cb=on_progress_cancel2,
            cancel_token=token2,
            cleanup_on_cancel=False,
        )

    produced = list(out_dir_kept.glob("*.png"))
    assert 0 < len(produced) < 6, (
        f"Expected fewer frames than requested (1..5), found {len(produced)}"
    )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_render_disk_cache(live_studio: BridgeClient, tmp_path: Path) -> None:
    """Requirement 2: Hermetic disk cache test showing cold=miss, repeat=hit, param/document change=miss."""
    backend = LiveBackend(client=live_studio)
    cache = RenderCache(cache_dir=tmp_path / "test_cache")
    pipeline = RenderPipeline(backend=backend, cache=cache)

    f1 = tmp_path / "frame_cold.png"
    f2 = tmp_path / "frame_repeat.png"
    f3 = tmp_path / "frame_param_change.png"
    f4 = tmp_path / "frame_doc_mutation.png"

    # 1. Cold render (expected MISS)
    print("\nCACHE TEST [Step 1]: Cold render at time=0.0s (expected MISS)")
    ok1 = await pipeline.render_cached_frame("doc_0", f1, time=0.0, width=160, height=120)
    assert ok1 is True
    assert f1.is_file()
    assert len(list(cache.cache_dir.glob("*.png"))) == 1
    print("CACHE TEST [Step 1 Result]: MISS verified -> cache entry created.")

    # 2. Repeat identical render (expected HIT)
    print("CACHE TEST [Step 2]: Repeat identical render at time=0.0s (expected HIT)")
    ok2 = await pipeline.render_cached_frame("doc_0", f2, time=0.0, width=160, height=120)
    assert ok2 is True
    assert f2.is_file()
    assert len(list(cache.cache_dir.glob("*.png"))) == 1
    print("CACHE TEST [Step 2 Result]: HIT verified -> served from disk cache without new render.")

    # 3. Parameter change (time=0.5s) (expected MISS)
    print("CACHE TEST [Step 3]: Parameter change to time=0.5s (expected MISS)")
    ok3 = await pipeline.render_cached_frame("doc_0", f3, time=0.5, width=160, height=120)
    assert ok3 is True
    assert f3.is_file()
    assert len(list(cache.cache_dir.glob("*.png"))) == 2
    print("CACHE TEST [Step 3 Result]: MISS verified -> new cache entry created.")

    # 4. Document mutation (modify circle layer in Studio) (expected MISS)
    print("CACHE TEST [Step 4]: Mutate document in Studio and render at time=0.0s (expected MISS)")
    await backend.layer_add(doc_id="doc_0", layer_type="circle")
    ok4 = await pipeline.render_cached_frame("doc_0", f4, time=0.0, width=160, height=120)
    assert ok4 is True
    assert f4.is_file()
    assert len(list(cache.cache_dir.glob("*.png"))) == 3
    print(
        "CACHE TEST [Step 4 Result]: MISS verified -> document state changed, new cache entry created."
    )


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_live_tools_path_sandbox_rejection(live_studio: BridgeClient, tmp_path: Path) -> None:
    """Security requirement: Path traversal and extension escapes via LiveBackend fail with typed SecuritySandboxError."""
    backend = LiveBackend(client=live_studio)
    sandbox_root = tmp_path / "sandbox_allowed"
    sandbox_root.mkdir()

    # 1. doc_open: outside sandbox rejection
    with pytest.raises(SecuritySandboxError, match="denied by workspace sandbox"):
        await backend.doc_open("C:/Windows/System32/drivers/etc/hosts.sif")

    # 2. doc_open: forbidden extension
    dummy_file = sandbox_root / "payload.exe"
    dummy_file.write_text("dummy", encoding="utf-8")
    with pytest.raises(SecuritySandboxError, match="not permitted"):
        await backend.doc_open(str(dummy_file))

    # 3. doc_save: outside sandbox rejection
    with pytest.raises(SecuritySandboxError, match="denied by workspace sandbox"):
        await backend.doc_save("doc_0", "C:/Windows/System32/hacked.sif")

    # 4. doc_save: forbidden extension
    with pytest.raises(SecuritySandboxError, match="not permitted"):
        await backend.doc_save("doc_0", str(sandbox_root / "escaped.bat"))

    # 5. render_frame: forbidden extension
    with pytest.raises(SecuritySandboxError, match="not permitted"):
        await backend.render_frame("doc_0", output_path=str(sandbox_root / "evil.ps1"))

    # 6. render_frame: outside sandbox rejection
    with pytest.raises(SecuritySandboxError, match="denied by workspace sandbox"):
        await backend.render_frame("doc_0", output_path="C:/Windows/System32/evil.png")

    # 7. render_sequence: outside sandbox rejection
    with pytest.raises(SecuritySandboxError, match="denied by workspace sandbox"):
        await backend.render_sequence("doc_0", output_dir="C:/Windows/System32/evil_seq")

    # 8. render_video: forbidden extension
    with pytest.raises(SecuritySandboxError, match="not permitted"):
        await backend.render_video("doc_0", output_path=str(sandbox_root / "video.exe"))

    # 9. render_contact_sheet: forbidden extension
    with pytest.raises(SecuritySandboxError, match="not permitted"):
        await backend.render_contact_sheet("doc_0", output_path=str(sandbox_root / "sheet.bin"))


@pytest.mark.real_studio
@pytest.mark.asyncio
async def test_bridge_direct_path_safety_rejection(
    live_studio: BridgeClient, tmp_path: Path
) -> None:
    """
    Security requirement 1: C++ bridge defense-in-depth rejects all 5 unsafe path categories:
    1. Absolute path outside root
    2. '..' directory traversal escape
    3. Symlink / junction escape
    4. Disallowed file extension
    5. Path inside root (must succeed)
    """
    inside_dir = tmp_path / "inside_workspace"
    inside_dir.mkdir(parents=True, exist_ok=True)

    # Configure bridge workspace roots to include repo root and tmp_path
    await live_studio.call(
        "hello",
        {
            "token": live_studio.token or "",
            "protocol_version": "1.0",
            "workspace_roots": [str(REPO_ROOT), str(tmp_path)],
        },
    )

    # -------------------------------------------------------------
    # Case 1: Absolute path outside root -> rejected (code 1203)
    # -------------------------------------------------------------
    with pytest.raises(SecurityError) as exc_abs_open:
        await live_studio.call("doc.open", {"file_path": "C:/Windows/System32/secret.sif"})
    assert exc_abs_open.value.code == 1203
    assert "outside configured workspace roots" in str(exc_abs_open.value).lower()

    with pytest.raises(SecurityError) as exc_abs_save:
        await live_studio.call(
            "doc.save", {"doc_id": "doc_0", "file_path": "C:/Windows/System32/hacked.sif"}
        )
    assert exc_abs_save.value.code == 1203
    assert "outside configured workspace roots" in str(exc_abs_save.value).lower()

    with pytest.raises(SecurityError) as exc_abs_render:
        await live_studio.call(
            "render.frame", {"doc_id": "doc_0", "output_path": "C:/Windows/System32/frame.png"}
        )
    assert exc_abs_render.value.code == 1203
    assert "outside configured workspace roots" in str(exc_abs_render.value).lower()

    # -------------------------------------------------------------
    # Case 2: '..' directory traversal escape -> rejected (code 1203)
    # -------------------------------------------------------------
    with pytest.raises(SecurityError) as exc_trav_open:
        await live_studio.call("doc.open", {"file_path": "../../secret.sif"})
    assert exc_trav_open.value.code == 1203
    assert "directory traversal" in str(exc_trav_open.value).lower()

    with pytest.raises(SecurityError) as exc_trav_save:
        await live_studio.call("doc.save", {"doc_id": "doc_0", "file_path": "../../hacked.sif"})
    assert exc_trav_save.value.code == 1203
    assert "directory traversal" in str(exc_trav_save.value).lower()

    with pytest.raises(SecurityError) as exc_trav_render:
        await live_studio.call(
            "render.frame", {"doc_id": "doc_0", "output_path": "../../frame.png"}
        )
    assert exc_trav_render.value.code == 1203
    assert "directory traversal" in str(exc_trav_render.value).lower()

    # -------------------------------------------------------------
    # Case 3: Symlink / junction escape -> rejected (code 1203)
    # -------------------------------------------------------------
    junction_dir = inside_dir / "external_junction"
    target_outside = Path("C:/Windows/System32")
    # Create NTFS directory junction pointing outside workspace
    subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(junction_dir), str(target_outside)],
        capture_output=True,
    )
    if junction_dir.exists():
        with pytest.raises(SecurityError) as exc_junc_open:
            await live_studio.call(
                "doc.open", {"file_path": str(junction_dir / "drivers" / "etc" / "hosts.sif")}
            )
        assert exc_junc_open.value.code == 1203
        assert "outside configured workspace roots" in str(exc_junc_open.value).lower()

        with pytest.raises(SecurityError) as exc_junc_save:
            await live_studio.call(
                "doc.save", {"doc_id": "doc_0", "file_path": str(junction_dir / "escaped.sif")}
            )
        assert exc_junc_save.value.code == 1203
        assert "outside configured workspace roots" in str(exc_junc_save.value).lower()

        with pytest.raises(SecurityError) as exc_junc_render:
            await live_studio.call(
                "render.frame",
                {"doc_id": "doc_0", "output_path": str(junction_dir / "escaped.png")},
            )
        assert exc_junc_render.value.code == 1203
        assert "outside configured workspace roots" in str(exc_junc_render.value).lower()

    # -------------------------------------------------------------
    # Case 4: Disallowed file extension -> rejected (code 1203)
    # -------------------------------------------------------------
    with pytest.raises(SecurityError) as exc_ext_open:
        await live_studio.call("doc.open", {"file_path": str(inside_dir / "payload.exe")})
    assert exc_ext_open.value.code == 1203
    assert "not permitted" in str(exc_ext_open.value).lower()

    with pytest.raises(SecurityError) as exc_ext_save:
        await live_studio.call(
            "doc.save", {"doc_id": "doc_0", "file_path": str(inside_dir / "payload.bat")}
        )
    assert exc_ext_save.value.code == 1203
    assert "not permitted" in str(exc_ext_save.value).lower()

    with pytest.raises(SecurityError) as exc_ext_render:
        await live_studio.call(
            "render.frame", {"doc_id": "doc_0", "output_path": str(inside_dir / "payload.sh")}
        )
    assert exc_ext_render.value.code == 1203
    assert "not permitted" in str(exc_ext_render.value).lower()

    # -------------------------------------------------------------
    # Case 5: Path inside root -> must succeed
    # -------------------------------------------------------------
    valid_render_path = inside_dir / "safe_output.png"
    res_render = await live_studio.call(
        "render.frame", {"doc_id": "doc_0", "output_path": str(valid_render_path)}
    )
    assert res_render.get("success") is True
    assert valid_render_path.is_file()
    assert valid_render_path.stat().st_size > 0
