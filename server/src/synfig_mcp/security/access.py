"""
Project-aware file access control for the direct-GUI Synfig MCP.

The old workspace jail (only ``Documents/SynfigMCP`` + temp) is gone.  Access
authority now comes from the production context itself:

* the active Synfig Studio project directory (reported by the native bridge),
* asset files already imported into the open project,
* files the user explicitly attached or passed to a tool,
* folders the user explicitly approved (e.g. ``Downloads``), remembered for
  the session and persisted across restarts.

Only minimal safety checks remain: path normalisation, traversal blocking,
symlink/junction escape blocking, Windows system / credential folder denial,
executable/script denial, and per-operation extension validation.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from synfig_mcp.errors import SecuritySandboxError
from synfig_mcp.logging import get_logger

logger = get_logger("synfig_mcp.security.access")

#: Directory names that hold credentials or private keys; never importable.
DENIED_DIR_NAMES = {
    ".ssh",
    ".aws",
    ".gnupg",
    ".azure",
    ".kube",
    ".docker",
    "credentials",
    "private",
    "privatekeys",
    "private_keys",
    "secret",
    "secrets",
}

#: Executable / script extensions are never imported as assets.
EXECUTABLE_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".com",
    ".scr",
    ".msi",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".bash",
    ".vbs",
    ".vbe",
    ".js",
    ".jse",
    ".wsf",
    ".wsh",
    ".jar",
    ".py",
    ".pyc",
    ".rb",
    ".pl",
}

#: Credential file names that must never be read even with a benign extension.
DENIED_FILE_NAMES = {
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "ntuser.dat",
    "sam",
    "security",
    "system",
}

_APPROVALS_FILE = Path.home() / ".synfig" / "mcp_access.json"


def _norm(path: Path | str) -> str:
    """Canonical string form used as a dictionary key (case-folded on Windows)."""
    text = str(path).replace("\\", "/").rstrip("/")
    if os.name == "nt":
        text = text.casefold()
    return text


def is_overly_broad_root(path: Path | str) -> tuple[bool, str]:
    """Reject roots so broad that approving them would expose the whole machine."""
    candidate = Path(path).expanduser()
    normalized = str(candidate).replace("\\", "/").rstrip("/")
    home = str(Path.home().resolve()).replace("\\", "/").rstrip("/")

    if normalized in {"", "/", home}:
        return True, "filesystem root and user home directories are not allowed"
    if re.fullmatch(r"[A-Za-z]:", normalized):
        return True, "drive roots are not allowed"

    system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    system_normalized = str(Path(system_root).expanduser()).replace("\\", "/").rstrip("/")
    if normalized.casefold() == system_normalized.casefold():
        return True, "system directories are not allowed"

    if normalized.casefold().endswith("/program files") or normalized.casefold().endswith(
        "/program files (x86)"
    ):
        return True, "program directories are not allowed"

    return False, ""


def is_system_path(resolved: Path) -> bool:
    """True when the resolved path lives inside OS / program installation folders."""
    text = _norm(resolved)
    if os.name == "nt":
        prefixes = []
        for env in ("SYSTEMROOT", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            value = os.environ.get(env)
            if value:
                prefixes.append(_norm(Path(value)))
        prefixes.extend(
            _norm(p)
            for p in (
                Path(resolved.anchor) / "Windows",
                Path(resolved.anchor) / "Program Files",
                Path(resolved.anchor) / "Program Files (x86)",
                Path(resolved.anchor) / "$Recycle.Bin",
                Path(resolved.anchor) / "System Volume Information",
            )
        )
        return any(text == p or text.startswith(p + "/") for p in prefixes if p)
    posix_prefixes = (
        "/etc/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/boot/",
        "/proc/",
        "/sys/",
        "/dev/",
        "/var/lib/",
    )
    return any(text.startswith(p) for p in posix_prefixes)


def is_credentials_path(resolved: Path) -> bool:
    """True when any path component is a credential/private-key location."""
    parts = [p.casefold() for p in resolved.parts]
    if any(part in DENIED_DIR_NAMES for part in parts):
        return True
    return resolved.name.casefold() in DENIED_FILE_NAMES and resolved.suffix in {
        "",
        ".pem",
        ".key",
        ".ppk",
    }


def has_link_redirect(path: Path) -> bool:
    """True when the path or any ancestor is a symlink/junction.

    Used to stop user-intent auto-approval from being laundered through a link
    that escapes the folder the user thinks they are addressing.
    """

    def is_link(part: Path) -> bool:
        try:
            # Windows junctions are reparse points, not symlinks.
            return part.is_symlink() or part.is_junction()
        except OSError:
            return True

    try:
        return any(is_link(part) for part in (path, *path.parents))
    except OSError:
        return True


@dataclass
class Approval:
    """One explicitly approved folder."""

    path: str
    reason: str = "user"
    approved_at: float = field(default_factory=time.time)


class AccessController:
    """Session authority for project-aware file access.

    Folder approvals persist in ``~/.synfig/mcp_access.json``; project and
    attachment registrations live for the current server session and are
    refreshed from the live Synfig project.
    """

    def __init__(self, approvals_file: Path | None = None) -> None:
        self._approvals_file = approvals_file or _APPROVALS_FILE
        self._approved: dict[str, Approval] = {}
        self._attachments: set[str] = set()
        self._project_dirs: set[str] = set()
        self._project_assets: set[str] = set()
        self._load()

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        try:
            data = json.loads(self._approvals_file.read_text(encoding="utf-8"))
            for item in data.get("approved_folders", []):
                approval = Approval(
                    path=item["path"],
                    reason=item.get("reason", "user"),
                    approved_at=item.get("approved_at", 0.0),
                )
                self._approved[_norm(approval.path)] = approval
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def _save(self) -> None:
        try:
            self._approvals_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "approved_folders": [
                    {"path": a.path, "reason": a.reason, "approved_at": a.approved_at}
                    for a in self._approved.values()
                ]
            }
            self._approvals_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not persist access approvals", error=str(exc))

    # -- registration ------------------------------------------------------

    def approve_folder(self, path: Path | str, reason: str = "user") -> Path:
        """Approve a folder (e.g. Downloads) for the session and future runs."""
        broad, why = is_overly_broad_root(path)
        if broad:
            raise SecuritySandboxError(f"Cannot approve '{path}': {why}")
        resolved = Path(path).expanduser().resolve()
        if is_system_path(resolved) or is_credentials_path(resolved):
            raise SecuritySandboxError(
                f"Cannot approve '{path}': system and credential folders are never approved"
            )
        self._approved[_norm(resolved)] = Approval(path=str(resolved), reason=reason)
        self._save()
        logger.info("Folder approved for Synfig MCP access", folder=str(resolved), reason=reason)
        return resolved

    def revoke_folder(self, path: Path | str) -> bool:
        key = _norm(Path(path).expanduser().resolve())
        if key in self._approved:
            del self._approved[key]
            self._save()
            return True
        return False

    def register_project(self, project_file: Path | str) -> Path:
        """Register the active project's directory as an access root."""
        resolved = Path(project_file).expanduser().resolve()
        directory = resolved if resolved.is_dir() else resolved.parent
        self._project_dirs.add(_norm(directory))
        return directory

    def register_project_assets(self, paths: list[Path | str]) -> int:
        """Register asset files referenced by the open Synfig project."""
        added = 0
        for raw in paths:
            try:
                resolved = Path(raw).expanduser().resolve()
            except OSError:
                continue
            key = _norm(resolved)
            if key not in self._project_assets:
                self._project_assets.add(key)
                added += 1
        return added

    def register_attachment(self, path: Path | str) -> Path:
        """Register a file the user explicitly attached or passed to a tool."""
        resolved = Path(path).expanduser().resolve()
        self._attachments.add(_norm(resolved))
        return resolved

    # -- decisions ---------------------------------------------------------

    def allowed_roots(self) -> list[Path]:
        """All folder-level roots currently granting access."""
        roots = [Path(a.path) for a in self._approved.values()]
        roots.extend(Path(p) for p in self._project_dirs)
        return roots

    def is_allowed(self, resolved: Path) -> tuple[bool, str]:
        key = _norm(resolved)
        if key in self._attachments:
            return True, "user attachment"
        if key in self._project_assets:
            return True, "project asset"
        for root in self.allowed_roots():
            root_key = _norm(root)
            if key == root_key or key.startswith(root_key + "/"):
                return True, f"approved folder {root}"
        return False, ""

    def status(self) -> dict[str, object]:
        return {
            "approved_folders": [
                {"path": a.path, "reason": a.reason} for a in self._approved.values()
            ],
            "project_directories": sorted(self._project_dirs),
            "project_asset_count": len(self._project_assets),
            "attachment_count": len(self._attachments),
            "policy": "project-aware (active project, attachments, explicit approvals)",
        }


