from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class IntegrationVerifier:
    def verify_telemetry_bundle(self, bundle_path: Path) -> dict[str, Any]:
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
        required = ["agent_id", "fingerprint", "timestamp", "capabilities", "schema_version"]
        missing = [k for k in required if k not in data]
        return {"valid": not missing, "missing": missing}

    def verify_snapshot_chain(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        prev = None
        for i, snap in enumerate(snapshots):
            if snap.get("prev_hash") != prev:
                return {"valid": False, "broken_at": i, "reason": "prev_hash mismatch"}
            prev = snap.get("snapshot_id")
        return {"valid": True}

    def verify_bridge_artifact(self, bridge: dict[str, Any]) -> dict[str, Any]:
        required = ["bridge_id", "agent_id", "expected_signature", "actual_signature", "adapter_code"]
        missing = [k for k in required if k not in bridge]
        if missing:
            return {"valid": False, "missing": missing}
        expected = bridge["bridge_id"]
        recomputed = _sha256_text(
            f'{bridge["agent_id"]}:{bridge["expected_signature"]}:{bridge["actual_signature"]}:{bridge["adapter_code"]}'
        )
        return {"valid": expected == recomputed, "recomputed": recomputed}
