"""Unit tests for configuration."""

from synfig_mcp.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.backend_mode == "auto"
    assert settings.bridge_host == "127.0.0.1"
    assert settings.bridge_port == 19998
    assert len(settings.workspace_roots) >= 1
