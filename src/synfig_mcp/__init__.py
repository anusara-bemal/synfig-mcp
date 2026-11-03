# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""synfig-mcp: Model Context Protocol server for Synfig Studio."""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__", "create_server"]


def create_server(*args, **kwargs):  # type: ignore[no-untyped-def]
    from .server import create_server as _create_server

    return _create_server(*args, **kwargs)
