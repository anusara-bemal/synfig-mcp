# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Shared context and helpers for MCP tools."""

from __future__ import annotations

import asyncio
import functools
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from mcp.server.fastmcp import FastMCP

from ..cli.binary import find_synfig_binary, probe_synfig
from ..cli.render import RenderManager
from ..config import Settings
from ..document.model import ProjectSession
from ..document.registry import ProjectRegistry
from ..document.validators import KNOWN_LAYER_TYPES
from ..errors import SynfigMCPError, SynfigNotFoundError
from ..logging import get_logger

logger = get_logger(__name__)
FuncT = TypeVar("FuncT", bound=Callable[..., Any])


@dataclass
class AppContext:
    settings: Settings
    registry: ProjectRegistry
    render_manager: RenderManager

    def __post_init__(self) -> None:
        self._probed: dict[str, Any] | None = None
        self._probe_lock = asyncio.Lock()
        self._vocab_cache: dict[str, frozenset[str] | None] = {}

    def binary_path(self) -> str | None:
        return find_synfig_binary(self.settings.synfig_bin)

    def require_binary(self) -> str:
        binary = self.binary_path()
        if not binary:
            raise SynfigNotFoundError()
        return binary

    async def probe(self) -> dict[str, Any]:
        async with self._probe_lock:
            if self._probed is None:
                binary = self.binary_path()
                self._probed = await asyncio.to_thread(probe_synfig, binary)
            return self._probed

    def invalidate_probe(self) -> None:
        self._probed = None

    async def known_layer_types(self) -> list[str]:
        probed = await self.probe()
        layers = probed.get("layers") or []
        return sorted(set(layers) | KNOWN_LAYER_TYPES)

    async def layer_vocab(self, layer_type: str) -> frozenset[str] | None:
        """Declared param names for a layer type (None if unverifiable)."""
        cache = self._vocab_cache
        key = layer_type.lower()
        if key in cache:
            return cache[key]
        binary = self.binary_path()
        vocab = None
        if binary:
            from ..cli.info import layer_vocabulary

            vocab = await asyncio.to_thread(layer_vocabulary, binary, layer_type)
        cache[key] = vocab
        return vocab

    async def after_mutation(self, session: ProjectSession) -> None:
        if self.settings.autosave and session.path:
            from ..document import io

            await asyncio.to_thread(io.write_project, session.tree, session.path, backup=True)


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def tool(server: FastMCP) -> Callable[[FuncT], FuncT]:
    """Register a tool, converting SynfigMCPError into JSON-structured errors."""

    def decorator(fn: FuncT) -> FuncT:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except SynfigMCPError as exc:
                logger.warning("tool error: %s", exc)
                raise RuntimeError(json_dumps(exc.to_dict())) from exc

        return server.tool()(wrapper)  # type: ignore[return-value]

    return decorator


def int_in_range(name: str, value: Any, low: int, high: int) -> int:
    try:
        intval = int(value)
    except (TypeError, ValueError) as exc:
        from ..errors import ParameterError

        raise ParameterError(f"{name} must be an integer between {low} and {high}.") from exc
    if not low <= intval <= high:
        from ..errors import LimitExceededError

        raise LimitExceededError(f"{name}={intval} is outside the allowed range {low}..{high}.")
    return intval
