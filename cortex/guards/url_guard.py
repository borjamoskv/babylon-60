# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""CORTEX Sovereign URLGuard — SSRF Mitigation Layer.

Implements centralized validation for all outgoing remote requests.
Addresses CodeQL Alert #95 (Server-Side Request Forgery).

Axiom: Ω₃ (Byzantine Default)
  - No external URL is trusted by default.
  - Private CIDR ranges are blocked to prevent internal infrastructure probing.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger("cortex.guards.url_guard")

# Private IP ranges (RFC 1918, etc.) to block
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918
    ipaddress.ip_network("169.254.0.0/16"),  # IPv4 link-local / Metadata
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local addr
]

_ALLOWED_SCHEMES = {"http", "https"}


def _is_private_host(host: str) -> bool:
    """Return True when a host literal or resolved address lands in a blocked range."""
    try:
        ip = ipaddress.ip_address(host)
        return any(ip in network for network in _PRIVATE_NETWORKS)
    except ValueError:
        pass

    lowered = host.lower()
    if lowered in {"localhost", "127.0.0.1", "::1", "metadata.google.internal"}:
        return True

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        logger.warning("URLGuard: DNS resolution failed for %s: %s", host, exc)
        return True

    for _family, _type, _proto, _canonname, sockaddr in infos:
        candidate = sockaddr[0]
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if any(ip in network for network in _PRIVATE_NETWORKS):
            logger.error(
                "URLGuard: Blocked hostname %s resolving to private IP %s", host, candidate
            )
            return True
    return False


def is_safe_url(url: str, allow_private: bool = False) -> bool:
    """Check if a URL is safe for an outbound request.

    Args:
        url: The URL to validate.
        allow_private: If True, bypass private network checks (use with CAUTION).

    Returns:
        True if URL is safe, False otherwise.
    """
    if not url or "\0" in url:
        return False

    try:
        parsed = urlparse(url)

        # 1. Scheme Validation
        if parsed.scheme not in _ALLOWED_SCHEMES:
            logger.warning("URLGuard: Blocked invalid scheme '%s' for URL: %s", parsed.scheme, url)
            return False

        # 2. Hostname Presence
        host = parsed.hostname
        if not host:
            logger.warning("URLGuard: Blocked URL with no hostname: %s", url)
            return False

        # 3. Private Network Protection (SSRF Mitigation)
        if not allow_private:
            if _is_private_host(host):
                logger.error("URLGuard: Blocked private or loopback host: %s", host)
                return False

        return True
    except Exception as e:
        logger.error("URLGuard: Validation error for %s: %s", url, e)
        return False


class SafeTransport:
    """A wrapper for HTTP clients (like httpx or aiohttp) that enforces URLGuard."""

    @staticmethod
    def validate(url: str) -> None:
        """Validate URL or raise ValueError if unsafe."""
        if not is_safe_url(url):
            raise ValueError(f"Sovereign URLGuard blocked unsafe request to: {url}")

    @staticmethod
    def inject_httpx(client_args: dict) -> dict:
        """Inject URL validation into httpx client arguments."""

        async def _check_url(request):
            SafeTransport.validate(str(request.url))

        event_hooks = client_args.setdefault("event_hooks", {})
        request_hooks = event_hooks.setdefault("request", [])
        request_hooks.append(_check_url)
        return client_args
