"""
Configuration settings for synfig-mcp server and backends.
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


def get_default_workspace_roots() -> list[Path]:
    """
    Resolve default workspace roots defensively.
    1. SYNFIG_MCP_WORKSPACE_ROOTS env var (if set, os.pathsep or comma separated).
    2. Dedicated ~/Documents/SynfigMCP directory only (created on first run).
       cwd is NEVER included by default to prevent leaking repositories or arbitrary launch directories.
    """
    env_roots = os.environ.get("SYNFIG_MCP_WORKSPACE_ROOTS")
    if env_roots:
        roots: list[Path] = []
        sep = os.pathsep if os.pathsep in env_roots else ("," if "," in env_roots else None)
        raw_list = env_roots.split(sep) if sep else [env_roots]
        for p in raw_list:
            p_strip = p.strip()
            if p_strip:
                roots.append(Path(p_strip).expanduser().resolve())
        if roots:
            return roots

    default_dir = Path.home() / "Documents" / "SynfigMCP"
    try:
        default_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        default_dir = Path.home() / ".synfig" / "workspace"
        default_dir.mkdir(parents=True, exist_ok=True)

    return [default_dir.resolve()]


ProfileType = Literal["core", "anim", "fx", "rig", "assets", "review", "all"]


def get_default_profile() -> ProfileType:
    """Resolve the active tool profile.

    The default is ``all`` so a freshly installed server exposes the complete
    Synfig feature set (every layer, parameter, animation, render and review
    tool).  Token constrained clients can narrow it down with
    ``SYNFIG_MCP_PROFILE=core|anim|fx|rig|assets|review``.
    """
    p = os.environ.get("SYNFIG_MCP_PROFILE", "all").lower()
    if p in ("core", "anim", "fx", "rig", "assets", "review", "all"):
        return p  # type: ignore[return-value]
    return "all"


def get_default_backend_mode() -> Literal["auto", "live", "headless"]:
    mode = os.environ.get("SYNFIG_MCP_BACKEND", "auto").lower()
    if mode in ("live", "headless", "auto"):
        return mode  # type: ignore[return-value]
    return "auto"


def get_default_bridge_port() -> int:
    try:
        return int(os.environ.get("SYNFIG_MCP_PORT", "19998"))
    except ValueError:
        return 19998


def get_default_token_path() -> Path:
    env_token = os.environ.get("SYNFIG_MCP_TOKEN_PATH")
    if env_token:
        return Path(env_token).expanduser().resolve()
    synfig_dir = Path.home() / ".synfig"
    default_token = synfig_dir / "mcp_token"
    if default_token.is_file():
        return default_token
    # If default token is missing, find the most recently modified mcp_token_<pid>
    candidates = sorted(
        synfig_dir.glob("mcp_token_*"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if candidates:
        return candidates[0]
    return default_token


class Settings(BaseModel):
    """Runtime configuration for synfig-mcp."""

    profile: ProfileType = Field(
        default_factory=get_default_profile,
        description="Tool profile to expose: 'all' (default, every Synfig tool), 'core' (minimal), 'anim', 'fx', 'rig', 'assets', or 'review'.",
    )
    backend_mode: Literal["auto", "live", "headless"] = Field(
        default_factory=get_default_backend_mode,
        description="Backend selection mode: 'live' (Studio), 'headless' (CLI/sif), or 'auto'.",
    )
    bridge_host: str = Field(
        default_factory=lambda: os.environ.get("SYNFIG_MCP_HOST", "127.0.0.1"),
        description="Host for the Synfig Studio native bridge socket.",
    )
    bridge_port: int = Field(
        default_factory=get_default_bridge_port,
        description="TCP port for the Synfig Studio native bridge.",
    )
    bridge_token_path: Path = Field(
        default_factory=get_default_token_path,
        description="Path to session authentication token written by patched Studio.",
    )
    bridge_connect_timeout_seconds: float = Field(
        default=2.0,
        description="Timeout when probing the live bridge socket.",
    )
    synfig_cli_path: Path | None = Field(
        default=None,
        description="Explicit path to 'synfig' CLI executable. Discovered via PATH if None.",
    )
    workspace_roots: list[Path] = Field(
        default_factory=get_default_workspace_roots,
        description="Allowed filesystem directory roots for sandboxed file operations.",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level for structlog (DEBUG, INFO, WARNING, ERROR).",
    )


settings = Settings()
