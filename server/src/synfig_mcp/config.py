"""
Configuration settings for synfig-mcp server and backends.
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from synfig_mcp.security.sandbox import is_overly_broad_root


def get_default_workspace_roots() -> list[Path]:
    """
    Resolve default workspace roots defensively.
    1. SYNFIG_MCP_WORKSPACE_ROOTS env var (if set, os.pathsep or comma separated).
    2. Dedicated ~/Documents/SynfigMCP directory (created on first run).
    3. Include Path.cwd() only if it is not dangerously broad (e.g. drive root, system dir, home dir).
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

    roots = [default_dir.resolve()]

    # Safely evaluate cwd: if it's not overly broad, also include it
    try:
        cwd = Path.cwd().resolve()
        broad, _ = is_overly_broad_root(cwd)
        if not broad and cwd not in roots:
            roots.append(cwd)
    except Exception:
        pass

    return roots


class Settings(BaseModel):
    """Runtime configuration for synfig-mcp."""

    backend_mode: Literal["auto", "live", "headless"] = Field(
        default="auto",
        description="Backend selection mode: 'live' (Studio), 'headless' (CLI/sif), or 'auto'.",
    )
    bridge_host: str = Field(
        default="127.0.0.1",
        description="Host for the Synfig Studio native bridge socket.",
    )
    bridge_port: int = Field(
        default=19998,
        description="TCP port for the Synfig Studio native bridge.",
    )
    bridge_token_path: Path = Field(
        default=Path.home() / ".synfig" / "mcp_token",
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
