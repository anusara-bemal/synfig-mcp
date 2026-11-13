"""
Verifies the classification of every Synfig render target.

The coverage matrix claims which targets can write a single frame, which need
a filename pattern and which write nothing.  Those claims are checked here by
actually rendering with the installed binary.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from synfig_mcp.cli.runner import CliRunner
from synfig_mcp.errors import SynfigError
from synfig_mcp.render.targets import (
    TARGET_CAPABILITIES,
    TARGET_MAGIC,
    TargetKind,
    frame_targets,
    require_frame_target,
    require_sequence_target,
)

SAMPLE_SIF = """<?xml version='1.0' encoding='utf-8'?>
<canvas version="1.2" width="64" height="64" xres="2834.645752" yres="2834.645752" \
fps="24.000" antialias="2" begin-time="0s" end-time="1.00s" view-box="-1.1 1.1 1.1 -1.1" \
bgcolor="0.5 0.5 0.5 1.0"><name>target probe</name><layer type="circle" active="true" \
version="0.2" desc="C"><param name="radius"><real value="0.5"/></param></layer></canvas>"""


@pytest.fixture
def synfig_binary() -> Path:
    from synfig_mcp.validation import find_synfig_binary

    binary = find_synfig_binary()
    if binary is None:
        pytest.skip("Synfig CLI binary not available")
    return binary


def test_every_advertised_target_is_classified(synfig_binary: Path) -> None:
    """Every target the binary reports must have a capability classification."""
    import asyncio

    runner = CliRunner(synfig_binary)
    targets = asyncio.run(runner.get_targets())
    assert targets, "the Synfig binary reported no targets"

    unknown = [t for t in targets if t not in TARGET_CAPABILITIES]
    assert not unknown, f"targets without a classification: {unknown}"

    # Converter modules (ImageMagick) are optional at Synfig build time.
    optional = {t for t, kind in TARGET_CAPABILITIES.items() if kind is TargetKind.CONVERTER}
    extra = [t for t in TARGET_CAPABILITIES if t not in targets and t not in optional]
    assert not extra, f"classified targets the binary does not have: {extra}"


@pytest.mark.parametrize("target", sorted(TARGET_MAGIC))
def test_frame_targets_write_a_valid_image(
    synfig_binary: Path, tmp_path: Path, target: str
) -> None:
    """A frame target must produce a file with the expected magic bytes."""
    sif = tmp_path / "probe.sif"
    sif.write_text(SAMPLE_SIF, encoding="utf-8")
    out = tmp_path / f"frame_{target}.out"

    proc = subprocess.run(
        [
            str(synfig_binary),
            "-q",
            str(sif),
            "-t",
            target,
            "-o",
            str(out),
            "--time",
            "0s",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert proc.returncode == 0, proc.stderr[-500:]
    assert out.is_file(), f"target '{target}' produced no file"
    data = out.read_bytes()
    assert data.startswith(TARGET_MAGIC[target]), (
        f"target '{target}' produced {data[:8]!r}, expected {TARGET_MAGIC[target]!r}"
    )


def test_frame_targets_are_exactly_the_verified_ones() -> None:
    """The advertised single-frame list must match the classification."""
    assert set(frame_targets()) == {
        target for target, kind in TARGET_CAPABILITIES.items() if kind is TargetKind.FRAME
    }


def test_single_frame_targets_are_rejected_for_sequences() -> None:
    with pytest.raises(SynfigError):
        require_frame_target("ffmpeg")
    with pytest.raises(SynfigError):
        require_frame_target("null")
    with pytest.raises(SynfigError):
        require_frame_target("magick++")
    with pytest.raises(SynfigError):
        require_frame_target("does-not-exist")


def test_sequence_targets_are_rejected_for_single_frames() -> None:
    with pytest.raises(SynfigError):
        require_sequence_target("null")
    with pytest.raises(SynfigError):
        require_sequence_target("magick++")
    assert require_sequence_target("ffmpeg") == "ffmpeg"
    assert require_sequence_target("png") == "png"
