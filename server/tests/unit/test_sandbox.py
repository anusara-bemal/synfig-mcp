"""Unit tests for filesystem security sandbox."""

from pathlib import Path

import pytest

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

    with pytest.raises(SecuritySandboxError):
        validate_path(outside_file, [root])
