"""
Filesystem sandbox validator preventing directory traversal and unauthorized path access.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from synfig_mcp.config import settings
from synfig_mcp.errors import SecuritySandboxError


def get_default_allowed_roots() -> list[Path]:
    """Return default allowed workspace roots, including system temp."""
    roots = [r.resolve() for r in settings.workspace_roots]
    temp_dir = Path(tempfile.gettempdir()).resolve()
    if temp_dir not in roots:
        roots.append(temp_dir)
    return roots


def validate_path(
    target_path: Path | str,
    allowed_roots: list[Path] | None = None,
    allowed_extensions: set[str] | None = None,
    must_exist: bool = False,
) -> Path:
    """
    Ensure target_path resolves inside one of the allowed_roots, has an allowed extension,
    and resolves symlinks / parent traversal ('..') safely.

    Raises:
        SecuritySandboxError: If path attempts to escape sandbox or has forbidden extension.
        FileNotFoundError: If must_exist is True and path does not exist.
    """
    path_obj = Path(target_path)
    # Canonicalize and resolve all symlinks and '..' components
    resolved_target = path_obj.resolve()

    roots = [r.resolve() for r in (allowed_roots or get_default_allowed_roots())]

    # Verify target or its parent is contained within at least one allowed root
    in_sandbox = False
    for root in roots:
        try:
            # If resolved_target is root or a descendant of root
            if resolved_target == root or root in resolved_target.parents:
                in_sandbox = True
                break
        except Exception:
            continue

    if not in_sandbox:
        raise SecuritySandboxError(
            f"Access to path '{target_path}' is denied by workspace sandbox. "
            f"Path must reside within configured workspace roots: {[str(r) for r in roots]}"
        )

    # Restrict file extensions if provided
    if allowed_extensions is not None:
        ext = resolved_target.suffix.lower()
        valid_exts = {e.lower() for e in allowed_extensions}
        if ext not in valid_exts:
            raise SecuritySandboxError(
                f"File extension '{ext}' is not permitted for '{target_path}'. "
                f"Allowed extensions: {sorted(valid_exts)}"
            )

    if must_exist and not resolved_target.exists():
        raise FileNotFoundError(f"File not found: {resolved_target}")

    return resolved_target
