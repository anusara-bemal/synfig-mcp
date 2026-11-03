# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Read-only inspection via the synfig CLI (and local file analysis)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .binary import clean_synfig_output, parse_version, raw_command

_TIMEOUT = 30.0


def version(binary: str) -> str | None:
    _rc, out, err = raw_command(binary, ["--version"], timeout=_TIMEOUT)
    return parse_version(out + "\n" + err)


def targets(binary: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--targets"], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]


def renderers(binary: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--renderers"], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]


def layers(binary: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--layers"], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]


def layer_info(binary: str, layer_name: str) -> dict[str, Any]:
    _rc, out, err = raw_command(binary, [f"--layer-info={layer_name}"], timeout=_TIMEOUT)
    text = clean_synfig_output(out + "\n" + err)
    info: dict[str, Any] = {"layer": layer_name, "found": False, "raw": "\n".join(text)}
    params: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text:
        stripped = line.strip()
        if stripped.startswith("Layer Name:"):
            info["found"] = True
            info["localized_name"] = stripped.split(":", 1)[1].strip().replace("Localized ", "")
        elif stripped.lower().startswith("version:"):
            info["version"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("param -"):
            if current:
                params.append(current)
            current = {"name": stripped.split("-", 1)[1].strip()}
        elif current is not None:
            key, _, value = stripped.partition(":")
            key = key.strip().lower().replace(" ", "_")
            if value and key in {"localized_name", "description", "hint"}:
                current[key] = value.strip()
    if current:
        params.append(current)
    info["params"] = params
    return info


@lru_cache(maxsize=256)
def layer_vocabulary(binary: str, layer_type: str) -> frozenset[str] | None:
    """Return the declared parameter names of a layer type, or None if unknown."""
    info = layer_info(binary, layer_type)
    if not info.get("found"):
        return None
    return frozenset(p.get("name", "") for p in info.get("params", []) if p.get("name"))


def video_codecs(binary: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--target-video-codecs"], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]


def canvas_info(
    binary: str, path: str, fields: str = "width,height,fps,duration,begin_time,end_time"
) -> dict[str, Any]:
    _rc, out, err = raw_command(binary, [f"--canvas-info={fields}", path], timeout=_TIMEOUT)
    lines = [line.strip() for line in clean_synfig_output(out + "\n" + err) if line.strip()]
    result: dict[str, Any] = {"path": path, "fields": fields, "lines": lines}
    for line in lines:
        key, sep, value = line.partition("=")
        if sep:
            result[key.strip()] = value.strip()
    return result


def canvases(binary: str, path: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--canvases", path], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]


def valuenodes(binary: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--valuenodes"], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]


def modules(binary: str) -> list[str]:
    _rc, out, _ = raw_command(binary, ["--modules"], timeout=_TIMEOUT)
    return [line.strip() for line in clean_synfig_output(out) if line.strip()]
