"""
URL and SSRF Validator for Asset Pipeline (Phase A5).
Guarantees HTTPS-only, resolves DNS, and blocks private/loopback/cloud-metadata targets.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Default provider domain allow-list
ALLOWED_DOMAINS = {
    "api.openverse.org",
    "openverse.org",
    "upload.wikimedia.org",
    "commons.wikimedia.org",
    "raw.githubusercontent.com",
}


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Check if an IP address belongs to loopback, private, link-local, or cloud metadata ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            # Explicit AWS/GCP/Azure link-local metadata address (169.254.169.254)
            or str(ip) == "169.254.169.254"
        )
    except ValueError:
        return True


def validate_asset_url(
    url: str,
    allowed_domains: set[str] | None = None,
    allow_custom_domains: bool = False,
) -> str:
    """
    Validate asset download URL against security constraints:
    1. Must use HTTPS scheme.
    2. Hostname must be in allowed domains (unless allow_custom_domains is enabled).
    3. Resolved DNS IP must NOT be private, loopback, or metadata service.
    Returns: Validated normalized URL string.
    Raises: ValueError with security reason if invalid.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Insecure scheme '{parsed.scheme}': only HTTPS URLs are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Missing hostname in URL.")

    allowed = allowed_domains or ALLOWED_DOMAINS
    if (
        not allow_custom_domains
        and hostname.lower() not in allowed
        and not any(hostname.lower().endswith(f".{d}") for d in allowed)
    ):
        raise ValueError(
            f"Domain '{hostname}' is not permitted by asset provider allowlist: {sorted(allowed)}"
        )

    # Resolve hostname to verify IP
    try:
        addr_info = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = str(sockaddr[0])
            if is_ip_private_or_restricted(ip_str):
                raise ValueError(
                    f"SSRF blocked: Domain '{hostname}' resolved to restricted IP '{ip_str}'."
                )
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for hostname '{hostname}': {exc}") from exc

    return url
