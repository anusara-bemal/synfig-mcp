# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Synfig time parsing and formatting.

Synfig prints times like ``0f``, ``2s 18f`` and ``1m 10s 12f``. Internally
everything is converted to float seconds; unknown markers (e.g. ``SOT``)
round-trip verbatim.
"""

from __future__ import annotations

import re

from ..errors import ParameterError

_TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([hmsmf])")


def parse_time(value: object, *, fps: float = 24.0) -> float:
    """Parse a synfig time value to float seconds."""
    if value is None:
        raise ParameterError("Missing time value.")
    if isinstance(value, (int, float)):
        if float(value) < 0:
            raise ParameterError("Time cannot be negative.")
        return float(value)
    text = str(value).strip()
    if not text:
        raise ParameterError("Empty time value.")
    if text.upper() == "SOT":
        # Marker kept verbatim elsewhere; cannot convert to seconds.
        raise ParameterError(
            "SOT is a marker, not an absolute time. Use an explicit time like '0f'."
        )
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        seconds = float(text)
        if seconds < 0:
            raise ParameterError("Time cannot be negative.")
        return seconds
    total = 0.0
    for amount, unit in _TOKEN_RE.findall(text):
        amount_f = float(amount)
        if unit == "h":
            total += amount_f * 3600.0
        elif unit == "m":
            total += amount_f * 60.0
        elif unit == "s":
            total += amount_f
        elif unit == "f":
            if fps <= 0:
                raise ParameterError("Frames need a positive fps.")
            total += amount_f / fps
    if total == 0.0 and not _TOKEN_RE.search(text):
        raise ParameterError(
            f"Unparseable time value: {value!r}. Examples: '0f', '2s 12f', '1m 30s', 1.5"
        )
    if total < 0:
        raise ParameterError("Time cannot be negative.")
    return total


def format_time(seconds: float, *, fps: float = 24.0) -> str:
    """Format float seconds the way synfig writes it in files."""
    if seconds < 0:
        raise ParameterError("Time cannot be negative.")
    remaining = float(seconds)
    hours, remaining = divmod(remaining, 3600.0)
    minutes, remaining = divmod(remaining, 60.0)
    whole_seconds = int(remaining)
    frac = remaining - whole_seconds
    frames = round(frac * fps)
    if frames >= fps:  # rounding overflow (e.g. 0.999s at 24fps)
        whole_seconds += 1
        frames = 0
    parts: list[str] = []
    if int(hours):
        parts.append(f"{int(hours)}h")
    if int(minutes):
        parts.append(f"{int(minutes)}m")
    if whole_seconds:
        parts.append(f"{whole_seconds}s")
    if frames or not parts:
        parts.append(f"{frames}f")
    return " ".join(parts)


def frame_count(begin: float, end: float, fps: float) -> int:
    if fps <= 0:
        return 0
    return max(0, round((end - begin) * fps) + 1)
