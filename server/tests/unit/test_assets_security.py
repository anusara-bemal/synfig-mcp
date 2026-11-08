"""
Unit tests for Asset Pipeline Security: SSRF validator, SVG sanitizer, raster hardening,
and license policy evaluation (Phase A5).
"""

from __future__ import annotations

import pytest

from synfig_mcp.assets.models import LicensePolicy
from synfig_mcp.assets.security.svg_sanitizer import sanitize_svg
from synfig_mcp.assets.security.url_validator import is_ip_private_or_restricted, validate_asset_url


def test_ssrf_ip_restriction() -> None:
    assert is_ip_private_or_restricted("127.0.0.1") is True
    assert is_ip_private_or_restricted("10.0.0.1") is True
    assert is_ip_private_or_restricted("192.168.1.100") is True
    assert is_ip_private_or_restricted("172.16.5.4") is True
    assert is_ip_private_or_restricted("169.254.169.254") is True
    assert is_ip_private_or_restricted("::1") is True
    assert is_ip_private_or_restricted("8.8.8.8") is False


def test_url_validator_insecure_scheme() -> None:
    with pytest.raises(ValueError, match="only HTTPS"):
        validate_asset_url("http://api.openverse.org/v1/images/123")


def test_url_validator_disallowed_domain() -> None:
    with pytest.raises(ValueError, match="not permitted"):
        validate_asset_url("https://malicious-site.com/asset.png")


def test_svg_sanitizer_removes_scripts() -> None:
    malicious_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <script>alert('XSS');</script>
        <circle cx="50" cy="50" r="40" fill="red" />
    </svg>"""
    cleaned = sanitize_svg(malicious_svg)
    assert "<script" not in cleaned
    assert "alert" not in cleaned
    assert "<circle" in cleaned


def test_svg_sanitizer_removes_event_handlers() -> None:
    malicious_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <rect width="50" height="50" onload="evilFunction()" onclick="stealCookie()" fill="blue" />
    </svg>"""
    cleaned = sanitize_svg(malicious_svg)
    assert "onload" not in cleaned
    assert "onclick" not in cleaned
    assert "evilFunction" not in cleaned
    assert "<rect" in cleaned


def test_svg_sanitizer_removes_foreign_object() -> None:
    malicious_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <foreignObject width="100" height="100">
            <iframe src="https://attacker.com/leak"></iframe>
        </foreignObject>
        <path d="M 10 10 L 90 90" stroke="black" />
    </svg>"""
    cleaned = sanitize_svg(malicious_svg)
    assert "foreignObject" not in cleaned.lower()
    assert "iframe" not in cleaned.lower()
    assert "<path" in cleaned


def test_svg_sanitizer_rejects_xml_bomb() -> None:
    xml_bomb = """<?xml version="1.0"?>
    <!DOCTYPE lolz [
        <!ENTITY lol "lol">
        <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;">
    ]>
    <svg><text>&lol2;</text></svg>"""
    with pytest.raises(ValueError, match="entity expansion"):
        sanitize_svg(xml_bomb)


def test_license_policy_evaluation() -> None:
    policy = LicensePolicy()

    # CC0 & PDM allowed
    ok_cc0, _ = policy.evaluate_license("cc0")
    assert ok_cc0 is True

    ok_pdm, _ = policy.evaluate_license("pdm")
    assert ok_pdm is True

    # No-Derivatives blocked
    ok_nd, reason_nd = policy.evaluate_license("by-nd")
    assert ok_nd is False
    assert "No-Derivatives" in reason_nd

    # Non-Commercial blocked for commercial project
    ok_nc, reason_nc = policy.evaluate_license("by-nc")
    assert ok_nc is False
    assert "Non-Commercial" in reason_nc

    # Mature content rejected
    ok_mature, reason_m = policy.evaluate_license("cc0", is_mature=True)
    assert ok_mature is False
    assert "mature content" in reason_m
