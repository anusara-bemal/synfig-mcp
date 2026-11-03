# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for the exception hierarchy."""

from __future__ import annotations

from synfig_mcp.errors import (
    ConfigError,
    DocumentNotFoundError,
    InvalidProjectError,
    LayerNotFoundError,
    SynfigMCPError,
    SynfigNotFoundError,
    UnknownLayerTypeError,
    WorkspaceError,
)


class TestBase:
    def test_to_dict(self) -> None:
        exc = SynfigMCPError("boom", hint="try again", context={"x": 1})
        assert exc.to_dict() == {
            "error": "synfig_mcp_error",
            "message": "boom",
            "hint": "try again",
            "context": {"x": 1},
        }
        assert str(exc) == "synfig_mcp_error: boom (hint: try again)"

    def test_minimal(self) -> None:
        exc = ConfigError("bad")
        assert exc.to_dict() == {"error": "config_error", "message": "bad"}
        assert str(exc) == "config_error: bad"

    def test_codes(self) -> None:
        assert WorkspaceError("x").code == "workspace_error"
        assert InvalidProjectError("x").code == "invalid_project"


class TestSpecialised:
    def test_document_not_found(self) -> None:
        exc = DocumentNotFoundError("abc", known=["1", "2"])
        assert exc.code == "project_not_found"
        assert "1, 2" in (exc.hint or "")
        assert exc.context == {"project_id": "abc"}

    def test_document_not_found_no_known(self) -> None:
        assert "open_project" in (DocumentNotFoundError("x").hint or "")

    def test_layer_not_found(self) -> None:
        exc = LayerNotFoundError("Ball", suggestions=["Balls"])
        assert exc.code == "layer_not_found"
        assert "Balls" in (exc.hint or "")
        assert LayerNotFoundError("x").hint is None

    def test_unknown_layer_type(self) -> None:
        exc = UnknownLayerTypeError("circl", ["circle", "rectangle"])
        assert exc.code == "unknown_layer_type"
        assert "circle" in (exc.hint or "")
        assert "list_layer_types" in (UnknownLayerTypeError("zzzz", ["circle"]).hint or "")

    def test_synfig_not_found(self) -> None:
        exc = SynfigNotFoundError()
        assert exc.code == "synfig_binary_not_found"
        assert "SYNFIG_BIN" in (exc.hint or "")
