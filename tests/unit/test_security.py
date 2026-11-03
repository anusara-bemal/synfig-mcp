# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for workspace confinement and input sanitisation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from synfig_mcp.errors import LimitExceededError, WorkspaceError
from synfig_mcp.security.paths import (
    IMAGE_EXTENSIONS,
    PROJECT_EXTENSIONS,
    check_file_size,
    ensure_output_path,
    resolve_workspace_path,
    sanitize_text,
)


class TestResolve:
    def test_relative_inside(self, tmp_path: Path) -> None:
        assert resolve_workspace_path("a.sif", tmp_path) == (tmp_path / "a.sif").resolve()

    def test_absolute_inside(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "a.sif"
        assert resolve_workspace_path(str(target), tmp_path) == target.resolve()

    def test_dotdot_escape(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError, match="outside"):
            resolve_workspace_path("../evil.sif", tmp_path)

    def test_absolute_outside(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError, match="outside"):
            resolve_workspace_path(tmp_path.parent / "evil.sif", tmp_path)

    def test_missing_value(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError, match="Missing"):
            resolve_workspace_path(None, tmp_path)  # type: ignore[arg-type]

    def test_extension(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError, match="extension"):
            resolve_workspace_path("a.txt", tmp_path, allowed_extensions=PROJECT_EXTENSIONS)

    def test_must_exist(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError, match="not found"):
            resolve_workspace_path("a.sif", tmp_path, must_exist=True)
        target = tmp_path / "a.sif"
        target.write_text("x")
        assert resolve_workspace_path("a.sif", tmp_path, must_exist=True) == target.resolve()

    def test_expanduser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        assert resolve_workspace_path("~/a.sif", tmp_path).name == "a.sif"

    def test_symlink_escape(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        outside = tmp_path / "outside.sif"
        outside.write_text("x")
        link = workspace / "link.sif"
        try:
            os.symlink(outside, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks are not available")
        with pytest.raises(WorkspaceError):
            resolve_workspace_path("link.sif", workspace)

    def test_symlink_inside(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        target = workspace / "real.sif"
        target.write_text("x")
        link = workspace / "link.sif"
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks are not available")
        assert resolve_workspace_path("link.sif", workspace).name in {"link.sif", "real.sif"}


class TestOutput:
    def test_default(self, tmp_path: Path) -> None:
        assert (
            ensure_output_path(None, tmp_path, default_name="out.png")
            == (tmp_path / "out.png").resolve()
        )

    def test_explicit_relative(self, tmp_path: Path) -> None:
        assert ensure_output_path("renders/a.png", tmp_path, default_name="x.png").name == "a.png"

    def test_extension_checked(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError):
            ensure_output_path(
                "out.exe", tmp_path, default_name="x.png", allowed_extensions=IMAGE_EXTENSIONS
            )


class TestSize:
    def test_ok(self, tmp_path: Path) -> None:
        path = tmp_path / "a.sif"
        path.write_bytes(b"12345")
        check_file_size(path, 10)

    def test_too_large(self, tmp_path: Path) -> None:
        path = tmp_path / "a.sif"
        path.write_bytes(b"1234567890")
        with pytest.raises(LimitExceededError):
            check_file_size(path, 5)

    def test_missing(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError, match="Cannot stat"):
            check_file_size(tmp_path / "missing", 10)


class TestSanitize:
    def test_removes_control_characters(self) -> None:
        assert sanitize_text("a\x00b\x01c\tdef\rghi\n") == "abc\tdef\rghi\n"

    def test_truncates(self) -> None:
        assert sanitize_text("abcdef", max_length=3) == "abc"

    def test_none(self) -> None:
        assert sanitize_text(None) == ""  # type: ignore[arg-type]
