"""
Unit tests for CliRunner (synfig CLI introspection and rendering).
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from synfig_mcp.cli.runner import CliRunner
from synfig_mcp.sif.parser import SifDocument
from synfig_mcp.sif.writer import save_sif


@pytest.mark.asyncio
async def test_cli_runner_discovery_and_version() -> None:
    runner = CliRunner()
    if not runner.is_available:
        pytest.skip("synfig binary not available on this system")

    version = await runner.get_version()
    assert version is not None
    assert len(version) > 0


@pytest.mark.asyncio
async def test_cli_runner_introspection() -> None:
    runner = CliRunner()
    if not runner.is_available:
        pytest.skip("synfig binary not available on this system")

    # Test layers listing
    layers = await runner.get_layers()
    assert len(layers) > 10
    assert "circle" in layers
    assert "rectangle" in layers
    assert "star" in layers

    # Test layer-info parsing
    circle_info = await runner.get_layer_info("circle")
    assert circle_info is not None
    assert circle_info.name == "circle"
    assert "radius" in circle_info.params
    assert "color" in circle_info.params
    assert circle_info.params["radius"].localized_name == "Radius"

    # Test targets
    targets = await runner.get_targets()
    assert len(targets) > 0
    assert "png" in targets

    # Test renderers
    renderers = await runner.get_renderers()
    assert len(renderers) > 0
    assert "software" in renderers

    # Test valuenodes
    valuenodes = await runner.get_valuenodes()
    assert len(valuenodes) > 0
    assert "composite" in valuenodes or "add" in valuenodes


@pytest.mark.asyncio
async def test_cli_runner_render_frame() -> None:
    runner = CliRunner()
    if not runner.is_available:
        pytest.skip("synfig binary not available on this system")

    doc = SifDocument.new(width=100, height=100, fps=24.0)
    doc.add_layer("circle", desc="RenderCircle")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        sif_file = tmp_path / "scene.sif"
        out_png = tmp_path / "frame.png"

        save_sif(doc, sif_file)

        success = await runner.render_frame(
            sif_path=sif_file,
            output_path=out_png,
            time=0.0,
            width=100,
            height=100,
            target="png",
        )

        assert success is True
        assert out_png.is_file()
        assert out_png.stat().st_size > 0


@pytest.mark.asyncio
async def test_cli_runner_mocked_fallback() -> None:
    runner = CliRunner(binary_path=Path("/nonexistent/synfig_fake"))
    assert runner.is_available is False

    assert await runner.get_version() is None
    assert await runner.get_layers() == []
    assert await runner.get_layer_info("circle") is None
    assert await runner.get_targets() == []
    assert await runner.get_renderers() == []
    assert await runner.get_valuenodes() == []
    assert await runner.render_frame(Path("a.sif"), Path("b.png")) is False


@pytest.mark.asyncio
async def test_cli_runner_mocked_subprocess_parse() -> None:
    runner = CliRunner(binary_path=Path("mock_synfig"))
    runner.binary_path = Path("mock_synfig")

    fake_stdout = (
        b"synfig(123) info: loading\n"
        b"Layer Name: custom_box\n"
        b"Localized Layer Name: Custom Box\n"
        b"Version: 0.5\n"
        b"param - size\n"
        b"\tLocalized Name: Size\n"
        b"\tDescription: Box dimensions\n"
        b"\tHint: vector\n"
    )

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_stdout, b"")
    mock_proc.returncode = 3

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
    ):
        info = await runner.get_layer_info("custom_box")
        assert info is not None
        assert info.name == "custom_box"
        assert info.localized_name == "Custom Box"
        assert info.version == "0.5"
        assert "size" in info.params
        assert info.params["size"].description == "Box dimensions"
        assert info.params["size"].hint == "vector"
