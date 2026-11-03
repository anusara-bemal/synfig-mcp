# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for the in-memory project registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from synfig_mcp.config import Settings
from synfig_mcp.document import io
from synfig_mcp.document.registry import ProjectRegistry, guess_project_path
from synfig_mcp.errors import DocumentNotFoundError, WorkspaceError

XML = b'<canvas version="1.0" width="10" height="10"><name>x</name></canvas>'


@pytest.fixture
def registry(tmp_path: Path) -> ProjectRegistry:
    return ProjectRegistry(Settings(workspace=tmp_path))


class TestCreate:
    async def test_create(self, registry: ProjectRegistry, tmp_path: Path) -> None:
        session = await registry.create(io.parse_sif(XML), path=tmp_path / "a.sif")
        assert session.project_id
        assert await registry.get(session.project_id) is session
        assert [item["project_id"] for item in await registry.list()] == [session.project_id]

    async def test_close(self, registry: ProjectRegistry, tmp_path: Path) -> None:
        session = await registry.create(io.parse_sif(XML), path=tmp_path / "a.sif")
        closed = await registry.close(session.project_id)
        assert closed is session
        with pytest.raises(DocumentNotFoundError):
            await registry.get(session.project_id)

    async def test_close_missing(self, registry: ProjectRegistry) -> None:
        with pytest.raises(DocumentNotFoundError):
            await registry.close("nope")

    async def test_get_missing_lists_known(self, registry: ProjectRegistry, tmp_path: Path) -> None:
        session = await registry.create(io.parse_sif(XML), path=tmp_path / "a.sif")
        with pytest.raises(DocumentNotFoundError) as excinfo:
            await registry.get("missing")
        assert session.project_id in (excinfo.value.hint or "")


class TestOpen:
    async def test_open(self, registry: ProjectRegistry, tmp_path: Path) -> None:
        path = tmp_path / "a.sif"
        io.write_project(io.parse_sif(XML), path, backup=False)
        session, created = await registry.open(path)
        assert created is True
        assert session.path == path.resolve()
        same, created2 = await registry.open(path)
        assert same is session
        assert created2 is False

    async def test_open_sifz(self, registry: ProjectRegistry, tmp_path: Path) -> None:
        path = tmp_path / "a.sifz"
        io.write_project(io.parse_sif(XML), path, backup=False)
        session, created = await registry.open(path)
        assert created is True
        assert session.name == "a"

    async def test_open_missing(self, registry: ProjectRegistry, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError):
            await registry.open(tmp_path / "missing.sif")


class TestGuessPath:
    def test_adds_extension(self, tmp_path: Path) -> None:
        assert guess_project_path(tmp_path, "demo").name == "demo.sif"
        assert guess_project_path(tmp_path, "demo.sifz").name == "demo.sifz"
        assert guess_project_path(tmp_path, "demo", ".sifz").name == "demo.sifz"

    def test_sanitizes(self, tmp_path: Path) -> None:
        assert guess_project_path(tmp_path, 'a<b>c:"d/e\\f|g?h').name == "abcdefgh.sif"

    def test_empty(self, tmp_path: Path) -> None:
        assert guess_project_path(tmp_path, "   ").name == "project.sif"
