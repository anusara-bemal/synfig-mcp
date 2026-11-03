# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Async, shell-free subprocess runner for synfig with timeout and cancellation."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from ..errors import RenderCancelledError, RenderTimeoutError
from ..logging import get_logger

logger = get_logger(__name__)


def _child_env() -> dict[str, str]:
    """Environment for the synfig subprocess.

    Starts from the current environment and backfills the OS essentials
    Synfig (a native binary) needs when the server was launched with a
    minimal environment (e.g. a bare MCP client config). Missing values
    crash synfig with 0xC0000005 on Windows, so we guarantee SYSTEMROOT,
    SystemDrive, WINDIR, TEMP/TMP, PATH, COMSPEC, USERPROFILE & co.
    """
    env = os.environ.copy()
    if os.name == "nt":
        system_drive = env.get("SystemDrive", "C:")
        defaults = {
            "SYSTEMROOT": f"{system_drive}\\Windows",
            "SystemRoot": f"{system_drive}\\Windows",
            "SystemDrive": system_drive,
            "WINDIR": f"{system_drive}\\Windows",
            "COMSPEC": f"{system_drive}\\Windows\\System32\\cmd.exe",
            "TEMP": f"{system_drive}\\Windows\\Temp",
            "TMP": f"{system_drive}\\Windows\\Temp",
            "USERPROFILE": f"{system_drive}\\Users\\Default",
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            "PATH": f"{system_drive}\\Windows\\System32;{system_drive}\\Windows;{system_drive}\\Windows\\System32\\Wbem",
            "APPDATA": f"{system_drive}\\Users\\Default\\AppData\\Roaming",
            "LOCALAPPDATA": f"{system_drive}\\Users\\Default\\AppData\\Local",
            "PROGRAMDATA": f"{system_drive}\\ProgramData",
            "PUBLIC": f"{system_drive}\\Users\\Public",
            "NUMBER_OF_PROCESSORS": str(os.cpu_count() or 4),
            "PROCESSOR_ARCHITECTURE": "AMD64",
        }
        for key, value in defaults.items():
            env.setdefault(key, value)
    else:
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        temp_dir = tempfile.gettempdir()
        env.setdefault("HOME", temp_dir)
        env.setdefault("TMPDIR", temp_dir)
    return env


@dataclass
class RunResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    duration_seconds: float

    @property
    def stdout_text(self) -> str:
        return self.stdout.decode("utf-8", errors="replace")

    @property
    def stderr_text(self) -> str:
        return self.stderr.decode("utf-8", errors="replace")


@dataclass
class ActiveProcess:
    render_id: str
    process: asyncio.subprocess.Process
    started_at: float = field(default_factory=time.time)
    description: str = ""


class ProcessRegistry:
    """Tracks in-flight synfig processes so they can be queried and cancelled."""

    def __init__(self) -> None:
        self._active: dict[str, ActiveProcess] = {}
        self._lock = asyncio.Lock()

    async def register(
        self, render_id: str, process: asyncio.subprocess.Process, description: str = ""
    ) -> None:
        async with self._lock:
            self._active[render_id] = ActiveProcess(render_id, process, time.time(), description)

    async def unregister(self, render_id: str) -> None:
        async with self._lock:
            self._active.pop(render_id, None)

    async def get(self, render_id: str) -> ActiveProcess | None:
        async with self._lock:
            return self._active.get(render_id)

    async def list(self) -> list[ActiveProcess]:
        async with self._lock:
            return list(self._active.values())

    async def cancel(self, render_id: str) -> bool:
        async with self._lock:
            active = self._active.get(render_id)
            if active is None:
                return False
            process = active.process
        _terminate(process)
        return True


def _terminate(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        if os.name == "posix":
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGTERM)  # type: ignore[attr-defined]
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    # Give it a moment, then force-kill.
    with contextlib.suppress(ProcessLookupError):
        process.kill()


_registry = ProcessRegistry()


def get_process_registry() -> ProcessRegistry:
    return _registry


async def run_synfig(
    binary: str,
    args: list[str],
    *,
    render_id: str | None = None,
    timeout: float = 300.0,
    description: str = "synfig",
    progress_cb: Callable[[float], None] | None = None,
) -> RunResult:
    """Run synfig asynchronously; never uses a shell."""
    env = _child_env()
    started = time.perf_counter()
    logger.info("spawning synfig render_id=%s args=%s", render_id, _redact_args(args))
    try:
        process = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=(os.name == "posix"),
        )
    except FileNotFoundError as exc:
        from ..errors import SynfigNotFoundError

        raise SynfigNotFoundError() from exc
    except PermissionError as exc:
        from ..errors import SynfigNotFoundError

        raise SynfigNotFoundError() from exc

    rid = render_id or f"render-{int(started * 1000)}"
    await _registry.register(rid, process, description)

    async def _read_stream(stream: asyncio.StreamReader, is_err: bool) -> bytes:
        chunks: list[bytes] = []
        assert stream is not None
        while True:
            line = await stream.readline()
            if not line:
                break
            chunks.append(line)
            if progress_cb is not None:
                _maybe_progress(line, progress_cb)
        return b"".join(chunks)

    try:
        stdout_task = asyncio.create_task(_read_stream(process.stdout, False))  # type: ignore[arg-type]
        stderr_task = asyncio.create_task(_read_stream(process.stderr, True))  # type: ignore[arg-type]
        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            _terminate(process)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(process.wait(), timeout=5.0)
            stdout_task.cancel()
            stderr_task.cancel()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise RenderTimeoutError(
                f"synfig timed out after {timeout:.0f}s.",
                hint="Raise SYNFIG_MCP_RENDER_TIMEOUT, lower the resolution, or render fewer frames.",
            ) from exc
        stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
    except asyncio.CancelledError as exc:
        _terminate(process)
        with contextlib.suppress(Exception):
            await asyncio.wait_for(process.wait(), timeout=5.0)
        raise RenderCancelledError("Render was cancelled.", context={"render_id": rid}) from exc
    finally:
        await _registry.unregister(rid)

    duration = time.perf_counter() - started
    return RunResult(
        returncode=process.returncode or 0,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
    )


def _maybe_progress(line: bytes, progress_cb: Callable[[float], None] | None) -> None:
    import re

    text = line.decode("utf-8", errors="replace")
    match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
    if match and progress_cb is not None:
        try:
            progress_cb(float(match.group(1)))
        except Exception:
            logger.debug("progress callback failed", exc_info=True)


def _redact_args(args: list[str]) -> list[str]:
    # Nothing secret is expected on the command line, but be defensive.
    return [a if not a.lower().startswith(("key=", "token=", "password=")) else "***" for a in args]
