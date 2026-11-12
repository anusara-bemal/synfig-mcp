"""
Capabilities of the Synfig render targets.

The Synfig binary advertises 13 output modules, but they are not
interchangeable: some write a single image, some are sequence encoders that
need a filename pattern, one is an image converter that needs an optional
module, and two deliberately write nothing.

The classification below was established by rendering a frame with every
target of the installed binary and inspecting the result (see
``server/tests/contract/test_render_targets.py``).
"""

from __future__ import annotations

from enum import StrEnum

from synfig_mcp.errors import SynfigError


class TargetKind(StrEnum):
    """How a Synfig output module behaves."""

    #: Writes exactly one image file for a single frame.
    FRAME = "frame"
    #: Encodes a sequence; the output path must contain a ``%04d`` pattern.
    SEQUENCE = "sequence"
    #: Converts the rendered frame into another image format.
    CONVERTER = "converter"
    #: Renders without writing any file (benchmarking / debugging).
    NONE = "none"


#: Capability of every target module of Synfig 1.5.
TARGET_CAPABILITIES: dict[str, TargetKind] = {
    "png": TargetKind.FRAME,
    "jpeg": TargetKind.FRAME,
    "bmp": TargetKind.FRAME,
    "gif": TargetKind.FRAME,
    "ppm": TargetKind.FRAME,
    "yuv420p": TargetKind.FRAME,
    "png-spritesheet": TargetKind.SEQUENCE,
    "ffmpeg": TargetKind.SEQUENCE,
    "libav": TargetKind.SEQUENCE,
    "dv": TargetKind.SEQUENCE,
    "magick++": TargetKind.CONVERTER,
    "imagemagick": TargetKind.CONVERTER,
    "null": TargetKind.NONE,
    "null-tile": TargetKind.NONE,
}

#: Magic bytes of the formats the frame targets produce.
TARGET_MAGIC: dict[str, bytes] = {
    "png": b"\x89PNG",
    "jpeg": b"\xff\xd8\xff",
    "bmp": b"BM",
    "gif": b"GIF",
    "ppm": b"P6",
}


def target_kind(target: str) -> TargetKind | None:
    """Return the capability of a target, or ``None`` for an unknown target."""
    return TARGET_CAPABILITIES.get(target.strip().lower())


def frame_targets() -> list[str]:
    """Targets that write a single image for a single frame."""
    return sorted(t for t, kind in TARGET_CAPABILITIES.items() if kind is TargetKind.FRAME)


def require_frame_target(target: str) -> str:
    """
    Validate that a target can be used for a single frame render.

    Raises:
        SynfigError: when the target cannot produce a single frame file.
    """
    normalized = target.strip().lower()
    kind = target_kind(normalized)
    if kind is None:
        raise SynfigError(
            f"Unknown Synfig render target '{target}'. Available targets: "
            f"{', '.join(sorted(TARGET_CAPABILITIES))}."
        )
    if kind is TargetKind.FRAME:
        return normalized
    if kind is TargetKind.SEQUENCE:
        raise SynfigError(
            f"The '{normalized}' target encodes a sequence and needs a filename pattern "
            f"(for example 'frame_%04d.png'). Use render_sequence for it, or one of the "
            f"single-frame targets: {', '.join(frame_targets())}."
        )
    if kind is TargetKind.CONVERTER:
        raise SynfigError(
            f"The '{normalized}' target converts a rendered frame into another image "
            "format and needs the optional ImageMagick module. Render with one of the "
            f"single-frame targets: {', '.join(frame_targets())}."
        )
    raise SynfigError(
        f"The '{normalized}' target renders without writing any file. Use one of the "
        f"single-frame targets: {', '.join(frame_targets())}."
    )


def require_sequence_target(target: str) -> str:
    """
    Validate that a target can be used for a sequence render.

    Raises:
        SynfigError: when the target cannot encode a sequence.
    """
    normalized = target.strip().lower()
    kind = target_kind(normalized)
    if kind is None:
        raise SynfigError(
            f"Unknown Synfig render target '{target}'. Available targets: "
            f"{', '.join(sorted(TARGET_CAPABILITIES))}."
        )
    if kind in (TargetKind.SEQUENCE, TargetKind.FRAME):
        return normalized
    if kind is TargetKind.CONVERTER:
        raise SynfigError(
            f"The '{normalized}' target converts a single frame and cannot encode a sequence."
        )
    raise SynfigError(
        f"The '{normalized}' target renders without writing any file and cannot encode a sequence."
    )
