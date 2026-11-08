"""
Benchmark comparing in-process Synfig Studio bridge rendering vs out-of-process CLI rendering.
Measures latency (median and p95) across N runs for single-frame 480p preview renders.
"""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add server/src to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "server" / "src"))

from synfig_mcp.protocol.client import BridgeClient  # noqa: E402


def get_machine_info() -> dict[str, str]:
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor() or "Unknown CPU",
        "arch": platform.machine(),
        "python": platform.python_version(),
    }


def find_synfig_cli() -> Path | None:
    found = shutil.which("synfig")
    if found:
        return Path(found)
    candidates = [
        REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfig.exe",
        Path("C:/Program Files/Synfig/bin/synfig.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def find_studio_bin() -> Path | None:
    candidates = [
        REPO_ROOT / "build_synfig" / "build_ucrt64" / "install" / "bin" / "synfigstudio.exe",
        Path("C:/Program Files/Synfig/bin/synfigstudio.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


async def run_benchmark(n_runs: int = 20) -> None:
    sample_sif = REPO_ROOT / "server" / "tests" / "fixtures" / "sample_project.sif"
    if not sample_sif.is_file():
        print(f"Error: sample project not found at {sample_sif}")
        sys.exit(1)

    synfig_cli = find_synfig_cli()
    studio_bin = find_studio_bin()

    info = get_machine_info()
    print("======================================================================")
    print("      Synfig MCP Render Benchmark: In-Process Bridge vs CLI           ")
    print("======================================================================")
    print(f"OS:           {info['os']}")
    print(f"CPU:          {info['cpu']}")
    print(f"Arch:         {info['arch']}")
    print(f"Python:       {info['python']}")
    print(f"Synfig CLI:   {synfig_cli}")
    print(f"Studio Bin:   {studio_bin}")
    print(f"N Runs:       {n_runs}")
    print("----------------------------------------------------------------------")

    # ------------------------------------------------------------------
    # 1. Benchmark Out-of-Process CLI Rendering
    # ------------------------------------------------------------------
    cli_times: list[float] = []
    if synfig_cli and synfig_cli.is_file():
        print(f"\n[1/2] Benchmarking CLI rendering ({synfig_cli.name}) for {n_runs} runs...")
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            for i in range(n_runs):
                out_png = tmp_path / f"cli_frame_{i}.png"
                t0 = time.perf_counter()
                res = subprocess.run(
                    [
                        str(synfig_cli),
                        str(sample_sif),
                        "-t", "png",
                        "-o", str(out_png),
                        "--width", "640",
                        "--height", "480",
                        "--time", "0s",
                    ],
                    capture_output=True,
                    text=True,
                )
                dt = (time.perf_counter() - t0) * 1000.0  # ms
                if res.returncode == 0 and out_png.is_file():
                    cli_times.append(dt)
                    print(f"  CLI Run {i+1:2d}/{n_runs}: {dt:6.2f} ms")
                else:
                    print(f"  CLI Run {i+1:2d}/{n_runs}: FAILED ({res.stderr[:80]})")
    else:
        print("\n[1/2] CLI not found. Skipping CLI benchmark.")

    # ------------------------------------------------------------------
    # 2. Benchmark In-Process Bridge Rendering
    # ------------------------------------------------------------------
    bridge_times: list[float] = []
    if studio_bin and studio_bin.is_file():
        print(f"\n[2/2] Benchmarking In-Process Bridge ({studio_bin.name}) for {n_runs} runs...")
        test_port = 19999
        env = os.environ.copy()
        env["SYNFIG_MCP_PORT"] = str(test_port)
        env["MSYS2_ARG_CONV_EXCL"] = "*"
        env["SYNFIG_DISABLE_AUTO_RECOVERY"] = "1"
        env["SYNFIG_DISABLE_AUTO_SAVE"] = "1"

        token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
        token_path = token_dir / "mcp_token"
        if token_path.exists():
            token_path.unlink()

        proc = subprocess.Popen(
            [str(studio_bin), str(sample_sif)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(studio_bin.parent),
        )

        try:
            # Wait for token
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

            if not token:
                raise RuntimeError("Failed to acquire studio mcp_token")

            client = BridgeClient(host="127.0.0.1", port=test_port, token=token, default_timeout=10.0)
            connected = False
            for _ in range(25):
                try:
                    await client.connect()
                    connected = True
                    break
                except Exception:
                    await asyncio.sleep(0.5)

            if not connected:
                raise RuntimeError("Failed to connect to running bridge")

            # Wait for doc initialization
            for _ in range(20):
                docs = await client.call("doc.list")
                if docs:
                    break
                await asyncio.sleep(0.5)

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                for i in range(n_runs):
                    out_png = tmp_path / f"bridge_frame_{i}.png"
                    t0 = time.perf_counter()
                    res = await client.call(
                        "canvas.render_frame",
                        {
                            "doc_id": "doc_0",
                            "output_path": str(out_png),
                            "time": 0.0,
                            "width": 640,
                            "height": 480,
                        },
                    )
                    dt = (time.perf_counter() - t0) * 1000.0  # ms
                    if res.get("success") and out_png.is_file():
                        bridge_times.append(dt)
                        print(f"  Bridge Run {i+1:2d}/{n_runs}: {dt:6.2f} ms")
                    else:
                        print(f"  Bridge Run {i+1:2d}/{n_runs}: FAILED")

            await client.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    else:
        print("\n[2/2] Patched Studio binary not found. Skipping bridge benchmark.")

    # ------------------------------------------------------------------
    # Results Summary
    # ------------------------------------------------------------------
    print("\n======================================================================")
    print("                         Benchmark Summary                            ")
    print("======================================================================")

    def stats(times: list[float]) -> tuple[float, float, float, float]:
        if not times:
            return 0.0, 0.0, 0.0, 0.0
        sorted_t = sorted(times)
        p95_idx = int(0.95 * len(sorted_t)) - 1
        p95 = sorted_t[max(0, p95_idx)]
        return min(times), statistics.median(times), p95, max(times)

    cli_min, cli_med, cli_p95, cli_max = stats(cli_times)
    br_min, br_med, br_p95, br_max = stats(bridge_times)

    print(f"CLI Rendering ({len(cli_times)} valid runs):")
    print(f"  Min:    {cli_min:6.2f} ms")
    print(f"  Median: {cli_med:6.2f} ms")
    print(f"  p95:    {cli_p95:6.2f} ms")
    print(f"  Max:    {cli_max:6.2f} ms")

    print(f"\nIn-Process Bridge Rendering ({len(bridge_times)} valid runs):")
    print(f"  Min:    {br_min:6.2f} ms")
    print(f"  Median: {br_med:6.2f} ms")
    print(f"  p95:    {br_p95:6.2f} ms")
    print(f"  Max:    {br_max:6.2f} ms")

    if br_med > 0 and cli_med > 0:
        ratio = cli_med / br_med
        print(f"\nRatio: In-Process Bridge is {ratio:.2f}x faster for single-frame previews.")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(run_benchmark(n_runs=20))