_controller: AccessController | None = None


def get_access_controller() -> AccessController:
    global _controller
    if _controller is None:
        _controller = AccessController()
    return _controller


def reset_access_controller() -> None:
    """Test hook: drop the session singleton (persisted approvals are reloaded)."""
    global _controller
    _controller = None


def get_staging_root() -> Path:
    """Directory for derived assets (slices, thumbnails, previews).

    Prefers the active project so derived files stay with the production;
    falls back to the configured workspace root.
    """
    controller = get_access_controller()
    if controller._project_dirs:
        first = sorted(controller._project_dirs)[0]
        return Path(first)
    from synfig_mcp.config import settings

    return settings.workspace_roots[0]


def get_temp_root() -> Path:
    return Path(tempfile.gettempdir()).resolve()


def collect_asset_paths(tree: dict[str, object]) -> list[str]:
    """Extract imported asset file paths from a scene tree dictionary.

    Walks the nested layer structure produced by both backends and collects
    every ``filename`` string parameter (import / sound layers).
    """
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            params = node.get("params")
            if isinstance(params, dict):
                filename = params.get("filename")
                value = filename.get("value") if isinstance(filename, dict) else filename
                if isinstance(value, str) and value and "://" not in value:
                    found.append(value)
            for child in node.get("children", []) or []:
                walk(child)
            for layer in node.get("layers", []) or []:
                walk(layer)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(tree)
    return found
