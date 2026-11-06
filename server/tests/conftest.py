"""Pytest fixtures and configuration."""

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend


@pytest.fixture
def headless_backend() -> HeadlessBackend:
    return HeadlessBackend()


@pytest.fixture
def live_backend() -> LiveBackend:
    return LiveBackend(host="127.0.0.1", port=19998)
