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


_real_studio_count = 0


def pytest_collection_modifyitems(
    session: pytest.Session,  # noqa: ARG001
    config: pytest.Config,  # noqa: ARG001
    items: list[pytest.Item],
) -> None:
    global _real_studio_count
    _real_studio_count = sum(
        1 for item in items if item.get_closest_marker("real_studio") is not None
    )


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter,
    exitstatus: int,  # noqa: ARG001
    config: pytest.Config,  # noqa: ARG001
) -> None:
    skipped_count = len(terminalreporter.stats.get("skipped", []))
    terminalreporter.write_sep("=", "Synfig MCP Test Summary")
    terminalreporter.write_line(f"Total skipped tests: {skipped_count}")
    terminalreporter.write_line(f"Total real_studio marked tests: {_real_studio_count}")
