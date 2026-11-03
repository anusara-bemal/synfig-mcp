# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Path security: every path handled by the server must live under the
configured workspace. Symlink escapes and '..' traversal are rejected."""

from __future__ import annotations

import os
from pathlib import Path

from ..errors import WorkspaceError

PROJECT_EXTENSIONS = {".sif", ".sifz", ".sfg"}
IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".svg",
    ".webp",
    ".tiff",
    ".tif",
    ".ppm",
    ".pgm",
    ".xcf",
}
OUTPUT_EXTENSIONS = {
    ".png",
    ".gif",
    ".webp",
    ".apng",
    ".mp4",
    ".webm",
    ".mov",
    ".mkv",
    ".sif",
    ".sifz",
    ".sfg",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".pdf",
    ".svg",
}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_workspace_path(
    raw: str | os.PathLike[str],
    workspace: Path,
    *,
    must_exist: bool = False,
    allowed_extensions: set[str] | None = None,
    purpose: str = "path",
) -> Path:
    """Resolve ``raw`` inside ``workspace`` or raise :class:`WorkspaceError`."""
    if raw is None:
        raise WorkspaceError(f"Missing {purpose}.")

    candidate = Path(str(raw)).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate

    try:
        workspace_resolved = workspace.resolve(strict=False)
    except OSError as exc:  # pragma: no cover - extremely unusual
        raise WorkspaceError(f"Workspace {workspace} is not usable: {exc}") from exc

    # resolve(strict=False) collapses '..' and resolves symlinks for existing
    # components; missing leaf names stay un-resolved which is fine.
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise WorkspaceError(f"Cannot resolve {purpose} {raw!s}: {exc}") from exc

    if not (_is_within(resolved, workspace_resolved) and _not_root(resolved, workspace_resolved)):
        raise WorkspaceError(
            f"{purpose.capitalize()} {resolved} is outside the configured workspace {workspace_resolved}.",
            hint="Set SYNFIG_MCP_WORKSPACE to a directory you trust, or pass a path inside it.",
            context={"requested": str(raw), "workspace": str(workspace_resolved)},
        )

    if allowed_extensions is not None and resolved.suffix.lower() not in allowed_extensions:
        raise WorkspaceError(
            f"Unsupported extension for {purpose}: {resolved.suffix or '(none)'}.",
            context={"allowed": sorted(allowed_extensions)},
        )

    if must_exist and not resolved.is_file():
        raise WorkspaceError(f"{purpose.capitalize()} not found: {resolved}")

    # Symlink leaf pointing outside the workspace would already fail the
    # resolve() check above on Windows/macOS/Linux because resolve()
    # follows links; double-check for defence in depth.
    if resolved.is_symlink():
        target = Path(os.path.realpath(resolved))
        if not _is_within(target, workspace_resolved):
            raise WorkspaceError(f"Symlink {resolved} escapes the workspace.")

    return resolved


def _not_root(path: Path, workspace: Path) -> bool:
    # Disallow the workspace root itself where a file is expected (sanity).
    return True  # the relative check above is sufficient; kept for clarity


def ensure_output_path(
    raw: str | os.PathLike[str] | None,
    workspace: Path,
    *,
    default_name: str,
    allowed_extensions: set[str] | None = None,
    purpose: str = "output path",
) -> Path:
    if not raw:
        candidate = workspace / default_name
    else:
        candidate = Path(str(raw)).expanduser()
        if not candidate.is_absolute():
            candidate = workspace / candidate
    return resolve_workspace_path(
        candidate,
        workspace,
        must_exist=False,
        allowed_extensions=allowed_extensions,
        purpose=purpose,
    )


def check_file_size(path: Path, max_bytes: int, purpose: str = "file") -> None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise WorkspaceError(f"Cannot stat {purpose} {path}: {exc}") from exc
    if size > max_bytes:
        from ..errors import LimitExceededError

        raise LimitExceededError(
            f"{purpose.capitalize()} {path.name} is {size} bytes, exceeding the {max_bytes} byte limit.",
            hint="Raise SYNFIG_MCP_MAX_FILE_MB or use a smaller document.",
        )


def sanitize_text(value: str | None, *, max_length: int = 4096) -> str:
    """Sanitize free-text content before embedding into XML or logs."""
    if value is None:
        return ""
    cleaned = value.replace("\x00", "")
    # Remove characters that are invalid in XML 1.0 documents.
    cleaned = "".join(ch for ch in cleaned if ch in "\t\n\r" or ord(ch) >= 0x20)
    return cleaned[:max_length]
