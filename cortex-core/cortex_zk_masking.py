import hashlib
import json
from typing import Any


class ZKSemanticMasking:
    """Generate deterministic, non-reversible proofs for Article 12 claim checks."""

    _VERSION = "cortex-zk-semantic-v1"

    def generate_proof(self, value: Any) -> str:
        canonical = self._canonicalize(value)
        digest = hashlib.sha256(f"{self._VERSION}\0{canonical}".encode()).hexdigest()
        return json.dumps(
            {"version": self._VERSION, "algorithm": "sha256-canonical", "digest": digest},
            sort_keys=True,
            separators=(",", ":"),
        )

    def verify_proof(self, value: Any, proof: str) -> tuple[bool, float]:
        try:
            payload = json.loads(proof)
        except (TypeError, json.JSONDecodeError):
            return False, 0.0

        expected = self.generate_proof(value)
        try:
            expected_payload = json.loads(expected)
        except json.JSONDecodeError:
            return False, 0.0

        matches = (
            payload.get("version") == self._VERSION
            and payload.get("algorithm") == "sha256-canonical"
            and payload.get("digest") == expected_payload["digest"]
        )
        return matches, 1.0 if matches else 0.0

    @staticmethod
    def _canonicalize(value: Any) -> str:
        if isinstance(value, str):
            return " ".join(value.split())
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
