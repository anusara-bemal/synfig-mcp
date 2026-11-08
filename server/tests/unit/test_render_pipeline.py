"""
Unit tests for RenderPipeline:
- Progress notifications
- Cancellation (assert partial files cleaned up or reported)
- Disk cache (identical call is cache hit; doc change or param change invalidates)
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.errors import SynfigError
from synfig_mcp.render.cache import RenderCache
from synfig_mcp.render.pipeline import CancellationToken, RenderPipeline


@pytest.fixture
def tmp_cache(tmp_path: Path) -> RenderCache:
    return RenderCache(cache_dir=tmp_path / "cache")


def get_mockable_backend() -> HeadlessBackend:
    backend = HeadlessBackend()
    if not backend.runner.is_available:

        async def fake_render(_doc_id: str, output_path: str, **_kwargs: Any) -> bool:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes")
            return True

        backend.render_frame = fake_render  # type: ignore[assignment,method-assign]
    return backend


@pytest.mark.asyncio
async def test_render_progress_notifications(tmp_path: Path, tmp_cache: RenderCache) -> None:
    """Assert progress callback is called with accurate frame counts and percentage."""
    backend = get_mockable_backend()
    doc = await backend.doc_new(width=160, height=120, fps=10.0)
    await backend.doc_set_time_range(doc.id, start_time=0.0, end_time=0.4, fps=10.0)

    pipeline = RenderPipeline(backend=backend, cache=tmp_cache)

    progress_events: list[tuple[int, int, float]] = []

    def on_progress(current: int, total: int, pct: float) -> None:
        progress_events.append((current, total, pct))

    out_dir = tmp_path / "seq_progress"
    frames = await pipeline.render_sequence(
        doc_id=doc.id,
        output_dir=out_dir,
        start_time=0.0,
        end_time=0.4,
        fps=10.0,
        progress_cb=on_progress,
    )
    # 0.0 to 0.4 at 10fps = 5 frames (0, 1, 2, 3, 4)
    assert len(frames) == 5
    assert len(progress_events) == 5
    assert progress_events[-1] == (5, 5, 100.0)
    assert progress_events[0] == (1, 5, 20.0)


@pytest.mark.asyncio
async def test_render_cancellation_and_cleanup(tmp_path: Path, tmp_cache: RenderCache) -> None:
    """Assert cancelling mid-render raises SynfigError and cleans up partial files when requested."""
    backend = get_mockable_backend()
    doc = await backend.doc_new(width=160, height=120, fps=10.0)
    await backend.doc_set_time_range(doc.id, start_time=0.0, end_time=1.0, fps=10.0)

    pipeline = RenderPipeline(backend=backend, cache=tmp_cache)
    token = CancellationToken()

    # Cancel after 2nd frame in progress callback
    def on_progress(current: int, _total: int, _pct: float) -> None:
        if current >= 2:
            token.cancel()

    out_dir = tmp_path / "seq_cancel_cleanup"
    with pytest.raises(SynfigError, match="cancelled by user"):
        await pipeline.render_sequence(
            doc_id=doc.id,
            output_dir=out_dir,
            start_time=0.0,
            end_time=1.0,
            fps=10.0,
            progress_cb=on_progress,
            cancel_token=token,
            cleanup_on_cancel=True,
        )

    # All partial frame files should be removed from disk
    remaining = list(out_dir.glob("*.png"))
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_render_cancellation_partial_reported(tmp_path: Path, tmp_cache: RenderCache) -> None:
    """Assert cancellation with cleanup_on_cancel=False leaves partial rendered frames intact."""
    backend = get_mockable_backend()
    doc = await backend.doc_new(width=160, height=120, fps=10.0)
    await backend.doc_set_time_range(doc.id, start_time=0.0, end_time=1.0, fps=10.0)

    pipeline = RenderPipeline(backend=backend, cache=tmp_cache)
    token = CancellationToken()

    def on_progress(current: int, _total: int, _pct: float) -> None:
        if current >= 2:
            token.cancel()

    out_dir = tmp_path / "seq_cancel_keep"
    with pytest.raises(SynfigError, match="cancelled by user"):
        await pipeline.render_sequence(
            doc_id=doc.id,
            output_dir=out_dir,
            start_time=0.0,
            end_time=1.0,
            fps=10.0,
            progress_cb=on_progress,
            cancel_token=token,
            cleanup_on_cancel=False,
        )

    # Partial files (at least 2) remain on disk
    remaining = list(out_dir.glob("*.png"))
    assert len(remaining) >= 2


@pytest.mark.asyncio
async def test_render_disk_cache_hits_and_invalidation(
    tmp_path: Path, tmp_cache: RenderCache
) -> None:
    """
    Assert:
    1. First render is a cache miss and populates cache.
    2. Second identical render is a cache hit.
    3. Modifying the document invalidates the cache key.
    4. Changing render parameters (e.g. width/height/time) produces a cache miss.
    """
    backend = get_mockable_backend()
    doc = await backend.doc_new(width=160, height=120, fps=10.0)
    pipeline = RenderPipeline(backend=backend, cache=tmp_cache)

    f1 = tmp_path / "frame1.png"
    # First render: cache miss
    assert tmp_cache.clear() == 0
    ok1 = await pipeline.render_cached_frame(doc.id, f1, time=0.0, width=160, height=120)
    assert ok1 is True
    assert f1.exists()

    # Cache now contains 1 entry
    cached_entries = list(tmp_cache.cache_dir.glob("*.png"))
    assert len(cached_entries) == 1
    assert cached_entries[0].stem

    # Second render with identical doc & params: cache hit
    f2 = tmp_path / "frame2.png"
    # Spy on backend.render_frame to ensure it is NOT called on cache hit
    backend.render_frame = AsyncMock(side_effect=backend.render_frame)  # type: ignore[method-assign]
    ok2 = await pipeline.render_cached_frame(doc.id, f2, time=0.0, width=160, height=120)
    assert ok2 is True
    assert f2.exists()
    assert backend.render_frame.call_count == 0  # CACHE HIT!

    # 3. Change render params (e.g. time=0.5s): cache miss
    f3 = tmp_path / "frame3.png"
    ok3 = await pipeline.render_cached_frame(doc.id, f3, time=0.5, width=160, height=120)
    assert ok3 is True
    assert backend.render_frame.call_count == 1  # Called again!
    assert len(list(tmp_cache.cache_dir.glob("*.png"))) == 2

    # 4. Modify document (add a circle layer): doc_state changes -> cache miss
    await backend.layer_add(doc.id, "circle")
    f4 = tmp_path / "frame4.png"
    ok4 = await pipeline.render_cached_frame(doc.id, f4, time=0.0, width=160, height=120)
    assert ok4 is True
    assert backend.render_frame.call_count == 2  # Cache miss due to doc modification!
    assert len(list(tmp_cache.cache_dir.glob("*.png"))) == 3
