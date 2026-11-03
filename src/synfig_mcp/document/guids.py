# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Synfig GUID generation: 32 uppercase hex characters (like Studio)."""

from __future__ import annotations

import secrets


def new_guid() -> str:
    return secrets.token_hex(16).upper()


def is_guid(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 32
        and all(c in "0123456789ABCDEFabcdef" for c in value)
    )
