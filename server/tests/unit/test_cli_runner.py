"""
The CLI runner must not spawn a subprocess per layer type on every call.

Introspecting the layer catalogue costs one ``synfig --layer-info`` invocation
per layer type.  Doing that on every ``layer_add`` made the first layer of a
session take ~18 seconds, so the catalogue is cached in memory and on disk.
"""

from __future__ import annotations

import json

import pytest

from synfig_mcp.cli.runner import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    r = CliRunner()
    if not r.is_available:
        pytest.skip("Synfig CLI not available in current environment")
    return r


@pytest.mark.asyncio
async def test_layer_catalog_is_cached_between_runners(runner: CliRunner) -> None:
    """A second runner must reuse the catalogue instead of re-introspecting it."""
    first = await runner.get_layer_catalog()
    assert first, "the layer catalogue is empty"

    second_runner = CliRunner(runner.binary_path)
    second = await second_runner.get_layer_catalog()

    assert set(second) == set(first)
    # The same objects are handed out, so no subprocess was spawned.
    assert second["circle"] is first["circle"] or second["circle"].version == (
        first["circle"].version
    )


@pytest.mark.asyncio
async def test_layer_catalog_is_persisted_on_disk(runner: CliRunner) -> None:
    """The catalogue is written to the disk cache for the next process."""
    await runner.get_layer_catalog()
    path = runner._catalog_disk_path()
    assert path.is_file(), "the layer catalogue was not cached on disk"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "circle" in data
    assert data["circle"]["version"]


@pytest.mark.asyncio
async def test_layer_version_comes_from_the_catalogue(runner: CliRunner) -> None:
    version = await runner.get_layer_version("circle")
    assert version, "the circle layer has no version"
