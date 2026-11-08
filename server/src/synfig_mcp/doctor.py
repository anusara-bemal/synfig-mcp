"""
System diagnostic utility for synfig-mcp.
Checks Studio binary, bridge responsiveness, token file ACL, synfig CLI, ffmpeg, and configuration.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    status: str  # PASS, WARN, FAIL, INFO
    message: str
    hint: str | None = None


def check_studio_binary() -> CheckResult:
    custom_path = os.environ.get("SYNFIG_STUDIO_PATH")
    if custom_path and Path(custom_path).is_file():
        return CheckResult(
            name="Synfig Studio Binary",
            status="PASS",
            message=f"Found via SYNFIG_STUDIO_PATH: {custom_path}",
        )

    found = shutil.which("synfigstudio")
    if found:
        return CheckResult(
            name="Synfig Studio Binary",
            status="PASS",
            message=f"Found on PATH: {found}",
        )

    # Search common development / installation paths
    candidate_paths = [
        Path("build_synfig/build_ucrt64/install/bin/synfigstudio.exe"),
        Path("../build_synfig/build_ucrt64/install/bin/synfigstudio.exe"),
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files"))
        / "Synfig"
        / "bin"
        / "synfigstudio.exe",
        Path("/usr/bin/synfigstudio"),
        Path("/usr/local/bin/synfigstudio"),
    ]
    for p in candidate_paths:
        if p.is_file():
            return CheckResult(
                name="Synfig Studio Binary",
                status="PASS",
                message=f"Found at: {p.resolve()}",
            )

    return CheckResult(
        name="Synfig Studio Binary",
        status="WARN",
        message="synfigstudio binary not found in standard paths",
        hint="Install Synfig Studio or set the SYNFIG_STUDIO_PATH environment variable.",
    )


def check_synfig_cli() -> CheckResult:
    found = shutil.which("synfig")
    if found:
        return CheckResult(
            name="Synfig CLI",
            status="PASS",
            message=f"Found on PATH: {found}",
        )

    candidate_paths = [
        Path("build_synfig/build_ucrt64/install/bin/synfig.exe"),
        Path("../build_synfig/build_ucrt64/install/bin/synfig.exe"),
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Synfig" / "bin" / "synfig.exe",
        Path("/usr/bin/synfig"),
        Path("/usr/local/bin/synfig"),
    ]
    for p in candidate_paths:
        if p.is_file():
            return CheckResult(
                name="Synfig CLI",
                status="PASS",
                message=f"Found at: {p.resolve()}",
            )

    return CheckResult(
        name="Synfig CLI",
        status="WARN",
        message="synfig CLI binary not found",
        hint="Add Synfig's bin/ directory to PATH for out-of-process rendering support.",
    )


def check_ffmpeg() -> CheckResult:
    found = shutil.which("ffmpeg")
    if found:
        return CheckResult(
            name="FFmpeg",
            status="PASS",
            message=f"Found on PATH: {found}",
        )
    return CheckResult(
        name="FFmpeg",
        status="WARN",
        message="ffmpeg not found on PATH",
        hint="Install ffmpeg to enable render_video functionality (e.g. winget install Gyan.FFmpeg or apt install ffmpeg).",
    )


def check_token_file() -> CheckResult:
    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token_path = token_dir / "mcp_token"

    if not token_path.exists():
        return CheckResult(
            name="Token File ACL",
            status="INFO",
            message=f"Token file does not exist yet ({token_path})",
            hint="Synfig Studio creates this file automatically with owner-only ACL on launch.",
        )

    if os.name == "nt":
        try:
            res = subprocess.run(
                ["icacls", str(token_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            out = res.stdout
            if "(I)" in out:
                return CheckResult(
                    name="Token File ACL",
                    status="FAIL",
                    message="Token file inherits permissions from parent directory",
                    hint="Remove inheritance and grant owner-only permissions: icacls <token> /inheritance:r /grant:r %USERNAME%:F",
                )
            if ":(F)" not in out and ":(M)" not in out:
                return CheckResult(
                    name="Token File ACL",
                    status="WARN",
                    message="Owner permissions could not be fully verified via icacls",
                )
            return CheckResult(
                name="Token File ACL",
                status="PASS",
                message=f"Owner-only Win32 ACL verified (inheritance disabled): {token_path}",
            )
        except Exception as e:
            return CheckResult(
                name="Token File ACL",
                status="WARN",
                message=f"Could not inspect Win32 ACL: {e}",
            )
    else:
        mode = token_path.stat().st_mode & 0o777
        if mode & 0o077 != 0:
            return CheckResult(
                name="Token File ACL",
                status="FAIL",
                message=f"Token file permissions too open: {oct(mode)}",
                hint=f"Restrict file permissions to owner-only: chmod 600 {token_path}",
            )
        return CheckResult(
            name="Token File ACL",
            status="PASS",
            message=f"Owner-only permissions verified ({oct(mode)}): {token_path}",
        )


def check_bridge_connection() -> CheckResult:
    host = os.environ.get("SYNFIG_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("SYNFIG_MCP_PORT", "19991"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        sock.connect((host, port))
        sock.close()
        return CheckResult(
            name="Bridge Connectivity",
            status="PASS",
            message=f"Bridge TCP socket responding at {host}:{port}",
        )
    except (ConnectionRefusedError, TimeoutError, OSError):
        return CheckResult(
            name="Bridge Connectivity",
            status="INFO",
            message=f"No active bridge listening on {host}:{port}",
            hint="Launch Synfig Studio to enable the live bridge. If Studio is not running, synfig-mcp runs in headless mode.",
        )


def check_config() -> CheckResult:
    backend = os.environ.get("SYNFIG_MCP_BACKEND", "auto")
    port = os.environ.get("SYNFIG_MCP_PORT", "19991")
    host = os.environ.get("SYNFIG_MCP_HOST", "127.0.0.1")

    valid_backends = {"auto", "live", "headless"}
    if backend not in valid_backends:
        return CheckResult(
            name="Configuration",
            status="FAIL",
            message=f"Invalid SYNFIG_MCP_BACKEND='{backend}'. Must be one of: {valid_backends}",
            hint="Set SYNFIG_MCP_BACKEND=auto or live or headless.",
        )

    try:
        p_val = int(port)
        if not (1 <= p_val <= 65535):
            raise ValueError()
    except ValueError:
        return CheckResult(
            name="Configuration",
            status="FAIL",
            message=f"Invalid SYNFIG_MCP_PORT='{port}'. Must be a valid port number 1-65535.",
        )

    return CheckResult(
        name="Configuration",
        status="PASS",
        message=f"Valid (backend={backend}, host={host}, port={port})",
    )


def run_doctor() -> int:
    """Run all diagnostics, print report, and return exit code."""
    checks = [
        check_studio_binary(),
        check_bridge_connection(),
        check_token_file(),
        check_synfig_cli(),
        check_ffmpeg(),
        check_config(),
    ]

    print("==================================================")
    print("           synfig-mcp System Doctor               ")
    print("==================================================")

    has_fail = False
    for c in checks:
        if c.status == "PASS":
            prefix = "[PASS] "
        elif c.status == "WARN":
            prefix = "[WARN] "
        elif c.status == "INFO":
            prefix = "[INFO] "
        else:
            prefix = "[FAIL] "
            has_fail = True

        print(f"{prefix}{c.name}: {c.message}")
        if c.hint:
            print(f"       -> Fix Hint: {c.hint}")

    print("--------------------------------------------------")
    if has_fail:
        print("Doctor status: FAILED. Please resolve the errors above.")
        return 1

    print("Doctor status: OK. synfig-mcp is ready for operation.")
    return 0


if __name__ == "__main__":
    sys.exit(run_doctor())
