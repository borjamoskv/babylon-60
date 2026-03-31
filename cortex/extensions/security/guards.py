"""GUARDS-Ω — Sovereign Security Infrastructure.

Implements critical security boundaries:
1. SSRF Protection (URL Validation/IP Restriction)
2. Path Injection Protection (Safe Join/Traversal Guard)
3. Sensitive Data Masking (Logging protection)
"""

import ipaddress
import logging
import socket
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("cortex.extensions.security.guards")

# ─── SSRF PROTECTION ────────────────────────────────────────────────────────

# Private/Internal IP ranges to block (RFC 1918, etc.)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),         # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),        # IPv6 unique local
]


def is_safe_url(url: str, allowed_schemes: Optional[list[str]] = None) -> bool:
    """Validate URL to prevent SSRF and protocol smuggling.

    Checks:
    - Scheme (must be http/https by default)
    - Hostname presence
    - IP resolution (must not be private/internal)
    """
    if not allowed_schemes:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)
        if not parsed.scheme or parsed.scheme not in allowed_schemes:
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # 1. Block literal IP addresses in hostname
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if any(ip_obj in network for network in PRIVATE_IP_RANGES):
                return False
        except ValueError:
            # Not a literal IP, continue to resolution
            pass

        # 2. Resolve hostname to IP and check
        try:
            # Note: This is sync, should be used carefully in async loops
            # In ScraperEngine, we'll wrap it or use it sparingly.
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            if any(ip_obj in network for network in PRIVATE_IP_RANGES):
                return False
        except (socket.gaierror, ValueError):
            return False

        return True
    except Exception as e:
        logger.warning("URL validation error: %s", e)
        return False


# ─── PATH PROTECTION ─────────────────────────────────────────────────────────

def safe_path_join(base: str | Path, *parts: str) -> Path:
    """Safely join paths ensuring the result is within the base directory.

    Prevents path traversal attacks (../../etc/passwd).
    """
    base_path = Path(base).resolve()
    target_path = base_path.joinpath(*parts).resolve()

    if not target_path.is_relative_to(base_path):
        raise ValueError(
            f"Security: Path traversal attempt blocked: {target_path}"
        )

    return target_path


# ─── LOGGING PROTECTION ──────────────────────────────────────────────────────

def mask_sensitive(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive string (API keys, tokens)."""
    if not data:
        return ""
    if len(data) <= visible_chars:
        return "*" * len(data)
    return data[:visible_chars] + "..." + data[-visible_chars:]
