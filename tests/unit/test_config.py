# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for environment/TOML configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from synfig_mcp.config import Settings, load_settings


class TestDefaults:
    def test_defaults(self, tmp_path: Path) -> None:
        settings = load_settings({}, start_dir=tmp_path)
        assert settings.workspace == tmp_path.resolve()
        assert settings.synfig_bin is None
        assert settings.render_timeout == 300.0
        assert settings.max_frames == 20000
        assert settings.max_resolution == 8192
        assert settings.max_layers == 5000
        assert settings.max_file_mb == 256
        assert settings.unit_px == 60.0
        assert settings.unit_system == "units"
        assert settings.history_depth == 50
        assert settings.render_workers == 2
        assert settings.autosave is False
        assert settings.max_file_bytes == 256 * 1024 * 1024

    def test_frozen(self, tmp_path: Path) -> None:
        settings = load_settings({}, start_dir=tmp_path)
        with pytest.raises(AttributeError):
            settings.max_frames = 1  # type: ignore[misc]


class TestEnv:
    def test_env_values(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        env = {
            "SYNFIG_MCP_WORKSPACE": str(workspace),
            "SYNFIG_BIN": " /usr/bin/synfig ",
            "SYNFIG_MCP_LOG_LEVEL": "debug",
            "SYNFIG_MCP_RENDER_TIMEOUT": "12.5",
            "SYNFIG_MCP_MAX_FRAMES": "100",
            "SYNFIG_MCP_MAX_RESOLUTION": "1920",
            "SYNFIG_MCP_MAX_LAYERS": "50",
            "SYNFIG_MCP_MAX_FILE_MB": "8",
            "SYNFIG_MCP_UNIT_PX": "100",
            "SYNFIG_MCP_UNIT_SYSTEM": "PIXELS",
            "SYNFIG_MCP_HISTORY_DEPTH": "5",
            "SYNFIG_MCP_RENDER_WORKERS": "4",
            "SYNFIG_MCP_AUTOSAVE": "yes",
        }
        settings = load_settings(env)
        assert settings.workspace == workspace.resolve()
        assert settings.synfig_bin == "/usr/bin/synfig"
        assert settings.log_level == "DEBUG"
        assert settings.render_timeout == 12.5
        assert settings.max_frames == 100
        assert settings.max_resolution == 1920
        assert settings.max_layers == 50
        assert settings.max_file_mb == 8
        assert settings.unit_px == 100
        assert settings.unit_system == "pixels"
        assert settings.history_depth == 5
        assert settings.render_workers == 4
        assert settings.autosave is True

    def test_invalid_values_fall_back(self, tmp_path: Path) -> None:
        env = {
            "SYNFIG_MCP_WORKSPACE": str(tmp_path),
            "SYNFIG_MCP_RENDER_TIMEOUT": "nope",
            "SYNFIG_MCP_MAX_FRAMES": "nope",
            "SYNFIG_MCP_UNIT_PX": "0",
            "SYNFIG_MCP_HISTORY_DEPTH": "-5",
            "SYNFIG_MCP_RENDER_WORKERS": "0",
            "SYNFIG_MCP_UNIT_SYSTEM": "furlongs",
        }
        settings = load_settings(env)
        assert settings.render_timeout == 300.0
        assert settings.max_frames == 20000
        assert settings.unit_px == 1.0
        assert settings.history_depth == 1
        assert settings.render_workers == 1
        assert settings.unit_system == "units"

    def test_empty_bin(self, tmp_path: Path) -> None:
        settings = load_settings({"SYNFIG_BIN": "  ", "SYNFIG_MCP_WORKSPACE": str(tmp_path)})
        assert settings.synfig_bin is None


class TestToml:
    def test_toml_used(self, tmp_path: Path) -> None:
        (tmp_path / "synfig-mcp.toml").write_text(
            'max_frames = 42\nunit_px = 30\nunit_system = "pixels"\nrender_workers = 3\n'
        )
        settings = load_settings({}, start_dir=tmp_path)
        assert settings.max_frames == 42
        assert settings.unit_px == 30
        assert settings.unit_system == "pixels"
        assert settings.render_workers == 3

    def test_env_wins(self, tmp_path: Path) -> None:
        (tmp_path / "synfig-mcp.toml").write_text("max_frames = 42\n")
        settings = load_settings({"SYNFIG_MCP_MAX_FRAMES": "7"}, start_dir=tmp_path)
        assert settings.max_frames == 7

    def test_broken_toml_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "synfig-mcp.toml").write_text("this is not toml [[[")
        settings = load_settings({}, start_dir=tmp_path)
        assert settings.max_frames == 20000

    def test_toml_path_property(self, tmp_path: Path) -> None:
        settings = Settings(workspace=tmp_path)
        assert settings.toml_path == tmp_path / "synfig-mcp.toml"
