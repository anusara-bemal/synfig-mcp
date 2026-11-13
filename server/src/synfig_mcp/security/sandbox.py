"""
Project-aware path validation for Synfig MCP file operations.

This module used to be a workspace jail: every file had to live inside
``Documents/SynfigMCP`` or temp, which blocked legitimate assets in Downloads
and forced users to copy files around.  It is now a thin validation layer over
:mod:`synfig_mcp.security.access`:

* paths explicitly supplied by the user (tool arguments / attachments) are
  authorised directly,
* the active Synfig project directory and its imported assets are authorised
  by the native bridge,
* explicitly approved folders (e.g. Downloads) are remembered,
* minimal safety checks always apply: traversal, symlink/junction escapes,
  system folders, credential folders, executables, extension allow-lists.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from synfig_mcp.errors import SecuritySandboxError
from synfig_mcp.security.access import (
    EXECUTABLE_EXTENSIONS,
    get_access_controller,
    get_temp_root,
    has_link_redirect,
    is_credentials_path,
    is_overly_broad_root,
    is_system_path,
)

__all__ = [
    "get_default_allowed_roots",
    "get_path_mappings",
    "is_overly_broad_root",
    "resolve_client_path",
    "validate_path",
]


def get_default_allowed_roots() -> list[Path]:
    """Folder-level roots granted by configuration, approvals and the project.

    Kept for diagnostics and staging; it is no longer a gate that every file
    must pass through.
    """
    from synfig_mcp.config import settings

    roots: list[Path] = [r.resolve() for r in settings.workspace_roots]
    roots.extend(get_access_controller().allowed_roots())
    temp_dir = get_temp_root()
    if temp_dir not in roots:
        roots.append(temp_dir)
    return roots


def get_path_mappings() -> list[tuple[str, Path]]:
    """Parse SYNFIG_MCP_PATH_MAPPING env var into prefix mappings (containers)."""
    raw = os.environ.get("SYNFIG_MCP_PATH_MAPPING", "").strip()
    mappings: list[tuple[str, Path]] = []
    if not raw:
        return mappings

    if raw.startswith("{") and raw.endswith("}"):
        try:
            import json

            data = json.loads(raw)
            for k, v in data.items():
                mappings.append((k.replace("\\", "/").rstrip("/"), Path(v).resolve()))
            return mappings
        except Exception:
            pass

    for item in re.split(r"[,;]", raw):
        item = item.strip()
        if "=" in item:
            src, dst = item.split("=", 1)
            mappings.append(
                (src.strip().replace("\\", "/").rstrip("/"), Path(dst.strip()).resolve())
            )
    return mappings


def resolve_client_path(target_path: Path | str) -> Path:
    """Resolve a client path against the host filesystem (container mounts)."""
    path_str = str(target_path).replace("\\", "/")
    mappings = get_path_mappings()

    for remote_prefix, local_root in mappings:
        if path_str == remote_prefix:
            return local_root
        if path_str.startswith(remote_prefix + "/"):
            rel_sub = path_str[len(remote_prefix) + 1 :]
            candidate = local_root / Path(rel_sub)
            if candidate.exists():
                return candidate.resolve()

    path_obj = Path(target_path).expanduser()
    try:
        # resolve() resolves symlink/junction ancestors even when the final
        # component does not exist yet, so a link escape is still detected for
        # new output paths.  strict=False keeps non-existent saves/renders valid.
        return path_obj.resolve()
    except Exception:
        return Path(os.path.abspath(str(path_obj)))


def _check_denied(resolved: Path, allowed_extensions: set[str] | None) -> None:
    if is_system_path(resolved):
        raise SecuritySandboxError(
            f"Path '{resolved}' denied: Windows system / program folders are never accessible"
        )
    if is_credentials_path(resolved):
        raise SecuritySandboxError(
            f"Path '{resolved}' denied: credential and private-key locations are never accessible"
        )
    extension = resolved.suffix.lower()
    if extension in EXECUTABLE_EXTENSIONS and not (
        allowed_extensions and extension in {e.lower() for e in allowed_extensions}
    ):
        raise SecuritySandboxError(
            f"File extension '{extension}' is an executable/script and cannot be imported"
        )


def validate_path(
    target_path: Path | str,
    allowed_roots: list[Path] | None = None,
    allowed_extensions: set[str] | None = None,
    must_exist: bool = False,
    user_intent: bool = False,
) -> Path:
    """Validate a file path under the project-aware access policy.

    ``user_intent=True`` marks a path the user explicitly supplied (an
    attachment or a direct tool argument).  Such files are authorised without
    copying them anywhere, unless a link redirect or a denied location is
    involved.  ``allowed_roots``, when given explicitly, remains a hard
    constraint for callers that need one.
    """
    path_text = str(target_path).replace("\\", "/")
    if any(part == ".." for part in path_text.split("/")):
        raise SecuritySandboxError(
            f"Path '{target_path}' denied: directory traversal is not permitted"
        )

    resolved_target = resolve_client_path(target_path)

    if allowed_extensions is not None:
        extension = resolved_target.suffix.lower()
        if extension not in {ext.lower() for ext in allowed_extensions}:
            allowed = ", ".join(sorted(allowed_extensions))
            raise SecuritySandboxError(
                f"File extension '{extension or '<none>'}' is not permitted; allowed: {allowed}"
            )

    _check_denied(resolved_target, allowed_extensions)

    if allowed_roots is not None:
        roots = [Path(root).expanduser().resolve() for root in allowed_roots]
        if not any(resolved_target == root or root in resolved_target.parents for root in roots):
            raise SecuritySandboxError(
                f"Path '{target_path}' denied: outside the explicitly requested roots"
            )
    else:
        controller = get_access_controller()
        allowed, _reason = controller.is_allowed(resolved_target)
        if not allowed and user_intent and not has_link_redirect(Path(os.path.abspath(path_text))):
            controller.register_attachment(resolved_target)
            allowed = True
        if not allowed:
            temp_root = get_temp_root()
            allowed = resolved_target == temp_root or temp_root in resolved_target.parents
        if not allowed:
            folder = resolved_target.parent
            raise SecuritySandboxError(
                f"Path '{target_path}' is not yet authorised for Synfig MCP. "
                f"It is outside the active Synfig project and no approval covers '{folder}'. "
                f"Approve the folder once with access_approve(folder=\"{folder}\"), "
                "or open/import the file in Synfig Studio. No manual copying is required."
            )

    if must_exist and not resolved_target.exists():
        raise FileNotFoundError(
            f"File not found on host: '{target_path}'. Host resolved path: '{resolved_target}'."
        )

    return resolved_target
