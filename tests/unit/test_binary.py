# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for binary discovery and output parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from synfig_mcp.cli import binary as b


class TestFind:
    def test_env_existing(self, tmp_path: Path) -> None:
        exe = tmp_path / "synfig"
        exe.write_text("")
        assert b.find_synfig_binary(str(exe)) == str(exe)

    def test_env_missing(self, tmp_path: Path) -> None:
        assert b.find_synfig_binary(str(tmp_path / "nope")) == str(tmp_path / "nope")

    def test_path_lookup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            b.shutil, "which", lambda name: "/usr/bin/synfig" if name == "synfig" else None
        )
        assert b.find_synfig_binary(None) == "/usr/bin/synfig"

    def test_windows_exe_lookup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(b.platform, "system", lambda: "Windows")
        monkeypatch.setattr(
            b.shutil, "which", lambda name: "C:/synfig.exe" if name == "synfig.exe" else None
        )
        assert b.find_synfig_binary(None) == "C:/synfig.exe"

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        fake = tmp_path / "synfig"
        fake.write_text("")
        monkeypatch.setattr(b.shutil, "which", lambda name: None)
        monkeypatch.setattr(b.platform, "system", lambda: "Linux")
        monkeypatch.setattr(b, "LINUX_DEFAULTS", [str(fake)])
        assert b.find_synfig_binary(None) == str(fake)

    def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(b.shutil, "which", lambda name: None)
        monkeypatch.setattr(b.platform, "system", lambda: "Linux")
        monkeypatch.setattr(b, "LINUX_DEFAULTS", [])
        assert b.find_synfig_binary(None) is None

    @pytest.mark.parametrize(
        ("system", "expected"),
        [
            ("Windows", b.WINDOWS_DEFAULTS),
            ("Darwin", b.MACOS_DEFAULTS),
            ("Linux", b.LINUX_DEFAULTS),
        ],
    )
    def test_default_candidates(
        self, monkeypatch: pytest.MonkeyPatch, system: str, expected: list[str]
    ) -> None:
        monkeypatch.setattr(b.platform, "system", lambda: system)
        assert b.default_candidates() == expected


class TestClean:
    def test_strips_noise_and_ansi(self) -> None:
        text = (
            "synfig(1234) [12:00:00] info: Loading modules\n"
            "\x1b[31mwarning: something\x1b[0m\n"
            "Unable to find module mod_x\n"
            "png\n"
            "\n"
            "gif\n"
        )
        assert b.clean_synfig_output(text) == ["png", "gif"]

    def test_parse_version(self) -> None:
        assert b.parse_version("synfig 1.5.5") == "synfig 1.5.5"
        assert b.parse_version("SynfigStudio 1.4.2-beta") == "synfig 1.4.2-beta"
        assert b.parse_version("nothing") is None


class TestProbe:
    def test_missing_binary(self, tmp_path: Path) -> None:
        result = b.probe_synfig(str(tmp_path / "missing"))
        assert result["found"] is False
        assert result["problems"]

    def test_probe(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        exe = tmp_path / "synfig"
        exe.write_text("")

        def fake(binary: str, args: list[str], *, timeout: float = 30.0) -> tuple[int, str, str]:
            if args == ["--version"]:
                return 3, "synfig 1.5.5", ""
            if args == ["--targets"]:
                return 0, "png\ngif\n", ""
            if args == ["--renderers"]:
                return 0, "cairo\n", ""
            if args == ["--layers"]:
                return 0, "circle\n", ""
            return 0, "valuenode\n", ""

        monkeypatch.setattr(b, "raw_command", fake)
        result = b.probe_synfig(str(exe))
        assert result["found"] is True
        assert result["version"] == "synfig 1.5.5"
        assert result["targets"] == ["png", "gif"]
        assert result["renderers"] == ["cairo"]
        assert result["layers"] == ["circle"]
        assert result["problems"] == []

    def test_probe_broken(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        exe = tmp_path / "synfig"
        exe.write_text("")
        monkeypatch.setattr(b, "raw_command", lambda *a, **k: (1, "", "boom"))
        result = b.probe_synfig(str(exe))
        assert result["found"] is True
        assert len(result["problems"]) == 3

    def test_raw_command_oserror(self) -> None:
        rc, _out, err = b.raw_command("definitely-not-a-real-binary-xyz", ["--version"])
        assert rc == -1
        assert err


class TestHelpers:
    def test_supports_flag(self) -> None:
        assert b.supports_flag("usage: synfig --time", "--time")
        assert not b.supports_flag("usage", "--time")

    def test_renderers_available(self) -> None:
        assert b.renderers_available({"renderers": ["cairo"]}, "cairo")
        assert not b.renderers_available({"renderers": []}, "cairo")

    def test_flatpak_hint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(b.platform, "system", lambda: "Linux")
        monkeypatch.setattr(b.shutil, "which", lambda name: "/usr/bin/flatpak")
        hint = b._flatpak_hint()
        assert hint is not None and b.FLATPAK_APP_ID in hint

    def test_flatpak_hint_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(b.platform, "system", lambda: "Windows")
        assert b._flatpak_hint() is None
