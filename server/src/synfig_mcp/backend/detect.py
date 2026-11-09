"""Best-effort detection of a running Synfig Studio process.

The MCP bridge is opt-in, so Studio can be running with its bridge disabled.
Detecting the process lets ``auto`` backend selection avoid silently creating
invisible headless documents when the user expects edits in the open window.
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def is_studio_running(timeout: float = 3.0) -> bool:
    """Return True when a Synfig Studio process appears to be running.

    Detection is advisory: it only distinguishes "Studio is open" from "no
    Studio", so a false negative degrades to the previous behaviour instead of
    breaking the server.
    """
    try:
        if sys.platform == "win32":
            return _windows_studio_running(timeout)
        return _posix_studio_running(timeout)
    except Exception:
        return False


def _windows_studio_running(timeout: float) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq synfigstudio.exe", "/NH"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return "synfigstudio.exe" in result.stdout.lower()


def _posix_studio_running(timeout: float) -> bool:
    pgrep = shutil.which("pgrep")
    if pgrep:
        result = subprocess.run(
            [pgrep, "-f", "synfigstudio"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    ps = shutil.which("ps")
    if ps:
        result = subprocess.run(
            [ps, "-A", "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return any("synfigstudio" in line.lower() for line in result.stdout.splitlines())
    return False
