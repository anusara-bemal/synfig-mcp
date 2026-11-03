# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Locate and probe the synfig binary (env var → PATH → OS defaults)."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

WINDOWS_DEFAULTS = [
    r"C:\Program Files\Synfig\bin\synfig.exe",
    r"C:\Program Files (x86)\Synfig\bin\synfig.exe",
]
MACOS_DEFAULTS = [
    "/Applications/SynfigStudio.app/Contents/MacOS/synfig",
    "/Applications/Synfig.app/Contents/MacOS/synfig",
    "/usr/local/bin/synfig",
    "/opt/homebrew/bin/synfig",
    "/opt/local/bin/synfig",
]
LINUX_DEFAULTS = [
    "/usr/bin/synfig",
    "/usr/local/bin/synfig",
    "/opt/synfig/bin/synfig",
    "/var/lib/flatpak/exports/bin/org.synfig.SynfigStudio",
    "/var/lib/flatpak/exports/bin/synfig",
]
FLATPAK_APP_ID = "org.synfig.SynfigStudio"

_NOISE = re.compile(
    r"^(synfig\(\d+\)\s*)?(\[[0-9: ]+\]\s*)?(info|warning|error)\s*:", re.IGNORECASE
)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LOADING = re.compile(r"^(Loading\b|Unable to find module|synfig\(\d+\))", re.IGNORECASE)


def default_candidates() -> list[str]:
    system = platform.system()
    if system == "Windows":
        return list(WINDOWS_DEFAULTS)
    if system == "Darwin":
        return list(MACOS_DEFAULTS)
    return list(LINUX_DEFAULTS)


def find_synfig_binary(env_synfig_bin: str | None) -> str | None:
    if env_synfig_bin:
        candidate = Path(env_synfig_bin).expanduser()
        if candidate.is_file():
            return str(candidate)
        return env_synfig_bin  # reported as configured-but-missing
    which = shutil.which("synfig")
    if which:
        return which
    if platform.system() == "Windows":
        which_exe = shutil.which("synfig.exe")
        if which_exe:
            return which_exe
    for default_path in default_candidates():
        if Path(default_path).is_file():
            return default_path
    return None


def clean_synfig_output(text: str) -> list[str]:
    """Strip loading chatter from synfig output; keep content lines."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = _ANSI.sub("", raw).rstrip()
        if not line.strip():
            continue
        if _LOADING.match(line):
            continue
        if _NOISE.match(line):
            continue
        lines.append(line)
    return lines


def raw_command(binary: str, args: list[str], *, timeout: float = 30.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - binary path is resolved and validated
            [binary, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return -1, "", f"synfig did not respond within {timeout:.0f}s"
    except OSError as exc:
        return -1, "", str(exc)
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    return proc.returncode, stdout, stderr


def parse_version(output: str) -> str | None:
    match = re.search(
        r"synfig\s*(?:studio)?\s+([0-9]+(?:\.[0-9]+)*(?:[-+._a-zA-Z0-9]*)?)",
        output,
        re.IGNORECASE,
    )
    return f"synfig {match.group(1)}" if match else None


def probe_synfig(binary: str | None, *, timeout: float = 30.0) -> dict[str, Any]:
    """Collect version/targets/renderers/layers from the binary (cached by caller)."""
    if not binary or not Path(binary).is_file():
        return {
            "found": False,
            "path": binary,
            "version": None,
            "targets": [],
            "renderers": [],
            "layers": [],
            "valuenodes": [],
            "problems": [
                "synfig binary not found or not executable",
                "set SYNFIG_BIN to the full path of the synfig executable",
            ],
        }

    rc_v, out_v, err_v = raw_command(binary, ["--version"], timeout=timeout)
    _rc_t, out_t, _ = raw_command(binary, ["--targets"], timeout=timeout)
    _rc_r, out_r, _ = raw_command(binary, ["--renderers"], timeout=timeout)
    _rc_l, out_l, _ = raw_command(binary, ["--layers"], timeout=timeout)
    _rc_n, out_n, _ = raw_command(binary, ["--valuenodes"], timeout=timeout)

    problems: list[str] = []

    def content_lines(text: str) -> list[str]:
        return [line.strip() for line in clean_synfig_output(text) if line.strip()]

    version = parse_version(out_v + "\n" + err_v)
    targets = content_lines(out_t)
    renderers = content_lines(out_r)
    layers = content_lines(out_l)
    valuenodes = content_lines(out_n)

    if rc_v != 0 and version is None:
        problems.append(f"synfig --version exited with code {rc_v}: {err_v.strip()[:200]}")
    if not targets:
        problems.append("synfig --targets produced no targets (the installation looks broken)")
    if not version:
        problems.append("could not parse the synfig version string")

    return {
        "found": True,
        "path": binary,
        "version": version,
        "targets": targets,
        "renderers": renderers,
        "layers": layers,
        "valuenodes": valuenodes,
        "flatpak_hint": _flatpak_hint(),
        "problems": problems,
    }


def _flatpak_hint() -> str | None:
    system = platform.system()
    if system == "Linux" and shutil.which("flatpak"):
        return (
            "flatpak is installed; if synfig is only available via flatpak, set "
            f"SYNFIG_BIN='/var/lib/flatpak/exports/bin/{FLATPAK_APP_ID}'"
        )
    return None


def supports_flag(help_text: str, flag: str) -> bool:
    return flag in help_text


def renderers_available(probed: dict[str, Any], renderer: str) -> bool:
    return renderer in probed.get("renderers", [])
