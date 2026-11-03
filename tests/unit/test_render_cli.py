# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for render argument construction and the render manager."""

from __future__ import annotations

import pytest

from synfig_mcp.cli import render
from synfig_mcp.cli.runner import RunResult
from synfig_mcp.config import Settings
from synfig_mcp.errors import (
    RenderCancelledError,
    RenderError,
    RenderTimeoutError,
    UnsupportedTargetError,
)


class TestVerifyTarget:
    def test_direct(self) -> None:
        assert render.verify_target("gif", ["gif", "png"]) == "gif"

    @pytest.mark.parametrize(
        ("requested", "resolved"),
        [("mp4", "ffmpeg"), ("webm", "ffmpeg"), ("jpg", "jpeg"), ("apng", "png")],
    )
    def test_aliases(self, requested: str, resolved: str) -> None:
        assert render.verify_target(requested, ["ffmpeg", "jpeg", "png", "gif"]) == resolved

    def test_unsupported(self) -> None:
        with pytest.raises(UnsupportedTargetError) as excinfo:
            render.verify_target("lottie", ["gif"])
        assert "gif" in (excinfo.value.hint or "")


class TestArgs:
    def test_frame(self) -> None:
        args = render.build_render_args(
            target="png",
            output="out.png",
            width=100,
            height=50,
            time_s=1.5,
            fps=24,
            antialias=2,
            input_file="in.sif",
        )
        assert args[:4] == ["-t", "png", "-w", "100"]
        assert "-h" in args and "50" in args
        assert "-a" in args and "2" in args
        assert "--time" in args and "1s 12f" in args
        output_index = args.index("-o")
        assert args[output_index + 1] == "out.png"
        assert args[-1] == "in.sif"

    def test_animation(self) -> None:
        args = render.build_render_args(
            target="gif",
            output="out.gif",
            width=None,
            height=None,
            begin_s=0.0,
            end_s=2.0,
            fps=24,
            quality="high",
            sequence_separator="_",
            extra=["--video-codec=libx264"],
            input_file="in.sif",
        )
        assert quality_marker(args)
        assert "--begin-time" in args and "0f" in args
        assert "--end-time" in args and "2s" in args
        assert "--sequence-separator" in args
        assert "--video-codec=libx264" in args
        assert args[args.index("-o") + 1] == "out.gif"
        assert args[-1] == "in.sif"

    def test_quality_alias(self) -> None:
        args = render.build_render_args(
            target="png",
            output="x.png",
            width=None,
            height=None,
            quality="best",
        )
        assert "4" in args

    def test_unknown_quality_no_aa(self) -> None:
        args = render.build_render_args(
            target="png",
            output="x.png",
            width=None,
            height=None,
            quality="ultra",
        )
        assert "-a" not in args

    def test_no_input(self) -> None:
        args = render.build_render_args(
            target="png",
            output="x.png",
            width=0,
            height=0,
        )
        assert args == ["-t", "png", "-o", "x.png"]


def quality_marker(args: list[str]) -> bool:
    return "-a" in args and "4" in args


class TestJob:
    def test_to_dict(self) -> None:
        job = render.RenderJob(render_id="r1", kind="frame", target="png", output="x.png")
        payload = job.to_dict()
        assert payload["status"] == "queued"
        assert payload["duration_seconds"] >= 0
        job.status = "done"
        job.finished_at = job.started_at + 2
        assert job.to_dict()["duration_seconds"] == 2.0

    def test_tail_and_hint(self) -> None:
        assert render._tail("  hello  ") == "hello"
        assert "input file" in render._render_hint("No such file")
        assert "cannot load" in render._render_hint("unknown layer type")
        assert "validate_project" in render._render_hint("XML parse error")
        assert "memory" in render._render_hint("Out of memory")
        assert "synfig_doctor" in render._render_hint("weird")


def run_result(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> RunResult:
    return RunResult(returncode=returncode, stdout=stdout, stderr=stderr, duration_seconds=0.1)


class TestManager:
    async def test_success_and_listing(
        self, monkeypatch: pytest.MonkeyPatch, settings: Settings
    ) -> None:
        async def fake(*args, **kwargs):  # type: ignore[no-untyped-def]
            return run_result()

        monkeypatch.setattr(render, "run_synfig", fake)
        manager = render.RenderManager(settings)
        job = await manager.run_render(
            kind="frame",
            binary="synfig",
            args=[],
            target="png",
            output="x.png",
        )
        assert job.status == "done"
        assert job.progress == 100.0
        assert await manager.get(job.render_id) is job
        assert [item.render_id for item in await manager.list_jobs()] == [job.render_id]
        assert await manager.get("missing") is None

    async def test_failure(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        async def fake(*args, **kwargs):  # type: ignore[no-untyped-def]
            return run_result(returncode=2, stderr=b"unknown layer")

        monkeypatch.setattr(render, "run_synfig", fake)
        manager = render.RenderManager(settings)
        with pytest.raises(RenderError) as excinfo:
            await manager.run_render(
                kind="frame", binary="synfig", args=[], target="png", output="x.png"
            )
        assert "exited with code 2" in excinfo.value.message

    async def test_timeout(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        async def fake(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RenderTimeoutError("timed out")

        monkeypatch.setattr(render, "run_synfig", fake)
        manager = render.RenderManager(settings)
        with pytest.raises(RenderTimeoutError):
            await manager.run_render(
                kind="frame", binary="synfig", args=[], target="png", output="x.png"
            )

    async def test_cancelled(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        async def fake(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RenderCancelledError("cancelled")

        monkeypatch.setattr(render, "run_synfig", fake)
        manager = render.RenderManager(settings)
        with pytest.raises(RenderCancelledError):
            await manager.run_render(
                kind="frame", binary="synfig", args=[], target="png", output="x.png"
            )

    async def test_cancel_unknown(self, settings: Settings) -> None:
        manager = render.RenderManager(settings)
        assert await manager.cancel("nope") is False

    async def test_cancel_known(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        async def fake(*args, **kwargs):  # type: ignore[no-untyped-def]
            return run_result()

        monkeypatch.setattr(render, "run_synfig", fake)
        manager = render.RenderManager(settings)
        job = await manager.run_render(
            kind="frame", binary="synfig", args=[], target="png", output="x.png"
        )

        async def cancel_ok(render_id: str) -> bool:
            return render_id == job.render_id

        monkeypatch.setattr(render.get_process_registry(), "cancel", cancel_ok)
        assert await manager.cancel(job.render_id) is True

    async def test_job_bound(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        async def fake(*args, **kwargs):  # type: ignore[no-untyped-def]
            return run_result()

        monkeypatch.setattr(render, "run_synfig", fake)
        manager = render.RenderManager(settings)
        original_max = render.RenderManager.MAX_JOBS
        render.RenderManager.MAX_JOBS = 2
        try:
            for _ in range(4):
                await manager.run_render(
                    kind="frame", binary="synfig", args=[], target="png", output="x.png"
                )
            assert len(await manager.list_jobs()) == 2
        finally:
            render.RenderManager.MAX_JOBS = original_max
