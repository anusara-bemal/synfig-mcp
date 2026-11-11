"""
Typed error hierarchy with stable numeric codes for synfig-mcp protocol and operations.
"""

from typing import Any


class SynfigError(Exception):
    """Base class for all synfig-mcp errors."""

    code: int = 1000
    message: str = "Internal Synfig MCP error"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        code: int | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        if code is not None:
            self.code = code

    def to_dict(self) -> dict[str, Any]:
        """Convert error to a standard JSON-RPC error payload."""
        return {
            "code": self.code,
            "message": self.message,
            "data": self.details,
        }


# Protocol & Connection Errors (1000-1099)
class BridgeConnectionError(SynfigError):
    """Failed to connect to the Synfig Studio bridge."""

    code = 1001
    message = "Cannot connect to Synfig Studio live bridge"


class BridgeAuthError(SynfigError):
    """Authentication or token verification failure with the live bridge."""

    code = 1002
    message = "Authentication with Synfig Studio bridge failed"


class ProtocolVersionMismatchError(SynfigError):
    """Protocol version incompatibility between server and Studio bridge."""

    code = 1003
    message = "Incompatible bridge protocol version"


# Document & Scene Errors (1100-1199)
class DocumentNotFoundError(SynfigError):
    """Requested document or canvas ID does not exist."""

    code = 1101
    message = "Document or canvas not found"


class LayerNotFoundError(SynfigError):
    """Specified layer not found in document."""

    code = 1102
    message = "Layer not found"


class ParamNotFoundError(SynfigError):
    """Specified parameter not found on layer."""

    code = 1103
    message = "Parameter not found on layer"


# Validation & Security Errors (1200-1299)
class ValidationError(SynfigError):
    """Parameter or action arguments failed schema validation."""

    code = 1201
    message = "Validation failed for action parameters"


class UnsupportedValueTypeError(ValidationError):
    """A value could not be represented in the Synfig document format.

    Raised by the SIF writer when a parameter carries a value type that has no
    upstream-compatible XML representation.  Failing here is deliberate: a
    lossy fallback (stringifying the value) produces a document that Synfig
    loads as a corrupt canvas, which is strictly worse than a typed error.
    """

    code = 1204
    message = "Unsupported value type for Synfig document serialisation"


class SecuritySandboxError(SynfigError):
    """File access outside of configured workspace sandbox."""

    code = 1202
    message = "File path access outside allowed workspace sandbox"


class SecurityError(SynfigError):
    """General security violation (network bind, perimeter, or protocol security)."""

    code = 1203
    message = "Security boundary violation"


# Execution & Render Errors (1300-1399)
class ActionExecutionError(SynfigError):
    """Synfig action execution failed in Studio or CLI."""

    code = 1301
    message = "Synfig action system failed to execute request"


class RenderError(SynfigError):
    """Rendering process failed."""

    code = 1302
    message = "Rendering failed"
