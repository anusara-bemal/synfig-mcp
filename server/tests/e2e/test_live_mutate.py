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
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from synfig_mcp.protocol.client import BridgeClient

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

    # -------------------------------------------------------------
    # 7. Requirement A: anim.time.set
    # -------------------------------------------------------------
    t_res = await client.call("anim.time.set", {"doc_id": "doc_0", "time": 2.25})
    assert abs(t_res["time"]["seconds"] - 2.25) < 0.01
    curr = await client.call("anim.time.get", {"doc_id": "doc_0"})
    assert abs(curr["time"]["seconds"] - 2.25) < 0.01

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
