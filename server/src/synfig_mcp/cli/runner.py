"""
Subprocess runner for synfig CLI and ffmpeg.
"""

import asyncio
import shutil
from pathlib import Path


class CliRunner:
    """Invokes synfig CLI and ffmpeg."""

    def __init__(self, binary_path: Path | None = None) -> None:
        which_synfig = shutil.which("synfig")
        self.binary_path = binary_path or (Path(which_synfig) if which_synfig else None)

    async def get_version(self) -> str | None:
        """Get version string from synfig CLI."""
        if not self.binary_path:
            return None

        proc = await asyncio.create_subprocess_exec(
            str(self.binary_path),
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode("utf-8").strip()
        return None
