"""Unit tests for configuration."""

import os
from pathlib import Path
from unittest.mock import patch

from synfig_mcp.config import Settings, get_default_workspace_roots


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.backend_mode == "auto"
    assert settings.bridge_host == "127.0.0.1"
    assert settings.bridge_port == 19998
    assert len(settings.workspace_roots) >= 1
    # Check that dedicated project root is always present
    doc_root = (Path.home() / "Documents" / "SynfigMCP").resolve()
    assert doc_root in settings.workspace_roots


def test_broad_cwd_rejected_in_default_roots() -> None:
    # 1. cwd is user home
    with patch("pathlib.Path.cwd", return_value=Path.home().resolve()):
        roots = get_default_workspace_roots()
        assert Path.home().resolve() not in roots
        assert (Path.home() / "Documents" / "SynfigMCP").resolve() in roots

    # 2. cwd is Windows system dir or root
    sys_dir = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")).resolve()
    with patch("pathlib.Path.cwd", return_value=sys_dir):
        roots = get_default_workspace_roots()
        assert sys_dir not in roots
        assert (Path.home() / "Documents" / "SynfigMCP").resolve() in roots

    # 3. cwd is drive root
    drive_root = Path(Path.cwd().anchor).resolve()
    with patch("pathlib.Path.cwd", return_value=drive_root):
        roots = get_default_workspace_roots()
        assert drive_root not in roots
        assert (Path.home() / "Documents" / "SynfigMCP").resolve() in roots


def test_env_workspace_roots_override() -> None:
    dummy1 = (Path.home() / "Documents" / "Project1").resolve()
    dummy2 = (Path.home() / "Documents" / "Project2").resolve()
    with patch.dict(os.environ, {"SYNFIG_MCP_WORKSPACE_ROOTS": f"{dummy1}{os.pathsep}{dummy2}"}):
        roots = get_default_workspace_roots()
        assert roots == [dummy1, dummy2]
