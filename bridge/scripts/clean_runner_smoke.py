#!/usr/bin/env python3
"""
Clean-runner smoke test for Synfig Studio MCP bridge.
Executed in clean CI runner environments without MSYS2/build dependencies to verify:
1. Application launching and dynamic library resolution
2. Bridge TCP listener startup and auth token generation
3. hello handshake
4. doc.new document creation
5. layer.add layer insertion
6. render.frame headless frame render to valid PNG
"""

import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def recv_json(sock: socket.socket) -> dict:
    buf = ""
    while "\n" not in buf:
        chunk = sock.recv(4096).decode("utf-8")
        if not chunk:
            break
        buf += chunk
    return json.loads(buf.strip())


def send_req(sock: socket.socket, req_id: int, method: str, params: dict) -> dict:
    msg = json.dumps({"id": req_id, "method": method, "params": params}) + "\n"
    sock.sendall(msg.encode("utf-8"))
    return recv_json(sock)


def run_smoke_test(studio_exe: Path) -> None:
    print(f"=== Starting Clean Runner Smoke Test with {studio_exe} ===")
    assert studio_exe.is_file(), f"Binary not found: {studio_exe}"

    # Prepare temp workspace root
    temp_dir = Path(tempfile.mkdtemp(prefix="synfig_smoke_"))
    doc_root = temp_dir / "workspace"
    doc_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["SYNFIG_MCP_ENABLE"] = "1"
    env["SYNFIG_MCP_PORT"] = "20002"
    env["SYNFIG_MCP_WORKSPACE_ROOTS"] = str(doc_root)
    env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
    env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"
    env["MSYS2_ARG_CONV_EXCL"] = "*"

    # Add bin directory of studio to PATH so DLLs resolve on Windows
    bin_dir = str(studio_exe.parent.resolve())
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    # Clean stale default token file before launching
    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    default_token = token_dir / "mcp_token"
    if default_token.exists():
        try:
            default_token.unlink()
        except Exception:
            pass

    log_file = open(temp_dir / "studio_smoke.log", "w", encoding="utf-8")
    print(f"Launching {studio_exe} (logging to {log_file.name})...", flush=True)
    proc = subprocess.Popen(
        [str(studio_exe)],
        env=env,
        stdout=log_file,
        stderr=log_file,
        cwd=bin_dir,
    )

    try:
        # Find token file
        token = ""
        token_file = None
        for attempt in range(40):
            time.sleep(0.5)
            pid_token = token_dir / f"mcp_token_{proc.pid}"
            candidates = [pid_token, default_token]
            for tf in candidates:
                if tf.is_file() and tf.stat().st_size > 0:
                    t = tf.read_text(encoding="utf-8").strip()
                    if t:
                        token = t
                        token_file = tf
                        break
            if token:
                break

        assert token, f"Bridge did not generate authentication token after 20 seconds. Returncode: {proc.poll()}"
        print(f"[PASS] Bridge started and generated auth token in {token_file.name}")

        # Connect TCP socket
        sock = None
        target_port = int(env.get("SYNFIG_MCP_PORT", "19998"))
        candidate_ports = [target_port] + [p for p in range(19998, 20008) if p != target_port]

        print(f"Connecting to bridge socket (probing candidate ports)...")
        for _ in range(30):
            for port in candidate_ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                try:
                    s.connect(("127.0.0.1", port))
                    sock = s
                    target_port = port
                    break
                except (ConnectionRefusedError, TimeoutError, OSError):
                    s.close()
            if sock:
                break
            time.sleep(0.5)

        assert sock, "Could not connect to bridge TCP socket on any port 19998..20007"
        sock.settimeout(10.0)
        print(f"[PASS] Connected to bridge TCP socket on 127.0.0.1:{target_port}")

        # 1. hello
        hello_resp = send_req(
            sock,
            1,
            "hello",
            {
                "client_name": "clean-runner-smoke",
                "protocol_version": "1.0",
                "token": token,
                "workspace_roots": [str(doc_root)],
            },
        )
        assert "result" in hello_resp, f"hello failed: {hello_resp}"
        res = hello_resp["result"]
        print(f"[PASS] hello handshake succeeded: version={res.get('bridge_version')} commit={res.get('commit_sha')}")

        # 2. doc.new
        doc_resp = send_req(sock, 2, "doc.new", {"name": "smoke_test_doc"})
        assert "result" in doc_resp, f"doc.new failed: {doc_resp}"
        doc_id = doc_resp["result"]["doc_id"]
        print(f"[PASS] doc.new created document with doc_id={doc_id}")

        # 3. layer.add
        layer_resp = send_req(
            sock,
            3,
            "layer.add",
            {
                "doc_id": doc_id,
                "layer_type": "circle",
            },
        )
        assert "result" in layer_resp, f"layer.add failed: {layer_resp}"
        layer_name = layer_resp["result"].get("layer_name", "Circle")
        print(f"[PASS] layer.add created circle layer: {layer_name}")

        # 4. render.frame
        out_png = doc_root / "smoke_frame.png"
        render_resp = send_req(
            sock,
            4,
            "render.frame",
            {
                "doc_id": doc_id,
                "output_path": str(out_png),
                "time": 0.0,
                "width": 128,
                "height": 128,
            },
        )
        assert "result" in render_resp, f"render.frame failed: {render_resp}"
        assert out_png.is_file(), f"Rendered output PNG does not exist at {out_png}"
        size_bytes = out_png.stat().st_size
        assert size_bytes > 0, f"Rendered output PNG is empty (0 bytes)"
        print(f"[PASS] render.frame rendered valid PNG ({size_bytes} bytes)")

        # 5. doc.close
        close_resp = send_req(sock, 5, "doc.close", {"doc_id": doc_id, "force": True})
        assert "result" in close_resp, f"doc.close failed: {close_resp}"
        print(f"[PASS] doc.close cleanly closed document {doc_id}")

        sock.close()
        print("=== ALL CLEAN RUNNER SMOKE TESTS PASSED ===")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        binary_path = Path(sys.argv[1])
    else:
        # Default local dev path
        if platform.system().lower() == "windows":
            binary_path = Path("build_synfig/build_ucrt64/install/bin/synfigstudio.exe")
        else:
            binary_path = Path("build_synfig/build_linux/install/bin/synfigstudio")

    run_smoke_test(binary_path)
