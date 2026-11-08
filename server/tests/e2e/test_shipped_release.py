"""
Test that downloads the shipped binary from the GitHub release and verifies
that the bridge handshake ('hello') reports the exact tag commit SHA.
"""

import json
import os
import platform
import socket
import subprocess
import tarfile
import time
import zipfile
from pathlib import Path

import pytest


@pytest.mark.skipif(
    os.environ.get("SYNFIG_TEST_SHIPPED_RELEASE") != "1",
    reason="Requires SYNFIG_TEST_SHIPPED_RELEASE=1 to download and verify release binaries",
)
def test_shipped_binary_reports_tag_commit(tmp_path: Path) -> None:
    tag = os.environ.get("SYNFIG_RELEASE_TAG", "v0.7.0-rc3")
    expected_sha = os.environ.get("SYNFIG_EXPECTED_COMMIT_SHA")

    if not expected_sha:
        # Resolve tag commit via git or gh api
        try:
            expected_sha = subprocess.check_output(
                ["git", "rev-parse", tag],
                text=True,
            ).strip()
        except Exception:
            pytest.skip(f"Could not resolve commit SHA for tag {tag}")

    # Determine asset name for current OS
    system = platform.system().lower()
    if system == "windows":
        asset_pattern = "synfigstudio-windows-ucrt64-mcp-*.zip"
    else:
        asset_pattern = "synfigstudio-linux-mcp-*.tar.gz"

    # Download release asset using gh CLI or direct GitHub API
    download_dir = tmp_path / "shipped_download"
    download_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading release assets for tag {tag}...")
    subprocess.run(
        ["gh", "release", "download", tag, "--pattern", asset_pattern, "--dir", str(download_dir)],
        check=True,
    )

    downloaded_files = list(download_dir.glob("*.zip")) + list(download_dir.glob("*.tar.gz"))
    assert downloaded_files, f"No release assets matching {asset_pattern} found in {download_dir}"
    asset_file = downloaded_files[0]

    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    if asset_file.suffix == ".zip":
        with zipfile.ZipFile(asset_file, "r") as z:
            z.extractall(extract_dir)
    else:
        with tarfile.open(asset_file, "r:*") as t:
            t.extractall(extract_dir)

    # Locate synfigstudio executable
    studio_candidates = list(extract_dir.rglob("synfigstudio.exe")) + list(
        extract_dir.rglob("synfigstudio")
    )
    studio_exe = None
    for cand in studio_candidates:
        if cand.is_file() and not cand.name.endswith(".zip"):
            studio_exe = cand
            break

    assert studio_exe and studio_exe.is_file(), (
        f"synfigstudio executable not found in extracted asset: {list(extract_dir.rglob('*'))}"
    )

    # Launch the extracted shipped studio binary
    test_port = 20005
    env = os.environ.copy()
    env["SYNFIG_MCP_ENABLE"] = "1"
    env["SYNFIG_MCP_PORT"] = str(test_port)

    # In clean Windows runner, ensure bundled bin is on PATH so DLLs resolve
    bin_dir = str(studio_exe.parent)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    log_path = tmp_path / "studio_shipped.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(studio_exe)],
            env=env,
            stdout=log_file,
            stderr=log_file,
        )

    try:
        # Wait for bridge to listen and find token
        token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
        token = ""
        for _ in range(30):
            token_candidates = list(token_dir.glob(f"mcp_token_{proc.pid}")) + list(
                token_dir.glob("mcp_token")
            )
            for tf in token_candidates:
                if tf.is_file() and tf.stat().st_size > 0:
                    token = tf.read_text(encoding="utf-8").strip()
                    if token:
                        break
            if token:
                break
            time.sleep(0.5)

        assert token, "Bridge did not create session token in time"

        # Connect to bridge socket and send hello
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", test_port))

        req = (
            json.dumps(
                {
                    "id": 1,
                    "method": "hello",
                    "params": {
                        "client_name": "test-shipped-release",
                        "protocol_version": "1.0",
                        "token": token,
                    },
                }
            )
            + "\n"
        )
        sock.sendall(req.encode("utf-8"))

        resp_raw = sock.recv(4096).decode("utf-8")
        sock.close()

        resp = json.loads(resp_raw)
        assert "result" in resp, f"hello handshake error: {resp}"
        result = resp["result"]

        reported_commit = result.get("commit_sha", "")
        print(f"Shipped binary reported commit SHA: {reported_commit}")
        print(f"Expected commit SHA: {expected_sha}")

        # Assert tag commit matches
        assert reported_commit == expected_sha or expected_sha.startswith(reported_commit), (
            f"Shipped binary commit mismatch: reported '{reported_commit}' vs expected '{expected_sha}'"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
