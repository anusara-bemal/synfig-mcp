# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for the async synfig subprocess runner."""

from __future__ import annotations

import asyncio
import sys

import pytest

from synfig_mcp.cli import runner
from synfig_mcp.errors import RenderCancelledError, RenderTimeoutError, SynfigNotFoundError


class TestEnv:
    def test_child_env_has_core_vars(self) -> None:
        env = runner._child_env()
        assert "PATH" in env
        if sys.platform == "win32":
            assert "SYSTEMROOT" in env
            assert "TEMP" in env
        else:
            assert "HOME" in env

    def test_redact(self) -> None:
        assert runner._redact_args(["a", "token=abc", "KEY=xyz"]) == ["a", "***", "***"]

    def test_progress_parser(self) -> None:
        values: list[float] = []
        runner._maybe_progress(b"rendering: 42.5%\n", values.append)
        assert values == [42.5]
        runner._maybe_progress(b"no progress\n", values.append)
        assert values == [42.5]

    def test_progress_callback_failure_is_swallowed(self) -> None:
        def boom(_: float) -> None:
            raise RuntimeError("nope")

        runner._maybe_progress(b"50%", boom)


class TestRun:
    async def test_success(self) -> None:
        result = await runner.run_synfig(
            sys.executable,
            ["-c", "import sys; print('25%'); sys.stderr.write('warn\\n')"],
            timeout=30,
        )
        assert result.returncode == 0
        assert "25%" in result.stdout_text
        assert "warn" in result.stderr_text
        assert result.duration_seconds >= 0

    async def test_progress_callback(self) -> None:
        seen: list[float] = []
        await runner.run_synfig(
            sys.executable,
            ["-c", "print('10%', flush=True); print('99%', flush=True)"],
            timeout=30,
            progress_cb=seen.append,
        )
        assert seen == [10.0, 99.0]

    async def test_missing_binary(self, tmp_path) -> None:
        with pytest.raises(SynfigNotFoundError):
            await runner.run_synfig(str(tmp_path / "nope"), [], timeout=5)

    async def test_timeout(self) -> None:
        with pytest.raises(RenderTimeoutError):
            await runner.run_synfig(
                sys.executable, ["-c", "import time; time.sleep(30)"], timeout=0.3
            )

    async def test_task_cancel(self) -> None:
        task = asyncio.create_task(
            runner.run_synfig(sys.executable, ["-c", "import time; time.sleep(30)"], timeout=60)
        )
        await asyncio.sleep(0.5)
        task.cancel()
        with pytest.raises(RenderCancelledError):
            await task

    async def test_registry_cancel(self) -> None:
        registry = runner.get_process_registry()
        task = asyncio.create_task(
            runner.run_synfig(
                sys.executable,
                ["-c", "import time; time.sleep(30)"],
                render_id="test-cancel",
                timeout=60,
            )
        )
        active = None
        for _ in range(50):
            active = await registry.get("test-cancel")
            if active is not None:
                break
            await asyncio.sleep(0.05)
        assert active is not None
        assert await registry.cancel("test-cancel") is True
        result = await task
        assert result.returncode != 0
        assert await registry.get("test-cancel") is None
        assert await registry.cancel("test-cancel") is False

    async def test_registry_listing(self) -> None:
        registry = runner.get_process_registry()
        task = asyncio.create_task(
            runner.run_synfig(
                sys.executable,
                ["-c", "import time; time.sleep(5)"],
                render_id="test-list",
                timeout=30,
            )
        )
        await asyncio.sleep(0.4)
        assert any(item.render_id == "test-list" for item in await registry.list())
        await registry.cancel("test-list")
        await task
