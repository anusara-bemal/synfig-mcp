"""
Unit tests for synfig_mcp.doctor system diagnostics.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from synfig_mcp.doctor import (
    check_config,
    check_ffmpeg,
    check_studio_binary,
    check_synfig_cli,
    check_token_file,
    run_doctor,
)


def test_check_studio_binary_found(tmp_path: Path) -> None:
    fake_bin = tmp_path / "synfigstudio.exe"
    fake_bin.write_text("dummy", encoding="utf-8")

    with patch.dict(os.environ, {"SYNFIG_STUDIO_PATH": str(fake_bin)}):
        res = check_studio_binary()
        assert res.status == "PASS"
        assert str(fake_bin) in res.message


def test_check_studio_binary_missing() -> None:
    with (
        patch.dict(os.environ, {"SYNFIG_STUDIO_PATH": "/nonexistent/path/synfigstudio"}),
        patch("shutil.which", return_value=None),
        patch.object(Path, "is_file", return_value=False),
    ):
        res = check_studio_binary()
        assert res.status == "WARN"
        assert "not found" in res.message


def test_check_synfig_cli() -> None:
    with patch("shutil.which", return_value="/bin/synfig"):
        res = check_synfig_cli()
        assert res.status == "PASS"

    with (
        patch("shutil.which", return_value=None),
        patch.object(Path, "is_file", return_value=False),
    ):
        res = check_synfig_cli()
        assert res.status == "WARN"


def test_check_ffmpeg() -> None:
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        res = check_ffmpeg()
        assert res.status == "PASS"

    with patch("shutil.which", return_value=None):
        res = check_ffmpeg()
        assert res.status == "WARN"


def test_check_token_file(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}):
        # File does not exist
        res = check_token_file()
        assert res.status == "INFO"

        token_dir = tmp_path / ".synfig"
        token_dir.mkdir(parents=True)
        token_file = token_dir / "mcp_token"
        token_file.write_text("test_token", encoding="utf-8")

        # Mock ACL check
        if os.name == "nt":
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "NT AUTHORITY\\SYSTEM:(F)\nUser:(F)"
                res = check_token_file()
                assert res.status == "PASS"
        else:
            token_file.chmod(0o600)
            res = check_token_file()
            assert res.status == "PASS"


def test_check_config() -> None:
    with patch.dict(os.environ, {"SYNFIG_MCP_BACKEND": "auto", "SYNFIG_MCP_PORT": "19991"}):
        res = check_config()
        assert res.status == "PASS"

    with patch.dict(os.environ, {"SYNFIG_MCP_BACKEND": "invalid_backend"}):
        res = check_config()
        assert res.status == "FAIL"

    with patch.dict(os.environ, {"SYNFIG_MCP_BACKEND": "auto", "SYNFIG_MCP_PORT": "99999"}):
        res = check_config()
        assert res.status == "FAIL"


def test_run_doctor_exit_code() -> None:
    with patch("synfig_mcp.doctor.check_config") as mock_check:
        from synfig_mcp.doctor import CheckResult

        mock_check.return_value = CheckResult(name="Test", status="PASS", message="ok")
        code = run_doctor()
        assert code in (0, 1)
