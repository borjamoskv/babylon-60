"""
CORTEX v5.0 — Deterministic Taint Guard (SAGA-2).

Enforces the AX-041 Write-Path Contract by generating and validating
cryptographic attribution signatures on generative output prior to persistence.
"""

import hashlib
from datetime import datetime, timezone


class TaintEngine:
    """Motor criptográfico para la generación y verificación de Taints (CORTEX-TAINT)."""

    prefix = "taint"

    @staticmethod
    def _hash_content(content: str) -> str:
        """Calcula el SHA3-256 del contenido canónico (string principal)."""
        return hashlib.sha3_256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_taint(agent_id: str, session_id: str, content: str) -> str:
        """
        Genera la firma determinista CORTEX-TAINT.
        Formato: taint:{agent_id}:{session_id}:{timestamp_iso8601}:{sha3_256}
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        digest = TaintEngine._hash_content(content)
        return f"{TaintEngine.prefix}:{agent_id}:{session_id}:{timestamp}:{digest}"

    @staticmethod
    def hash_content(content: str) -> str:
        """Expose the canonical digest used by CORTEX-TAINT."""
        return TaintEngine._hash_content(content)

    @staticmethod
    def extract_digest(taint_str: str | None) -> str | None:
        """Return the digest suffix from a taint token, if present."""
        if not taint_str or not taint_str.startswith(f"{TaintEngine.prefix}:"):
            return None

        try:
            digest_in_taint = taint_str.rsplit(":", 1)[-1]
        except IndexError:
            return None

        return digest_in_taint or None

    @staticmethod
    def verify_digest(expected_digest: str, taint_str: str | None) -> bool:
        """Compare a taint token against a known canonical digest."""
        return TaintEngine.extract_digest(taint_str) == expected_digest

    @staticmethod
    def verify_taint(content: str, taint_str: str) -> bool:
        """
        Verifica que el payload (content) coincide exactamente con la firma SHA3-256
        embebida en el Taint dictado por el sistema.
        """
        expected_digest = TaintEngine._hash_content(content)
        return TaintEngine.verify_digest(expected_digest, taint_str)
