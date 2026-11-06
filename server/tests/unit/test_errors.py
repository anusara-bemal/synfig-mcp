"""Unit tests for errors."""

from synfig_mcp.errors import (
    BridgeAuthError,
    BridgeConnectionError,
    DocumentNotFoundError,
    LayerNotFoundError,
    SecuritySandboxError,
    SynfigError,
)


def test_error_to_dict() -> None:
    err = BridgeConnectionError("Cannot connect", details={"host": "127.0.0.1"})
    payload = err.to_dict()
    assert payload["code"] == 1001
    assert payload["message"] == "Cannot connect"
    assert payload["data"] == {"host": "127.0.0.1"}


def test_error_hierarchy() -> None:
    assert issubclass(BridgeAuthError, SynfigError)
    assert issubclass(DocumentNotFoundError, SynfigError)
    assert issubclass(LayerNotFoundError, SynfigError)
    assert issubclass(SecuritySandboxError, SynfigError)
