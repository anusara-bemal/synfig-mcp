# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Configurable resource limits, enforced throughout the server."""

from __future__ import annotations

from ..config import Settings
from ..errors import LimitExceededError


class Limits:
    """Thin wrapper so the rest of the code reads caps from one place."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_resolution(self, width: int, height: int) -> None:
        cap = self.settings.max_resolution
        if width < 1 or height < 1:
            raise LimitExceededError(f"Resolution must be positive, got {width}x{height}.")
        if width > cap or height > cap:
            raise LimitExceededError(
                f"Resolution {width}x{height} exceeds SYNFIG_MCP_MAX_RESOLUTION ({cap}px).",
                hint="Lower the requested size or raise the cap.",
            )

    def check_frames(self, frames: int) -> None:
        cap = self.settings.max_frames
        if frames < 0:
            raise LimitExceededError("Negative frame counts are not allowed.")
        if frames > cap:
            raise LimitExceededError(
                f"Frame count {frames} exceeds SYNFIG_MCP_MAX_FRAMES ({cap}).",
                hint="Render a shorter range or raise the cap.",
            )

    def check_layer_count(self, count: int) -> None:
        cap = self.settings.max_layers
        if count > cap:
            raise LimitExceededError(
                f"Layer count {count} exceeds SYNFIG_MCP_MAX_LAYERS ({cap}).",
                hint="Simplify the scene or raise the cap.",
            )

    def check_render_pixels(self, width: int, height: int, frames: int) -> None:
        # Guard against absurd total work: 8192*8192*1 frame already exceeds typical RAM/time budgets.
        cap_px = 64_000_000  # 64 MP per frame
        if width * height > cap_px:
            raise LimitExceededError(
                f"{width}x{height} per frame ({width * height} px) exceeds the 64-megapixel per-frame budget."
            )
        if frames > 0:
            self.check_frames(frames)
