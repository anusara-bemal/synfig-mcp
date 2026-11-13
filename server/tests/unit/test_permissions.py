"""
Unit tests for the runtime user-granted permission model.

Covers granting/revoking roots, read-only grants, overly-broad rejection,
Unicode/relative paths and the atomic write helper.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from synfig_mcp.errors import SecurityError, SecuritySandboxError
from synfig_mcp.security.permissions import PermissionStore
from synfig_mcp.security.sandbox import safe_write_bytes, validate_path


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> PermissionStore:
    fresh = PermissionStore()
    fresh.clear()
    monkeypatch.setattr("synfig_mcp.security.permissions.permissions", fresh)
    # Make the store the sole source of allowed roots (no implicit temp dir), so
    # a path under tmp_path is denied unless it was explicitly granted.
    monkeypatch.setattr(
        "synfig_mcp.security.sandbox.get_default_allowed_roots",
        lambda: [g.path for g in fresh.grants()],
    )
    return fresh


def test_grant_and_validate(store: PermissionStore, tmp_path: Path) -> None:
    target = tmp_path / "project" / "scene.sif"
    target.parent.mkdir()
    target.write_text("x", encoding="utf-8")

    store.grant(tmp_path)
    assert validate_path(target) == target.resolve()


def test_ungranted_path_is_rejected(store: PermissionStore, tmp_path: Path) -> None:  # noqa: ARG001
    other = tmp_path / "other"
    other.mkdir()
    (other / "secret.sif").write_text("s", encoding="utf-8")

    with pytest.raises(SecuritySandboxError, match="denied by the workspace permission model"):
        validate_path(other / "secret.sif")


def test_read_only_grant_blocks_write(store: PermissionStore, tmp_path: Path) -> None:
    store.grant(tmp_path, read=True, write=False)
    with pytest.raises(SecuritySandboxError, match="read-only"):
        validate_path(tmp_path / "new.sif", for_write=True)


def test_write_grant_allows_write(store: PermissionStore, tmp_path: Path) -> None:
    store.grant(tmp_path, read=True, write=True)
    assert validate_path(tmp_path / "new.sif", for_write=True) == (tmp_path / "new.sif").resolve()


def test_relative_path_is_resolved_against_cwd(
    store: PermissionStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "rel.sif").write_text("x", encoding="utf-8")
    store.grant(tmp_path)
    assert validate_path(Path("rel.sif")) == (tmp_path / "rel.sif").resolve()


def test_unicode_directory_is_supported(store: PermissionStore, tmp_path: Path) -> None:
    uni = tmp_path / "作品" / "シーン"
    uni.mkdir(parents=True)
    target = uni / "シーン.sif"
    target.write_text("x", encoding="utf-8")
    store.grant(tmp_path)
    assert validate_path(target) == target.resolve()


def test_grant_nonexistent_path_is_rejected(store: PermissionStore, tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="does not exist"):
        store.grant(tmp_path / "does_not_exist")


def test_grant_of_file_uses_parent(store: PermissionStore, tmp_path: Path) -> None:
    f = tmp_path / "file.sif"
    f.write_text("x", encoding="utf-8")
    grant = store.grant(f)
    assert grant.path == tmp_path.resolve()


def test_revoke_removes_grant(store: PermissionStore, tmp_path: Path) -> None:
    store.grant(tmp_path)
    assert store.revoke(tmp_path) is True
    assert store.revoke(tmp_path) is False


def test_safe_write_bytes_is_atomic_and_backs_up(tmp_path: Path) -> None:
    target = tmp_path / "doc.sif"
    target.write_text("old", encoding="utf-8")

    safe_write_bytes(target, b"new")

    assert target.read_bytes() == b"new"
    assert (tmp_path / "doc.sif.bak").read_text(encoding="utf-8") == "old"
    # No leftover temp files
    assert not list(tmp_path.glob(".doc.sif.*"))


def test_safe_write_bytes_creates_parents(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "doc.sif"
    safe_write_bytes(target, b"data", backup=False)
    assert target.read_bytes() == b"data"
