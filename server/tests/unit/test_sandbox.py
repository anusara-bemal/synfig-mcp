"""
Unit tests for filesystem security sandbox:
- Directory traversal (..) and symlink escapes
- Extension restrictions (.sif/.sifz/.sfg for docs, .png/.mp4 for renders)
- LiveBackend and HeadlessBackend enforcement
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.errors import SecuritySandboxError
from synfig_mcp.security.sandbox import validate_path


def test_sandbox_allows_path_inside_root(tmp_path: Path) -> None:
    safe_file = tmp_path / "project.sif"
    safe_file.write_text("content", encoding="utf-8")

    result = validate_path(safe_file, [tmp_path])
    assert result == safe_file.resolve()


def test_sandbox_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    with pytest.raises(SecuritySandboxError, match="denied by the workspace permission model"):
        validate_path(outside_file, [root])


def test_sandbox_rejects_dotdot_traversal(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    traversal_path = root / ".." / "secret.sif"

    with pytest.raises(SecuritySandboxError, match="denied by the workspace permission model"):
        validate_path(traversal_path, [root])


def test_sandbox_rejects_forbidden_extension(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    malicious_script = root / "exploit.exe"

    with pytest.raises(SecuritySandboxError, match="extension .* is not permitted"):
        validate_path(
            malicious_script,
            allowed_roots=[root],
            allowed_extensions={".sif", ".sifz", ".sfg"},
        )


@pytest.mark.asyncio
async def test_live_backend_rejects_escapes(tmp_path: Path) -> None:
    workspace = tmp_path / "sandbox_ws"
    workspace.mkdir()

    mock_client = AsyncMock()
    backend = LiveBackend(client=mock_client)

    outside = tmp_path / "outside.sif"

    # Enforce custom allowed roots
    from unittest.mock import patch

    with patch(
        "synfig_mcp.security.sandbox.get_default_allowed_roots",
        return_value=[workspace],
    ):
        # 1. doc_open outside
        with pytest.raises(SecuritySandboxError):
            await backend.doc_open(str(outside))

        # 2. doc_open invalid extension
        bad_ext = workspace / "bad.sh"
        bad_ext.write_text("echo hello")
        with pytest.raises(SecuritySandboxError):
            await backend.doc_open(str(bad_ext))

        # 3. doc_save outside
        with pytest.raises(SecuritySandboxError):
            await backend.doc_save("doc_0", file_path=str(outside))

        # 4. render_frame outside
        with pytest.raises(SecuritySandboxError):
            await backend.render_frame("doc_0", output_path=str(outside))

        # 5. render_frame bad extension
        with pytest.raises(SecuritySandboxError):
            await backend.render_frame("doc_0", output_path=str(workspace / "out.exe"))

        # 6. render_sequence outside
        with pytest.raises(SecuritySandboxError):
            await backend.render_sequence("doc_0", output_dir=str(tmp_path / "outside_dir"))

        # 7. render_video outside
        with pytest.raises(SecuritySandboxError):
            await backend.render_video("doc_0", output_path=str(outside))

        # 8. render_contact_sheet outside
        with pytest.raises(SecuritySandboxError):
            await backend.render_contact_sheet("doc_0", output_path=str(outside))

    # Assert bridge client was never called for any escape attempt!
    assert mock_client.call.call_count == 0


@pytest.mark.asyncio
async def test_headless_backend_rejects_escapes(tmp_path: Path) -> None:
    workspace = tmp_path / "sandbox_ws"
    workspace.mkdir()

    backend = HeadlessBackend()
    outside = tmp_path / "outside.sif"

    from unittest.mock import patch

    with patch(
        "synfig_mcp.security.sandbox.get_default_allowed_roots",
        return_value=[workspace],
    ):
        with pytest.raises(SecuritySandboxError):
            await backend.doc_open(str(outside))

        doc = await backend.doc_new()

        with pytest.raises(SecuritySandboxError):
            await backend.doc_save(doc.id, file_path=str(outside))

        with pytest.raises(SecuritySandboxError):
            await backend.render_frame(doc.id, output_path=str(outside))


def test_sandbox_rejects_junction_escape(tmp_path: Path) -> None:
    import os
    import subprocess

    root = tmp_path / "workspace"
    root.mkdir()
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    outside_file = outside_dir / "target.sif"
    outside_file.write_text("secret", encoding="utf-8")

    junction_path = root / "junction_to_outside"
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction_path), str(outside_dir)], check=True
        )
    else:
        os.symlink(str(outside_dir), str(junction_path))

    path_through_junction = junction_path / "target.sif"
    with pytest.raises(SecuritySandboxError, match="denied by the workspace permission model"):
        validate_path(path_through_junction, [root])

    # Write target through junction
    write_target = junction_path / "payload.png"
    with pytest.raises(SecuritySandboxError, match="denied by the workspace permission model"):
        validate_path(write_target, [root], allowed_extensions={".png"})
