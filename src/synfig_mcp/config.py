# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Configuration: environment variables plus optional synfig-mcp.toml.

Precedence: explicit env var > synfig-mcp.toml > built-in default.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - 3.10 only
    import tomli as tomllib


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        raw: Any = tomllib.load(fh)
        if isinstance(raw, dict):
            return {str(k): v for k, v in raw.items()}
        return {}


_TRUE = {"1", "true", "yes", "on"}


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the server."""

    synfig_bin: str | None = None
    synfig_studio_bin: str | None = None
    workspace: Path = field(default_factory=Path.cwd)
    log_level: str = "INFO"
    render_timeout: float = 300.0
    max_frames: int = 20000
    max_resolution: int = 8192
    max_layers: int = 5000
    max_file_mb: int = 256
    unit_px: float = 60.0
    unit_system: str = "units"  # "units" | "pixels"
    history_depth: int = 50
    render_workers: int = 2
    autosave: bool = False
    auto_open_studio: bool = False

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def toml_path(self) -> Path:
        return self.workspace / "synfig-mcp.toml"


def load_settings(
    environ: dict[str, str] | None = None, *, start_dir: Path | None = None
) -> Settings:
    """Load settings from env vars and, if present, ``synfig-mcp.toml``."""
    env = dict(os.environ if environ is None else environ)
    workspace = Path(env.get("SYNFIG_MCP_WORKSPACE") or (start_dir or Path.cwd())).expanduser()
    toml_path = workspace / "synfig-mcp.toml"
    toml: dict[str, Any] = {}
    if toml_path.is_file():
        try:
            toml = _load_toml(toml_path)
        except Exception:
            # A broken TOML must not kill the server; fall back to env/defaults.
            toml = {}

    def pick(name: str) -> Any:
        if name in env:  # explicit env wins
            return env[name]
        # Env names are SYNFIG_MCP_* / SYNFIG_BIN; TOML keys are the
        # lower-case setting names (max_frames, unit_px, ...).
        toml_key = name.removeprefix("SYNFIG_MCP_").removeprefix("SYNFIG_").lower()
        return toml.get(toml_key)

    unit_system = str(pick("SYNFIG_MCP_UNIT_SYSTEM") or "units").strip().lower()
    if unit_system not in {"units", "pixels"}:
        unit_system = "units"

    try:
        workspace = workspace.resolve(strict=False)
    except OSError:
        workspace = workspace.absolute()

    return Settings(
        synfig_bin=(str(pick("SYNFIG_BIN")).strip() or None) if pick("SYNFIG_BIN") else None,
        synfig_studio_bin=(str(pick("SYNFIG_STUDIO_BIN")).strip() or None)
        if pick("SYNFIG_STUDIO_BIN")
        else None,
        workspace=workspace,
        log_level=str(pick("SYNFIG_MCP_LOG_LEVEL") or "INFO").upper(),
        render_timeout=_as_float(pick("SYNFIG_MCP_RENDER_TIMEOUT"), 300.0),
        max_frames=_as_int(pick("SYNFIG_MCP_MAX_FRAMES"), 20000),
        max_resolution=_as_int(pick("SYNFIG_MCP_MAX_RESOLUTION"), 8192),
        max_layers=_as_int(pick("SYNFIG_MCP_MAX_LAYERS"), 5000),
        max_file_mb=_as_int(pick("SYNFIG_MCP_MAX_FILE_MB"), 256),
        unit_px=max(_as_float(pick("SYNFIG_MCP_UNIT_PX"), 60.0), 1.0),
        unit_system=unit_system,
        history_depth=max(_as_int(pick("SYNFIG_MCP_HISTORY_DEPTH"), 50), 1),
        render_workers=max(_as_int(pick("SYNFIG_MCP_RENDER_WORKERS"), 2), 1),
        autosave=_as_bool(pick("SYNFIG_MCP_AUTOSAVE"), False),
        auto_open_studio=_as_bool(pick("SYNFIG_MCP_AUTO_OPEN_STUDIO"), False),
    )
