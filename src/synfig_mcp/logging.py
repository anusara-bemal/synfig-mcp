# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Structured logging to stderr only (stdout is reserved for MCP stdio)."""

from __future__ import annotations

import logging
import os
import sys

_DEFAULT_FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s"


def configure_logging(level: str | None = None) -> None:
    lvl = (level or os.environ.get("SYNFIG_MCP_LOG_LEVEL") or "INFO").upper()
    numeric = getattr(logging, lvl, logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(numeric)
    # Quieten noisy third parties but keep our own logs visible.
    logging.getLogger("mcp").setLevel(max(numeric, logging.WARNING))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
