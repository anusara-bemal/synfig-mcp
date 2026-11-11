"""
Shared harness for the live Synfig Studio end-to-end tests.

Launches the *patched* ``synfigstudio.exe``, waits for the MCP bridge token and
yields a connected :class:`BridgeClient`.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from synfig_mcp.protocol.client import BridgeClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "server" / "tests" / "fixtures"
SAMPLE_SIF = FIXTURES_DIR / "sample_project.sif"


def _resolve_studio_binary() -> Path | None:
    env_bin = os.environ.get("SYNFIG_STUDIO_PATH")
    if env_bin and Path(env_bin).exists():
        return Path(env_bin)
    for candidate in (
        REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe",
        REPO_ROOT / "build_synfig" / "build_linux" / "install" / "bin" / "synfigstudio",
    ):
        if candidate.exists():
            return candidate
    return None


BIN_PATH = _resolve_studio_binary()


def studio_env(**overrides: str) -> dict[str, str]:
    """Build an environment able to launch the *installed* Studio binary."""
    env = os.environ.copy()
    if BIN_PATH is not None and not BIN_PATH.name.endswith(".exe"):
        root = BIN_PATH.parent.parent
        lib_dir = str(root / "lib")
        existing_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing_ld}" if existing_ld else lib_dir
        env["SYNFIG_MODULE_DIR"] = str(root / "lib" / "synfig" / "modules")
        env.setdefault("SYNFIG_DATA_DIR", str(root / "share"))
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env.update(overrides)
    return env


def studio_log_tail(log_path: Path, limit: int = 6000) -> str:
    """Return the tail of a Studio log file for failure diagnostics."""
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception:
        return "<log unavailable>"


async def start_studio(
    port: int,
    tmp_path: Path,
    *,
    open_sample: bool = False,
) -> AsyncIterator[BridgeClient]:
    """Launch the patched Studio and yield a connected bridge client."""
    if BIN_PATH is None or not BIN_PATH.exists():
        pytest.skip("Patched Synfig Studio binary not found")

    env = studio_env(
        SYNFIG_MCP_ENABLE="1",
        SYNFIG_MCP_PORT=str(port),
        SYNFIG_DISABLE_AUTO_RECOVERY="1",
        SYNFIG_DISABLE_AUTO_SAVE="1",
    )

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    if token_dir.is_dir():
        for tf in token_dir.glob("mcp_token*"):
            with contextlib.suppress(Exception):
                tf.unlink()

    log_path = tmp_path / "studio_e2e.log"
    args = [str(BIN_PATH)]
    if open_sample and SAMPLE_SIF.exists():
        args.append(str(SAMPLE_SIF))

    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            args,
            env=env,
            stdout=log_file,
            stderr=log_file,
            cwd=str(BIN_PATH.parent),
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

        assert token, (
            "Session token was not created by Synfig Studio. "
            f"Binary: {BIN_PATH}\n--- Studio log ---\n{studio_log_tail(log_path)}"
        )

        client = BridgeClient(host="127.0.0.1", port=port, token=token, default_timeout=15.0)
        connected = False
        for _ in range(25):
            try:
                await client.connect()
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert connected, (
            f"Failed to connect to live bridge on port {port}\n"
            f"--- Studio log ---\n{studio_log_tail(log_path)}"
        )

        for _ in range(20):
            docs = await client.call("doc.list")
            if docs:
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


@pytest_asyncio.fixture
async def live_studio(tmp_path: Path) -> AsyncIterator[BridgeClient]:
    """Live Studio bridge client used by the end-to-end tests."""
    async for client in start_studio(19994, tmp_path):
        yield client
