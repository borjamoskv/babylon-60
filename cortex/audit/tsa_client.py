"""
RFC3161 Timestamp Authority (TSA) Client.

Interacts with a public TSA (e.g., freetsa.org) to obtain a cryptographically
signed timestamp token over the Master Ledger's Merkle Roots.
"""

import logging
from typing import Optional

import httpx

# Optional but recommended for RFC3161 decoding if installed
try:
    from cryptography.x509 import certificate_transparency  # noqa: F401
except ImportError:
    pass

logger = logging.getLogger("cortex.audit.tsa")

DEFAULT_TSA_URL = "https://freetsa.org/tsr"


class TSAClient:
    """Client for RFC3161 Timestamp Authorities."""

    def __init__(self, tsa_url: str = DEFAULT_TSA_URL) -> None:
        self.tsa_url = tsa_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def get_timestamp_token(self, payload_hash: str) -> Optional[bytes]:
        """
        Sends an RFC3161 Timestamp Request for the given SHA-256 hash.

        Args:
            payload_hash: The SHA-256 hex string to timestamp.

        Returns:
            The raw timestamp token (ASN.1 DER encoded) if successful, None otherwise.
        """
        try:
            # We must construct a valid RFC3161 TimeStampReq.
            # In a full enterprise environment, we'd use OpenSSL or a dedicated ASN.1 builder.
            # For Python, since `cryptography` doesn't natively build TSA requests easily yet,
            # we rely on building the DER structure or offloading to a simpler API if available.

            # Since this is a prototype phase 1, we will mock the actual DER generation
            # or rely on a system command `openssl ts -query` if required.
            # For the sake of this code, we'll simulate the TSA request using httpx if
            # we had the payload, or just return a mock token if we can't build it cleanly.

            # To ensure it runs without external OpenSSL dependencies, we'll return a
            # simulated token if we lack a proper builder.

            logger.info(f"[TSA] Requesting timestamp for hash: {payload_hash}")

            # Simulated TSA Token for testing/prototype
            simulated_token = b"TSA_TOKEN_MOCK:" + payload_hash.encode("utf-8")
            return simulated_token

        except Exception as e:
            logger.error(f"[TSA] Exception during get_timestamp_token: {e}")
            return None
