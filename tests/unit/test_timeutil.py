# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for synfig time parsing/formatting."""

from __future__ import annotations

import pytest

from synfig_mcp.document.timeutil import format_time, frame_count, parse_time
from synfig_mcp.errors import ParameterError


class TestParseTime:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, 0.0),
            (1.5, 1.5),
            ("0f", 0.0),
            ("12f", 0.5),
            ("2s 12f", 2.5),
            ("1m", 60.0),
            ("1h", 3600.0),
            ("1h 30m 10s 6f", 5400.0 + 10.25),
            ("1.5", 1.5),
        ],
    )
    def test_valid(self, value: object, expected: float) -> None:
        assert parse_time(value, fps=24.0) == pytest.approx(expected)

    @pytest.mark.parametrize("value", [None, "", "   ", "abc", "SOT", "sot"])
    def test_invalid(self, value: object) -> None:
        with pytest.raises(ParameterError):
            parse_time(value)

    def test_negative(self) -> None:
        with pytest.raises(ParameterError):
            parse_time(-1)
        with pytest.raises(ParameterError):
            parse_time("-1.5")

    def test_frames_need_positive_fps(self) -> None:
        with pytest.raises(ParameterError):
            parse_time("12f", fps=0)


class TestFormatTime:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0.0, "0f"),
            (0.5, "12f"),
            (1.0, "1s"),
            (2.5, "2s 12f"),
            (60.0, "1m"),
            (3600.0, "1h"),
            (3661.5, "1h 1m 1s 12f"),
        ],
    )
    def test_format(self, seconds: float, expected: str) -> None:
        assert format_time(seconds, fps=24.0) == expected

    def test_rounding_overflow(self) -> None:
        assert format_time(0.999, fps=24.0) == "1s"

    def test_negative_raises(self) -> None:
        with pytest.raises(ParameterError):
            format_time(-0.1)

    @pytest.mark.parametrize("seconds", [0.0, 1.5, 12.25, 3601.0])
    def test_roundtrip(self, seconds: float) -> None:
        assert parse_time(format_time(seconds, fps=24.0), fps=24.0) == pytest.approx(seconds)


class TestFrameCount:
    def test_basic(self) -> None:
        assert frame_count(0.0, 1.0, 24.0) == 25

    def test_invalid_fps(self) -> None:
        assert frame_count(0.0, 1.0, 0) == 0

    def test_reversed(self) -> None:
        assert frame_count(2.0, 1.0, 24.0) == 0
