# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tool-level tests for render tools using a fake render manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.conftest import ToolBox

from synfig_mcp.cli.render import RenderJob
from synfig_mcp.tools.common import AppContext

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def payload(raw: Any) -> dict:
    if isinstance(raw, list):
        return json.loads(raw[0].text)
    return json.loads(raw)


def error(raw: Exception) -> dict:
    return json.loads(str(raw))


@pytest.fixture
def ctx(context: AppContext) -> AppContext:
    context._probed = {
        "found": True,
        "version": "synfig 1.5.5",
        "targets": ["png", "gif", "ffmpeg", "bmp", "jpeg", "ppm"],
        "renderers": [],
        "layers": [],
        "problems": [],
    }

    async def fake_render(
        *,
        kind: str,
        binary: str,
        args: list[str],
        target: str,
        output: str,
        progress_cb=None,
        **_kwargs: Any,
    ) -> RenderJob:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(PNG if target == "png" else b"GIF89a" + b"0" * 16)
        if progress_cb is not None:
            progress_cb(100.0)
        job = RenderJob(
            render_id="render-test",
            kind=kind,
            target=target,
            output=str(path),
            status="done",
        )
        await context.render_manager._record(job)
        return job

    context.render_manager.run_render = fake_render  # type: ignore[method-assign]
    return context


class TestFrame:
    async def test_render_frame_png(self, tools: ToolBox, project: str, ctx: AppContext) -> None:
        result = await tools.render_frame(project_id=project, time="12f")
        data = payload(result)
        assert data["target"] == "png"
        assert data["status"] == "done"
        assert data["time"] == "12f"
        assert Path(data["output"]).is_file()
        assert data["size_bytes"] > 0
        assert len(result) == 2
        assert result[1].data

    async def test_render_frame_no_image(
        self, tools: ToolBox, project: str, ctx: AppContext
    ) -> None:
        raw = await tools.render_frame(project_id=project, output="frame.png", return_image=False)
        data = payload(raw)
        assert isinstance(raw, str)
        assert data["output"].endswith("frame.png")

    async def test_render_frame_quality_and_size(
        self, tools: ToolBox, project: str, ctx: AppContext
    ) -> None:
        result = payload(
            await tools.render_frame(
                project_id=project,
                width=100,
                height=50,
                quality="high",
                antialias=4,
                span=0.5,
                return_image=False,
            )
        )
        assert result["width"] == 100
        assert result["height"] == 50

    async def test_render_frame_dirty_snapshot(
        self, tools: ToolBox, project: str, ctx: AppContext
    ) -> None:
        await tools.add_circle(project_id=project, name="ball")
        result = payload(await tools.render_frame(project_id=project, return_image=False))
        assert Path(result["output"]).is_file()
        assert not list((ctx.settings.workspace / ".synfig-mcp" / "render-tmp").glob("*.sifz"))

    async def test_render_frame_bad_time(
        self, tools: ToolBox, project: str, ctx: AppContext
    ) -> None:
        with pytest.raises(RuntimeError):
            await tools.render_frame(project_id=project, time="bogus")

    async def test_preview_and_thumbnail(
        self, tools: ToolBox, project: str, ctx: AppContext
    ) -> None:
        preview = payload(await tools.render_preview(project_id=project))
        assert preview["width"] == 480
        thumb = payload(await tools.render_thumbnail(project_id=project, size=128))
        assert thumb["width"] == 128


class TestAnimation:
    async def test_render_gif(self, tools: ToolBox, project: str, ctx: AppContext) -> None:
        data = payload(await tools.render_animation(project_id=project, target="gif"))
        assert data["target"] == "gif"
        assert data["frames"] >= 1
        assert Path(data["output"]).is_file()

    async def test_render_with_options(self, tools: ToolBox, project: str, ctx: AppContext) -> None:
        data = payload(
            await tools.render_animation(
                project_id=project,
                target="ffmpeg",
                output="clip.mp4",
                width=64,
                height=64,
                fps=12,
                begin_time="0f",
                end_time="1s",
                video_codec="libx264",
                video_bitrate="1M",
                antialias=2,
            )
        )
        assert data["target"] == "ffmpeg"
        assert data["output"].endswith("clip.mp4")

    async def test_unsupported_target(self, tools: ToolBox, project: str, ctx: AppContext) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await tools.render_animation(project_id=project, target="lottie")
        assert error(excinfo.value)["error"] == "unsupported_target"
        with pytest.raises(RuntimeError):
            await tools.render_animation(project_id=project, target="bogus")

    async def test_bad_range(self, tools: ToolBox, project: str, ctx: AppContext) -> None:
        with pytest.raises(RuntimeError):
            await tools.render_animation(
                project_id=project, target="gif", begin_time="2s", end_time="1s"
            )

    async def test_missing_binary(
        self,
        tools: ToolBox,
        project: str,
        context: AppContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(context, "binary_path", lambda: None)
        context._probed = {"found": False, "targets": [], "problems": ["missing"]}
        with pytest.raises(RuntimeError) as excinfo:
            await tools.render_frame(project_id=project)
        assert error(excinfo.value)["error"] == "synfig_binary_not_found"


class TestJobs:
    async def test_status_and_cancel(self, tools: ToolBox, ctx: AppContext) -> None:
        job = RenderJob(
            render_id="render-x", kind="frame", target="png", output="x.png", status="running"
        )
        await ctx.render_manager._record(job)
        status = payload(await tools.get_render_status(render_id="render-x"))
        assert status["found"] is True
        assert status["job"]["status"] == "running"
        assert payload(await tools.get_render_status(render_id="missing"))["found"] is False
        jobs = payload(await tools.get_render_status())["jobs"]
        assert jobs[0]["render_id"] == "render-x"

        async def fake_cancel(render_id: str) -> bool:
            return render_id == "render-x"

        ctx.render_manager.cancel = fake_cancel  # type: ignore[method-assign]
        assert payload(await tools.cancel_render(render_id="render-x"))["cancelled"] is True
        assert payload(await tools.cancel_render(render_id="other"))["cancelled"] is False
