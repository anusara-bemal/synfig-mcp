"""Unit tests for the visual review service orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.errors import RenderError
from synfig_mcp.review.service import ReviewService


@pytest.mark.asyncio
async def test_review_frame_raises_when_render_produces_no_output() -> None:
    """A failed render must surface a typed error instead of a FileNotFoundError."""
    backend = AsyncMock(spec=BackendBase)
    backend.render_frame = AsyncMock(return_value=False)
    service = ReviewService(backend=backend)

    with pytest.raises(RenderError, match="produced no output"):
        await service.review_frame(doc_id="doc_0", time=0.0)
