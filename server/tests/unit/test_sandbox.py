"""
Unit tests for project-aware file access (replaces the old workspace jail):
- user-supplied paths are authorised directly (the Downloads fix)
- approved folders, project directories and project assets grant access
- minimal safety checks remain: traversal, symlink/junction escapes, system
  folders, credential folders, executables, extension allow-lists
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.errors import SecuritySandboxError
from synfig_mcp.security import access as access_mod
from synfig_mcp.security.access import AccessController
from synfig_mcp.security.sandbox import validate_path


@pytest.fixture(autouse=True)
def isolated_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Fresh access controller per test; approvals never touch the real home."""
    controller = AccessController(approvals_file=tmp_path / "approvals.json")
    monkeypatch.setattr(access_mod, "_controller", controller)
    # Keep pytest's own temp tree from counting as the always-allowed temp root.
    monkeypatch.setattr(
        "synfig_mcp.security.sandbox.get_temp_root", lambda: tmp_path / "temp_root"
    )
    yield controller
    access_mod.reset_access_controller()


def test_explicit_roots_still_enforced(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    inside = root / "project.sif"
    inside.write_text("content", encoding="utf-8")
    assert validate_path(inside, [root]) == inside.resolve()

    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(SecuritySandboxError, match="outside the explicitly requested roots"):
        validate_path(outside, [root])


def test_user_intent_authorises_downloads_style_file(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    sheet = downloads / "rig_sheet.png"
    sheet.write_bytes(b"\x89PNG\r\n\x1a\n")

    # No approval, no project: a file the user passes directly is authorised.
    result = validate_path(sheet, must_exist=True, user_intent=True)
    assert result == sheet.resolve()

    # Without user intent the same file is not authorised yet.
    access_mod.reset_access_controller()
    controller = AccessController(approvals_file=tmp_path / "approvals2.json")
    access_mod._controller = controller
    with pytest.raises(SecuritySandboxError, match="access_approve"):
        validate_path(sheet, must_exist=True)


def test_approved_folder_grants_access_and_persists(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    asset = downloads / "background.png"
    asset.write_bytes(b"\x89PNG\r\n\x1a\n")

    controller = access_mod.get_access_controller()
    controller.approve_folder(downloads)
    assert validate_path(asset, must_exist=True) == asset.resolve()

    # A new controller (server restart) reloads the persisted approval.
    reloaded = AccessController(approvals_file=tmp_path / "approvals.json")
    allowed, reason = reloaded.is_allowed(asset.resolve())
    assert allowed
    assert "approved folder" in reason

    assert controller.revoke_folder(downloads) is True
    with pytest.raises(SecuritySandboxError):
        validate_path(asset, must_exist=True)


def test_project_directory_and_assets_authorise(tmp_path: Path) -> None:
    project = tmp_path / "my_film"
    project.mkdir()
    assets = project / "assets"
    assets.mkdir()
    doc = project / "film.sifz"
    doc.write_text("<canvas/>", encoding="utf-8")
    img = assets / "prop.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    elsewhere = tmp_path / "elsewhere" / "other.png"
    elsewhere.parent.mkdir()
    elsewhere.write_bytes(b"\x89PNG\r\n\x1a\n")

    controller = access_mod.get_access_controller()
    controller.register_project(doc)
    controller.register_project_assets([img])

    assert validate_path(img, must_exist=True) == img.resolve()
    sibling = project / "new_layer.png"
    assert validate_path(sibling) == sibling.resolve()
    with pytest.raises(SecuritySandboxError):
        validate_path(elsewhere, must_exist=True)


def test_traversal_blocked(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    with pytest.raises(SecuritySandboxError, match="traversal"):
        validate_path(root / ".." / "secret.sif", [root])
    with pytest.raises(SecuritySandboxError, match="traversal"):
        validate_path(root / ".." / "secret.sif", user_intent=True)


def test_extension_allowlist(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    script = root / "exploit.exe"
    with pytest.raises(SecuritySandboxError, match="extension .* is not permitted"):
        validate_path(script, allowed_roots=[root], allowed_extensions={".sif", ".sifz"})


def test_executable_denied_even_with_user_intent(tmp_path: Path) -> None:
    payload = tmp_path / "Downloads" / "tool.exe"
    payload.parent.mkdir()
    with pytest.raises(SecuritySandboxError, match="executable"):
        validate_path(payload, user_intent=True)


def test_system_and_credential_paths_denied(tmp_path: Path) -> None:
    if os.name == "nt":
        system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "notepad.exe"
        with pytest.raises(SecuritySandboxError):
            validate_path(system, user_intent=True)
    creds = tmp_path / ".ssh" / "id_rsa"
    with pytest.raises(SecuritySandboxError, match="credential"):
        validate_path(creds, user_intent=True)


def test_overly_broad_roots_rejected(tmp_path: Path) -> None:
    controller = access_mod.get_access_controller()
    with pytest.raises(SecuritySandboxError):
        controller.approve_folder(Path.home())
    if os.name == "nt":
        with pytest.raises(SecuritySandboxError):
            controller.approve_folder("C:\\")
        with pytest.raises(SecuritySandboxError):
            controller.approve_folder(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    with pytest.raises(SecuritySandboxError):
        controller.approve_folder("/")


def test_junction_escape_blocked(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    (outside_dir / "target.sif").write_text("secret", encoding="utf-8")

    junction = root / "junction_to_outside"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside_dir)], check=True)
    else:
        os.symlink(str(outside_dir), str(junction))

    # Explicit roots: the resolved target is outside them.
    with pytest.raises(SecuritySandboxError):
        validate_path(junction / "target.sif", [root])
    # User intent must not be laundered through a link redirect either.
    with pytest.raises(SecuritySandboxError):
        validate_path(junction / "target.sif", user_intent=True)


@pytest.mark.asyncio
async def test_live_backend_user_path_reaches_bridge(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    doc_file = downloads / "open_me.sif"
    doc_file.write_text("<canvas/>", encoding="utf-8")

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.call.return_value = {
        "doc_id": "doc_0",
        "id": "doc_0",
        "name": "Open Me",
        "file_path": str(doc_file),
        "width": 1920,
        "height": 1080,
        "fps": 24.0,
        "start_time": 0.0,
        "end_time": 5.0,
        "duration_frames": 120,
        "project_dir": str(downloads),
        "assets": [],
    }
    backend = LiveBackend(client=mock_client)

    info = await backend.doc_open(str(doc_file))
    assert info.id == "doc_0"
    assert mock_client.call.await_count >= 1
    assert mock_client.call.await_args_list[0].args[0] == "doc.open"

    # The open project now authorises its directory without any approval.
    controller = access_mod.get_access_controller()
    allowed, _ = controller.is_allowed((downloads / "another.png").resolve())
    assert allowed


@pytest.mark.asyncio
async def test_live_backend_unsafe_paths_never_reach_bridge(tmp_path: Path) -> None:
    mock_client = AsyncMock()
    mock_client.is_connected = True
    backend = LiveBackend(client=mock_client)

    with pytest.raises(SecuritySandboxError):
        await backend.doc_open(str(tmp_path / ".." / "escape.sif"))
    with pytest.raises(SecuritySandboxError):
        await backend.doc_open(str(tmp_path / "bad.sh"))
    with pytest.raises(SecuritySandboxError):
        await backend.render_frame("doc_0", output_path=str(tmp_path / "out.exe"))
    assert mock_client.call.call_count == 0


@pytest.mark.asyncio
async def test_headless_backend_user_path_and_safety(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    doc_file = downloads / "scene.sif"
    doc_file.write_text(
        '<?xml version="1.0"?><canvas version="1.0" width="480" height="270"></canvas>',
        encoding="utf-8",
    )

    info = await backend.doc_open(str(doc_file))
    assert info.file_path == str(doc_file.resolve())

    with pytest.raises(SecuritySandboxError):
        await backend.doc_open(str(tmp_path / ".." / "escape.sif"))

    doc = await backend.doc_new()
    with pytest.raises(SecuritySandboxError):
        await backend.render_frame(doc.id, output_path=str(tmp_path / "out.exe"))