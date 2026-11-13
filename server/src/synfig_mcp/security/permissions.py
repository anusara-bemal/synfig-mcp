"""
Runtime, user-granted filesystem permission model.

The server no longer treats the workspace as an opaque sandbox the user cannot
see.  Instead the user *grants* access to specific directory roots at runtime
(through the ``permission_grant`` tool or the ``SYNFIG_MCP_WORKSPACE_ROOTS``
environment variable).  Every path the server touches must resolve inside one of
those granted roots; path traversal, symlink/junction escapes, extension
restrictions and existence checks are still enforced.

This keeps the security guarantees (no escape, no arbitrary read/write) while
making normal local project access straightforward: the user names the folders
the agent may work in, and the agent works there.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from synfig_mcp.errors import SecurityError


@dataclass
class Grant:
    """A single user-granted directory root."""

    path: Path
    read: bool = True
    write: bool = True
    source: str = "config"

    def as_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "read": self.read,
            "write": self.write,
            "source": self.source,
        }


@dataclass
class PermissionStore:
    """Thread-safe registry of granted directory roots.

    The store is process-global (one server process serves one user session) but
    every mutating operation is guarded by a lock so concurrent tool calls cannot
    corrupt it.
    """

    _grants: dict[str, Grant] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _loaded: bool = False

    # -- loading -----------------------------------------------------------

    def load_defaults(self) -> None:
        """Seed grants from config once, on first use.

        Config already resolves ``SYNFIG_MCP_WORKSPACE_ROOTS`` (env) and falls
        back to a dedicated ``~/Documents/SynfigMCP`` project folder, so the
        store starts with exactly the roots the user configured.
        """
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
            from synfig_mcp.config import settings

            for root in settings.workspace_roots:
                self._add(root, read=True, write=True, source="config", resolve=True)

    def _add(self, path: Path, *, read: bool, write: bool, source: str, resolve: bool) -> Grant:
        resolved = path.expanduser().resolve() if resolve else path
        key = _key(resolved)
        existing = self._grants.get(key)
        if existing is not None:
            # Widen permissions rather than silently narrowing a prior grant.
            existing.read = existing.read or read
            existing.write = existing.write or write
            return existing
        grant = Grant(path=resolved, read=read, write=write, source=source)
        self._grants[key] = grant
        return grant

    # -- mutation ----------------------------------------------------------

    def grant(
        self,
        path: str | Path,
        *,
        read: bool = True,
        write: bool = True,
        source: str = "user",
    ) -> Grant:
        """Grant access to ``path`` and return the resulting grant."""
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        resolved = candidate.expanduser().resolve()
        if not resolved.exists():
            raise SecurityError(f"Cannot grant access: '{resolved}' does not exist.")
        if not resolved.is_dir():
            resolved = resolved.parent
        with self._lock:
            return self._add(resolved, read=read, write=write, source=source, resolve=False)

    def revoke(self, path: str | Path) -> bool:
        """Remove a grant; returns True if one was removed."""
        key = _key(Path(path).expanduser().resolve())
        with self._lock:
            return self._grants.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._grants.clear()
            self._loaded = True

    # -- queries -----------------------------------------------------------

    def grants(self) -> list[Grant]:
        self.load_defaults()
        with self._lock:
            return list(self._grants.values())

    def roots(self) -> list[Path]:
        """All granted roots (readable or writable)."""
        return [g.path for g in self.grants()]

    def resolve_within(self, target: Path | str, *, write: bool = False) -> Path | None:
        """Return the resolved target if it is inside a suitable grant, else None.

        ``write=True`` requires a writable grant.  Symlinks and ``..`` are
        resolved first, so an escape through either is not contained by any root.
        """
        resolved = Path(target).expanduser().resolve()
        for grant in self.grants():
            if write and not grant.write:
                continue
            if not grant.read and not write:
                continue
            if resolved == grant.path or grant.path in resolved.parents:
                return resolved
        return None


def _key(path: Path) -> str:
    return os.path.normcase(str(path))


#: Process-global permission store.
permissions = PermissionStore()
