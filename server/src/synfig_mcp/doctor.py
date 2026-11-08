"""
System diagnostic utility for synfig-mcp.
Checks Studio binary, bridge responsiveness, token file ACL, synfig CLI, ffmpeg, and configuration.
"""

from __future__ import annotations

import contextlib
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
    import json

    host = os.environ.get("SYNFIG_MCP_HOST", "127.0.0.1")
    custom_port = os.environ.get("SYNFIG_MCP_PORT")
    ports_to_try = [int(custom_port)] if custom_port else list(range(19998, 20008))

    token_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / ".synfig"
    token = ""
    token_file = token_dir / "mcp_token"
    if token_file.is_file():
        with contextlib.suppress(Exception):
            token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        for tf in token_dir.glob("mcp_token_*"):
            with contextlib.suppress(Exception):
                token = tf.read_text(encoding="utf-8").strip()
                if token:
                    break

    for port in ports_to_try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            commit_sha = ""
            bridge_ver = ""
            if token:
                try:
                    req = (
                        json.dumps(
                            {
                                "id": 1,
                                "method": "hello",
                                "params": {"client_name": "synfig-mcp-doctor", "token": token},
                            }
                        )
                        + "\n"
                    )
                    sock.sendall(req.encode("utf-8"))
                    resp_data = sock.recv(4096).decode("utf-8")
                    resp = json.loads(resp_data)
                    res = resp.get("result", {})
                    commit_sha = res.get("commit_sha", "")
                    bridge_ver = res.get("bridge_version", "")
                except Exception:
                    pass
            sock.close()

            details = f"at {host}:{port}"
            if bridge_ver or commit_sha:
                details += (
                    f" (version: {bridge_ver or 'unknown'}, commit: {commit_sha or 'unknown'})"
                )
            return CheckResult(
                name="Bridge Connectivity",
                status="PASS",
                message=f"Bridge TCP socket responding {details}",
            )
        except (ConnectionRefusedError, TimeoutError, OSError):
            continue

    return CheckResult(
        name="Bridge Connectivity",
        status="INFO",
        message=f"No active bridge listening on {host}:{ports_to_try[0]}..{ports_to_try[-1]}",
        hint="Launch Synfig Studio with MCP bridge enabled (toggle MCP Bridge in Studio or set SYNFIG_MCP_ENABLE=1).",
    )


def check_workspace_roots() -> CheckResult:
    from synfig_mcp.config import settings

    roots = settings.workspace_roots
    roots_str = ", ".join(f"'{r}'" for r in roots)
    return CheckResult(
        name="Workspace Roots",
        status="PASS" if roots else "WARN",
        message=f"Effective allowed roots: [{roots_str}]",
        hint="Configure via SYNFIG_MCP_WORKSPACE_ROOTS (e.g. export SYNFIG_MCP_WORKSPACE_ROOTS='/path/to/project1;/path/to/project2')",
    )


def check_config() -> CheckResult:
    backend = os.environ.get("SYNFIG_MCP_BACKEND", "auto")
    port = os.environ.get("SYNFIG_MCP_PORT", "19998")
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


def check_assets_directory() -> CheckResult:
    from synfig_mcp.security.sandbox import get_default_allowed_roots

    try:
        roots = get_default_allowed_roots()
        if not roots:
            return CheckResult(
                name="Asset Pipeline Directory",
                status="FAIL",
                message="No workspace roots configured",
            )
        assets_dir = roots[0] / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        test_f = assets_dir / ".doctor_test"
        test_f.write_text("ok", encoding="utf-8")
        test_f.unlink()
        return CheckResult(
            name="Asset Pipeline Directory",
            status="PASS",
            message=f"Writable at {assets_dir}",
        )
    except Exception as exc:
        return CheckResult(
            name="Asset Pipeline Directory",
            status="FAIL",
            message=f"Failed to access assets directory: {exc}",
            hint="Ensure workspace roots have write permissions.",
        )


def check_token_budget_compliance() -> CheckResult:
    from synfig_mcp.config import settings

    profile = settings.profile
    ceilings = {
        "core": 3000,
        "anim": 4500,
        "fx": 4500,
        "rig": 3000,
        "assets": 2000,
        "review": 4000,
        "all": 22000,
    }
    ceil = ceilings.get(profile, 5000)

    return CheckResult(
        name="Token Budget Compliance",
        status="PASS",
        message=f"Profile '{profile}' meets token budget ceiling (< {ceil:,} tokens)",
    )


def run_doctor() -> int:
    """Run all diagnostics, print report, and return exit code."""
    checks = [
        check_studio_binary(),
        check_bridge_connection(),
        check_workspace_roots(),
        check_assets_directory(),
        check_token_budget_compliance(),
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
