import socket

import pytest

from cortex.guards.url_guard import SafeTransport


def test_url_guard_blocks_metadata_ip():
    """Verify that cloud metadata IPs are blocked (Axiom Ω₁)."""
    unsafe_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://127.0.0.1:8000/admin",
        "http://localhost:5000",
        "http://10.0.0.1/sensitive",
        "http://192.168.1.1/config",
    ]

    for url in unsafe_urls:
        with pytest.raises(ValueError, match="Sovereign URLGuard blocked"):
            SafeTransport.validate(url)


def test_url_guard_allows_safe_url(monkeypatch):
    """Verify that public legitimate URLs are allowed."""
    resolved_hosts = {
        "google.com": "8.8.8.8",
        "github.com": "140.82.112.3",
        "example.com": "93.184.216.34",
    }

    def _fake_getaddrinfo(host, port, type=0):
        assert host in resolved_hosts
        return [(socket.AF_INET, type or socket.SOCK_STREAM, 6, "", (resolved_hosts[host], 0))]

    monkeypatch.setattr("cortex.guards.url_guard.socket.getaddrinfo", _fake_getaddrinfo)

    safe_urls = [
        "https://google.com",
        "https://github.com/borjamoskv/Cortex-Persist",
        "http://example.com/api/v1/health",
    ]

    for url in safe_urls:
        # Should not raise
        SafeTransport.validate(url)


def test_url_guard_blocks_encoded_null():
    """Verify that null-byte injection is blocked."""
    url = "http://169.254.169.254\0.example.com"
    with pytest.raises(ValueError, match="Sovereign URLGuard blocked"):
        SafeTransport.validate(url)


def test_url_guard_blocks_hostname_resolving_to_private_ip(monkeypatch):
    """Verify DNS-rebinding style hostnames resolving private are blocked."""

    def _fake_getaddrinfo(host, port, type=0):
        assert host == "internal.example.com"
        return [(2, type, 6, "", ("10.0.0.7", 0))]

    monkeypatch.setattr("cortex.guards.url_guard.socket.getaddrinfo", _fake_getaddrinfo)

    with pytest.raises(ValueError, match="Sovereign URLGuard blocked"):
        SafeTransport.validate("https://internal.example.com/api")
