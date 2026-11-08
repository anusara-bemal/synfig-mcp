"""
Unit tests for Streamable HTTP transport authentication, Host allow-list,
and network bind security validations.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from synfig_mcp.errors import SecurityError
from synfig_mcp.http_transport import create_http_app, validate_network_bind
from synfig_mcp.server import create_server


def test_http_transport_missing_auth() -> None:
    server = create_server()
    app = create_http_app(server, host="127.0.0.1", token="secret-123")
    client = TestClient(app, base_url="http://127.0.0.1")

    # Missing Authorization header -> 401 with non-sensitive body
    resp = client.get("/mcp")
    assert resp.status_code == 401
    assert resp.text == "Unauthorized"


def test_http_transport_invalid_auth() -> None:
    server = create_server()
    app = create_http_app(server, host="127.0.0.1", token="secret-123")
    client = TestClient(app, base_url="http://127.0.0.1")

    # Wrong token -> 401 with non-sensitive body
    resp = client.get("/mcp", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401
    assert resp.text == "Unauthorized"


def test_http_transport_forbidden_host() -> None:
    server = create_server()
    app = create_http_app(
        server,
        host="127.0.0.1",
        token="secret-123",
        allowed_hosts=["127.0.0.1", "localhost"],
    )
    client = TestClient(app, base_url="http://127.0.0.1")

    # Request with disallowed Host header -> 403 with non-sensitive body
    resp = client.get(
        "/mcp",
        headers={"Host": "malicious-domain.com", "Authorization": "Bearer secret-123"},
    )
    assert resp.status_code == 403
    assert resp.text == "Forbidden"


def test_http_transport_valid_auth_and_host() -> None:
    server = create_server()
    app = create_http_app(
        server,
        host="127.0.0.1",
        token="secret-123",
        allowed_hosts=["127.0.0.1", "localhost"],
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        # Correct Authorization and Host header passes security middleware to MCP endpoint
        resp = client.get(
            "/mcp",
            headers={"Host": "127.0.0.1", "Authorization": "Bearer secret-123"},
        )
        assert resp.status_code not in (401, 403)


def test_validate_network_bind() -> None:
    # 1. Loopback bind always allowed even without token
    validate_network_bind(host="127.0.0.1", token=None, allow_remote=False)
    validate_network_bind(host="localhost", token=None, allow_remote=False)
    validate_network_bind(host="::1", token=None, allow_remote=False)

    # 2. Non-loopback without allow_remote -> refused
    with pytest.raises(SecurityError, match="Refusing to bind on non-loopback host"):
        validate_network_bind(host="0.0.0.0", token="secret", allow_remote=False)

    with pytest.raises(SecurityError, match="Refusing to bind on non-loopback host"):
        validate_network_bind(host="192.168.1.50", token="secret", allow_remote=False)

    # 3. Non-loopback with allow_remote but no token -> refused
    with pytest.raises(SecurityError, match="without a secure authentication token"):
        validate_network_bind(host="0.0.0.0", token=None, allow_remote=True)

    with pytest.raises(SecurityError, match="without a secure authentication token"):
        validate_network_bind(host="0.0.0.0", token="", allow_remote=True)

    # 4. Non-loopback with allow_remote and token -> allowed
    validate_network_bind(host="0.0.0.0", token="strong-secret-token", allow_remote=True)
