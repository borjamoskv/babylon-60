"""
Event Envelope for CORTEX-Persist Strict Origin Verification.
"""

import base64
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from .registry import KeyRegistry


class EventEnvelope:
    """
    Cryptographic envelope for events. Enforces canonical JSON representation
    and strict signature verification.
    """

    def __init__(self, payload: dict[str, Any], key_id: str, signature_b64: str | None = None):
        self.payload = payload
        self.key_id = key_id
        self.signature_b64 = signature_b64

    @staticmethod
    def canonicalize(payload: dict[str, Any]) -> bytes:
        """Returns the canonical JSON representation of the payload."""
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def sign(self, private_key_b64: str) -> None:
        """Signs the canonical payload with the provided private key."""
        priv_bytes = base64.b64decode(private_key_b64)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)

        canonical_payload = self.canonicalize(self.payload)
        sig = private_key.sign(canonical_payload)
        self.signature_b64 = base64.b64encode(sig).decode("utf-8")

    def verify(self, registry: KeyRegistry) -> bool:
        """
        Verifies the signature of the envelope against the provided KeyRegistry.
        Returns True if the signature is valid and the key is active.
        """
        if not self.signature_b64:
            return False

        key_record = registry.get_key(self.key_id)
        if not key_record or not key_record.is_active:
            return False

        try:
            pub_bytes = base64.b64decode(key_record.public_key_b64)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

            sig_bytes = base64.b64decode(self.signature_b64)
            canonical_payload = self.canonicalize(self.payload)

            public_key.verify(sig_bytes, canonical_payload)
            return True
        except (InvalidSignature, ValueError):
            return False

    def to_dict(self) -> dict[str, Any]:
        """Serializes the envelope to a dictionary."""
        return {
            "payload": self.payload,
            "key_id": self.key_id,
            "signature": self.signature_b64,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        """Deserializes an envelope from a dictionary."""
        return cls(
            payload=data.get("payload", {}),
            key_id=data.get("key_id", ""),
            signature_b64=data.get("signature"),
        )
