"""
Ingest an image the MCP client uploaded (a reference picture or a rig sheet).

An MCP client cannot hand the server a file path into its own filesystem, but it
*can* attach an ``ImageContent`` block (base64 ``data`` + ``mime_type``).  This
adapter turns that block - or a local path the server is already allowed to read
- into a hardened PNG written inside an authorized directory, so the rest of the
pipeline (``slice_rig_sheet``, ``character_rig_from_parts``) can consume it like
any other asset.

Hardening reuses :func:`synfig_mcp.assets.security.raster_hardening.sanitize_raster_bytes`:
magic-byte check, a 16-megapixel ceiling (also a PIL decompression-bomb guard) and
a full pixel rebuild that drops every EXIF/metadata payload.  The write goes
through :func:`synfig_mcp.security.sandbox.safe_write_bytes`, so a crash mid-write
cannot leave a truncated file behind.
"""

from __future__ import annotations

import base64
import binascii
import io
import re
from pathlib import Path
from typing import Any

from synfig_mcp.assets.security.raster_hardening import sanitize_raster_bytes
from synfig_mcp.errors import SecuritySandboxError, ValidationError
from synfig_mcp.security.sandbox import safe_write_bytes, validate_path

#: Largest accepted base64 payload (before decoding), ~96 MB.
MAX_BASE64_CHARS = 96 * 1024 * 1024

_DATA_URL = re.compile(r"^data:(?P<mime>[\w.+-]+/[\w.+-]+)?;base64,(?P<data>.*)$", re.DOTALL)
_SAFE_STEM = re.compile(r"[^A-Za-z0-9_.-]+")


def decode_image_payload(image_base64: str) -> tuple[bytes, str]:
    """Decode a base64 image payload, tolerating a ``data:`` URL wrapper.

    Returns ``(raw_bytes, mime_type)``; the mime type defaults to
    ``application/octet-stream`` when the payload carries no ``data:`` prefix.
    """
    if not image_base64 or not image_base64.strip():
        raise ValidationError("Image payload is empty.")
    text = image_base64.strip()
    mime = "application/octet-stream"
    match = _DATA_URL.match(text)
    if match:
        mime = match.group("mime") or mime
        text = match.group("data")
    if len(text) > MAX_BASE64_CHARS:
        raise ValidationError(
            f"Image payload is too large ({len(text)} base64 chars > {MAX_BASE64_CHARS})."
        )
    try:
        raw = base64.b64decode(text, validate=False)
    except (binascii.Error, ValueError) as err:
        raise ValidationError(f"Image payload is not valid base64: {err}") from err
    if not raw:
        raise ValidationError("Image payload decoded to zero bytes.")
    return raw, mime


def _target_path(output_dir: str | Path, filename: str, suffix: str) -> Path:
    """Resolve ``output_dir/filename`` inside a granted root, forcing ``suffix``."""
    directory = validate_path(output_dir, for_write=True)
    stem = _SAFE_STEM.sub("_", Path(filename).stem).strip("_.") or "reference"
    candidate = directory / f"{stem}{suffix}"
    return validate_path(candidate, allowed_extensions={suffix}, for_write=True)


def ingest_image_content(
    image_base64: str,
    output_dir: str | Path,
    *,
    filename: str = "reference",
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Write an uploaded ``ImageContent`` payload to a hardened PNG inside a granted root.

    Args:
        image_base64: The block's ``data`` field (raw base64 or a ``data:`` URL).
        output_dir: Directory the server may write to (must be a granted root).
        filename: Base name for the written file (``.png`` is forced).
        mime_type: The block's declared ``mime_type`` (informational).

    Returns: ``{path, width, height, bytes, source, mime_type}``.
    """
    raw, detected_mime = decode_image_payload(image_base64)
    declared = mime_type or detected_mime
    try:
        clean = sanitize_raster_bytes(raw)
    except ValueError as err:
        raise ValidationError(f"Uploaded image rejected: {err}") from err

    target = _target_path(output_dir, filename, ".png")
    buffer = io.BytesIO()
    clean.save(buffer, format="PNG", optimize=True)
    data = buffer.getvalue()
    safe_write_bytes(target, data, backup=False)

    return {
        "path": str(target),
        "width": clean.width,
        "height": clean.height,
        "bytes": len(data),
        "source": "image_content",
        "mime_type": declared,
    }


def resolve_image_input(
    output_dir: str | Path,
    *,
    image_base64: str | None = None,
    file_path: str | None = None,
    filename: str = "reference",
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Resolve an uploaded image or a local path into a single usable PNG.

    Exactly one of ``image_base64`` / ``file_path`` must be given.  A local path
    is validated against the granted roots and returned unchanged (no copy); an
    uploaded payload is hardened and written into ``output_dir``.
    """
    if bool(image_base64) == bool(file_path):
        raise ValidationError("Give exactly one of 'image_base64' or 'file_path'.")
    if file_path is not None:
        from synfig_mcp.characters.cutout import IMAGE_EXTENSIONS

        path = validate_path(file_path, allowed_extensions=IMAGE_EXTENSIONS, must_exist=True)
        return {"path": str(path), "source": "file_path", "mime_type": mime_type or ""}
    assert image_base64 is not None
    return ingest_image_content(image_base64, output_dir, filename=filename, mime_type=mime_type)


def require_authorized_output_dir(output_dir: str | Path | None) -> Path:
    """Return a writable output directory, falling back to the first granted root.

    Raises :class:`SecuritySandboxError` when the user has granted no roots, so a
    misconfiguration surfaces as a clear error instead of a silent write.
    """
    from synfig_mcp.security.sandbox import get_default_allowed_roots

    if output_dir is not None:
        return validate_path(output_dir, for_write=True)
    roots = get_default_allowed_roots()
    if not roots:
        raise SecuritySandboxError(
            "No directory is authorized for writing; call permission_grant(path=...) first."
        )
    return validate_path(roots[0], for_write=True)
