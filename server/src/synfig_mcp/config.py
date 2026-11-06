"""
Configuration settings for synfig-mcp server and backends.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


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
        default_factory=lambda: [Path.cwd()],
        description="Allowed filesystem directory roots for sandboxed file operations.",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level for structlog (DEBUG, INFO, WARNING, ERROR).",
    )


settings = Settings()
