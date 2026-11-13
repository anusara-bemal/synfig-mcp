"""
Filesystem path validator for the user-granted permission model.

Paths must resolve inside a directory root the user has *granted* (see
:mod:`synfig_mcp.security.permissions`).  Traversal (``..``), symlink and NTFS
junction escapes, extension restrictions and existence checks are all enforced
here; the grant model only decides *which* roots count.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import tempfile
from pathlib import Path

from synfig_mcp.errors import SecuritySandboxError


def is_overly_broad_root(path: Path | str) -> tuple[bool, str]:
    """Check if a candidate workspace root is dangerously broad (drive root, system dir, user home root)."""
    p = Path(path).resolve()

    # 1. Drive root (e.g. C:\ or /)
    if p == Path(p.anchor):
        return True, "drive root is overly broad; specify a project-specific directory"

    # 2. Windows system dirs
    sys_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    if sys_root:
        res_sys = Path(sys_root).resolve()
        if p == res_sys or res_sys in p.parents:
            return True, "Windows system directory is not allowed as a workspace root"

    # 3. Program Files
    for pf_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        val = os.environ.get(pf_var)
        if val:
            res_pf = Path(val).resolve()
            if p == res_pf or res_pf in p.parents:
                return True, f"{pf_var} directory is not allowed as a workspace root"

    # 4. User home root directly
    home = Path.home().resolve()
    if p == home:
        return (
            True,
            "User home directory directly is overly broad; specify a dedicated project subfolder",
        )
    if p == home.parent:
        return True, "User profiles directory is overly broad"

    # 5. POSIX system dirs
    if str(p) in {"/", "/root", "/home", "/Users", "/etc", "/usr", "/bin", "/sbin", "/var"}:
        return True, "system directory is overly broad"

    return False, ""


def get_default_allowed_roots() -> list[Path]:
    """Return the currently granted roots, ensuring roots are narrow and secure.

    Roots are the user's granted directories (config/env defaults plus anything
    added at runtime with ``permission_grant``).  Overly broad roots are still
    filtered out defensively.
    """
    from synfig_mcp.security.permissions import permissions

    roots: list[Path] = []
    for r in permissions.roots():
        resolved = r.resolve()
        broad, _ = is_overly_broad_root(resolved)
        if not broad:
            roots.append(resolved)

    # Scoped user temp directory (e.g. AppData/Local/Temp or /tmp)
    temp_dir = Path(tempfile.gettempdir()).resolve()
    if temp_dir not in roots:
        roots.append(temp_dir)
    return roots


def get_path_mappings() -> list[tuple[str, Path]]:
    """Parse SYNFIG_MCP_PATH_MAPPING into (client prefix, host root) pairs.

    Informational only: it lets diagnostics report how client/container paths map
    to host paths. It never widens the sandbox - validate_path still enforces the
    allowed roots.
    """
    raw = os.environ.get("SYNFIG_MCP_PATH_MAPPING", "").strip()
    mappings: list[tuple[str, Path]] = []
    if not raw:
        return mappings

    # JSON object form: {"C:/client/dir": "/host/dir"}
    if raw.startswith("{") and raw.endswith("}"):
        try:
            import json

            data = json.loads(raw)
            for k, v in data.items():
                mappings.append((str(k).replace("\\", "/").rstrip("/"), Path(v).resolve()))
            return mappings
        except Exception:
            pass

    # Separator form: /client/path=C:\host\path (comma or semicolon separated)
    for item in re.split(r"[,;]", raw):
        item = item.strip()
        if "=" in item:
            src, dst = item.split("=", 1)
            mappings.append(
                (src.strip().replace("\\", "/").rstrip("/"), Path(dst.strip()).resolve())
            )
    return mappings


def validate_path(
    target_path: Path | str,
    allowed_roots: list[Path] | None = None,
    allowed_extensions: set[str] | None = None,
    must_exist: bool = False,
    for_write: bool = False,
) -> Path:
    """
    Ensure target_path resolves inside a granted root, has an allowed extension,
    and resolves symlinks / parent traversal ('..') safely.

    ``for_write=True`` additionally requires the containing grant to be writable;
    use it for every path the server will create or overwrite.

    Raises:
        SecuritySandboxError: If the path escapes every granted root or has a
            forbidden extension, or a write is attempted in a read-only grant.
        FileNotFoundError: If must_exist is True and the path does not exist.
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
            f"Access to path '{target_path}' is denied by the workspace permission model. "
            f"Path must reside within a granted root: {[str(r) for r in roots]}. "
            f"Grant access with permission_grant(path=...)."
        )

    # When the caller only supplied explicit roots, treat them as writable.
    if for_write and allowed_roots is None:
        _require_writable(resolved_target, target_path)

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


def _require_writable(resolved_target: Path, original: Path | str) -> None:
    """Raise unless the grant covering ``resolved_target`` is writable."""
    from synfig_mcp.security.permissions import permissions

    for grant in permissions.grants():
        if resolved_target == grant.path or grant.path in resolved_target.parents:
            if not grant.write:
                raise SecuritySandboxError(
                    f"Write to '{original}' is denied: the grant for '{grant.path}' is read-only."
                )
            return
    # Not covered by a user grant (e.g. the implicit temp dir) - allowed.


def safe_write_bytes(target: Path | str, data: bytes, *, backup: bool = True) -> Path:
    """Atomically write ``data`` to ``target``, optionally keeping a ``.bak`` copy.

    The write goes to a sibling temp file that is flushed and ``fsync``-ed, then
    ``os.replace``-d over the destination, so a crash mid-write can never leave a
    truncated document behind.  When ``backup`` is set and the file already
    exists, the previous contents are preserved as ``<name>.bak``.

    Permission errors (read-only file/directory) surface as a typed
    :class:`SecuritySandboxError` rather than a bare ``OSError``.
    """
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if backup and target_path.exists():
        with contextlib.suppress(OSError):
            shutil.copy2(target_path, target_path.with_name(target_path.name + ".bak"))

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target_path.parent), prefix=f".{target_path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target_path)
    except PermissionError as err:
        raise SecuritySandboxError(
            f"Cannot write '{target_path}': the file or directory is not writable ({err})."
        ) from err
    finally:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
    return target_path
