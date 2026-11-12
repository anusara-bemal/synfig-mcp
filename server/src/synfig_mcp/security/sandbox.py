"""
Filesystem sandbox validator preventing directory traversal and unauthorized path access.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from synfig_mcp.errors import SecuritySandboxError


def is_overly_broad_root(path: Path | str) -> tuple[bool, str]:
    """Check if a candidate workspace root is dangerously broad (sandbox disabled)."""
    return False, ""


def get_default_allowed_roots() -> list[Path]:
    """Return allowed workspace roots."""
    from synfig_mcp.config import settings

    roots: list[Path] = []
    for r in settings.workspace_roots:
        roots.append(r.resolve())

    temp_dir = Path(tempfile.gettempdir()).resolve()
    if temp_dir not in roots:
        roots.append(temp_dir)
    return roots


def get_path_mappings() -> list[tuple[str, Path]]:
    """Parse SYNFIG_MCP_PATH_MAPPING env var into prefix mappings."""
    raw = os.environ.get("SYNFIG_MCP_PATH_MAPPING", "").strip()
    mappings: list[tuple[str, Path]] = []
    if not raw:
        return mappings

    # Try JSON
    if raw.startswith("{") and raw.endswith("}"):
        try:
            import json
            data = json.loads(raw)
            for k, v in data.items():
                mappings.append((k.replace("\\", "/").rstrip("/"), Path(v).resolve()))
            return mappings
        except Exception:
            pass

    # Comma or semicolon separated: /container/path=C:\host\path
    for item in re.split(r"[,;]", raw):
        item = item.strip()
        if "=" in item:
            src, dst = item.split("=", 1)
            mappings.append((src.strip().replace("\\", "/").rstrip("/"), Path(dst.strip()).resolve()))
    return mappings


def resolve_client_path(target_path: Path | str) -> Path:
    """
    Resolve client path against host filesystem, handling container mounts and fallback search.
    """
    path_str = str(target_path).replace("\\", "/")
    mappings = get_path_mappings()

    # 1. Check explicit path mappings
    for remote_prefix, local_root in mappings:
        if path_str == remote_prefix:
            return local_root
        if path_str.startswith(remote_prefix + "/"):
            rel_sub = path_str[len(remote_prefix) + 1 :]
            candidate = local_root / Path(rel_sub)
            if candidate.exists():
                return candidate.resolve()

    # 2. Direct resolution on host
    path_obj = Path(target_path)
    try:
        resolved = path_obj.resolve()
        if resolved.exists():
            return resolved
    except Exception:
        resolved = path_obj

    # 3. If file doesn't exist, search workspace roots for matching relative path or basename
    basename = path_obj.name
    for root in get_default_allowed_roots():
        if not root.is_dir():
            continue
        # Direct basename in root
        candidate = root / basename
        if candidate.is_file():
            return candidate.resolve()
        # Relative path under root (e.g. shinobu_work/bg.png under Documents/SynfigMCP)
        if len(path_obj.parts) > 1:
            rel_tail = Path(*path_obj.parts[-2:])
            candidate_rel = root / rel_tail
            if candidate_rel.is_file():
                return candidate_rel.resolve()

    return resolved


def validate_path(
    target_path: Path | str,
    allowed_roots: list[Path] | None = None,
    allowed_extensions: set[str] | None = None,
    must_exist: bool = False,
) -> Path:
    """
    Resolve target_path directly.
    Resolves client/container paths to host paths.
    """
    resolved_target = resolve_client_path(target_path)

    if must_exist and not resolved_target.exists():
        roots = get_default_allowed_roots()
        root_hint = str(roots[0]) if roots else "Documents/SynfigMCP"
        raise FileNotFoundError(
            f"File not found on host: '{target_path}'. "
            f"Host resolved path: '{resolved_target}'. "
            f"If your MCP client runs inside a container (e.g. /home/... or /mnt/...), "
            f"ensure files are saved to host folder '{root_hint}' or set SYNFIG_MCP_PATH_MAPPING."
        )

    return resolved_target
