# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Registry of open project sessions, keyed by project_id."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lxml import etree

from ..config import Settings
from ..errors import DocumentNotFoundError
from ..security.limits import Limits
from ..security.paths import check_file_size
from . import io
from .model import ProjectSession


class ProjectRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.limits = Limits(settings)
        self._sessions: dict[str, ProjectSession] = {}
        self._by_path: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, tree: etree._ElementTree, *, path: Path | None, name: str | None = None
    ) -> ProjectSession:
        async with self._lock:
            session = ProjectSession(tree, settings=self.settings, path=path, name=name)
            self._sessions[session.project_id] = session
            if path:
                self._by_path[str(path.resolve())] = session.project_id
            return session

    async def open(self, path: Path) -> tuple[ProjectSession, bool]:
        resolved = path.resolve()
        async with self._lock:
            existing_id = self._by_path.get(str(resolved))
            if existing_id and existing_id in self._sessions:
                return self._sessions[existing_id], False
        check_file_size(resolved, self.settings.max_file_bytes, "project")
        tree = io.read_project(resolved, self.limits)
        async with self._lock:
            # Another coroutine may have opened it meanwhile.
            existing_id = self._by_path.get(str(resolved))
            if existing_id and existing_id in self._sessions:
                return self._sessions[existing_id], False
            session = ProjectSession(
                tree, settings=self.settings, path=resolved, name=resolved.stem
            )
            self._sessions[session.project_id] = session
            self._by_path[str(resolved)] = session.project_id
            return session, True

    async def get(self, project_id: str) -> ProjectSession:
        async with self._lock:
            session = self._sessions.get(project_id)
        if session is None:
            async with self._lock:
                known = sorted(self._sessions)
            raise DocumentNotFoundError(project_id, known=known)
        return session

    async def close(self, project_id: str) -> ProjectSession:
        async with self._lock:
            session = self._sessions.pop(project_id, None)
            if session is None:
                raise DocumentNotFoundError(project_id, known=sorted(self._sessions))
            if session.path:
                self._by_path.pop(str(session.path.resolve()), None)
            return session

    async def list(self) -> list[dict[str, Any]]:
        async with self._lock:
            sessions = list(self._sessions.values())
        return [session.info() for session in sessions]


def guess_project_path(workspace: Path, name: str, extension: str = ".sif") -> Path:
    safe_name = (
        "".join(ch for ch in name.strip() if ch not in '<>:"/\\|?*\x00').strip() or "project"
    )
    if not safe_name.lower().endswith((".sif", ".sifz", ".sfg")):
        safe_name += extension
    return workspace / safe_name
