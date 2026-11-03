# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Custom exception hierarchy for synfig-mcp.

Every tool converts these into MCP tool errors with actionable messages.
Raw tracebacks never leave the server boundary.
"""

from __future__ import annotations

import difflib
from typing import Any


class SynfigMCPError(Exception):
    """Base class for all expected, user-facing errors."""

    code = "synfig_mcp_error"

    def __init__(
        self, message: str, *, hint: str | None = None, context: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.hint:
            payload["hint"] = self.hint
        if self.context:
            payload["context"] = self.context
        return payload

    def __str__(self) -> str:  # for logs/tests
        base = f"{self.code}: {self.message}"
        return f"{base} (hint: {self.hint})" if self.hint else base


class ConfigError(SynfigMCPError):
    code = "config_error"


class SecurityError(SynfigMCPError):
    """Path outside the configured workspace, or another policy violation."""

    code = "security_error"


class WorkspaceError(SecurityError):
    code = "workspace_error"


class LimitExceededError(SynfigMCPError):
    """A configurable resource cap was hit (resolution, frames, layers, size...)."""

    code = "limit_exceeded"


class DocumentError(SynfigMCPError):
    code = "document_error"


class DocumentNotFoundError(DocumentError):
    code = "project_not_found"

    def __init__(self, project_id: str, known: list[str] | None = None) -> None:
        hint = (
            f"Known project ids: {', '.join(known)}"
            if known
            else ("Open a project first with open_project or create_project.")
        )
        super().__init__(
            f"No open project with id {project_id!r}.",
            hint=hint,
            context={"project_id": project_id},
        )


class UnsupportedFormatError(DocumentError):
    code = "unsupported_format"


class InvalidProjectError(DocumentError):
    code = "invalid_project"


class LayerNotFoundError(SynfigMCPError):
    code = "layer_not_found"

    def __init__(self, layer_ref: str | int, suggestions: list[str] | None = None) -> None:
        hint = None
        if suggestions:
            hint = f"Did you mean: {', '.join(suggestions)}?"
        super().__init__(
            f"Layer {layer_ref!r} not found or not a layer index/name.",
            hint=hint,
            context={"layer_ref": layer_ref},
        )


class UnknownLayerTypeError(SynfigMCPError):
    code = "unknown_layer_type"

    def __init__(self, layer_type: str, known: list[str]) -> None:
        close = difflib.get_close_matches(layer_type, known, n=3, cutoff=0.45)
        hint = (
            f"Did you mean: {', '.join(close)}?"
            if close
            else ("Run list_layer_types to see all types available in this synfig build.")
        )
        super().__init__(
            f"Unknown synfig layer type {layer_type!r}.",
            hint=hint,
            context={"layer_type": layer_type},
        )


class ParameterError(SynfigMCPError):
    code = "parameter_error"


class KeyframeNotFoundError(SynfigMCPError):
    code = "keyframe_not_found"


class WaypointError(SynfigMCPError):
    code = "waypoint_error"


class ExportError(SynfigMCPError):
    code = "export_error"


class SynfigNotFoundError(SynfigMCPError):
    code = "synfig_binary_not_found"

    def __init__(self) -> None:
        super().__init__(
            "Could not locate the 'synfig' binary.",
            hint=(
                "Set the SYNFIG_BIN environment variable to the full path of synfig(.exe), "
                "or install Synfig (https://www.synfig.org) and make sure it is on PATH. "
                "Run synfig_doctor for a diagnosis."
            ),
        )


class RenderError(SynfigMCPError):
    code = "render_error"


class RenderTimeoutError(RenderError):
    code = "render_timeout"


class RenderCancelledError(RenderError):
    code = "render_cancelled"


class UnsupportedTargetError(SynfigMCPError):
    code = "unsupported_target"


class BinaryInfoError(SynfigMCPError):
    code = "binary_info_error"


class HistoryError(SynfigMCPError):
    code = "history_error"


class BatchOperationError(SynfigMCPError):
    code = "batch_operation_error"
