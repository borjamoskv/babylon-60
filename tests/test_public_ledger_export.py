from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cortex.ledger.public_export import (
    ExportAuthority,
    public_key_record,
    write_public_ledger_export,
)
from cortex.ledger.public_verifier import verify_export

TENANT_ID = "tenant-acme"
STREAM_ID = "tenant:acme:ledger:primary"
ACTOR_ID = "agent-risk-01"
ACTOR_KEY_ID = "ed25519:agent-risk-01:test-export-001"
EXPORT_KEY_ID = "ed25519:export-authority:test-export-001"
CREATED_AT = "2026-02-03T10:15:30Z"


def test_write_public_ledger_export_package_with_verification_report(tmp_path: Path) -> None:
    actor_private_key = Ed25519PrivateKey.generate()
    export_private_key = Ed25519PrivateKey.generate()
    event = _signed_event(actor_private_key)
    export_dir = tmp_path / "forensic-export"

    result = write_public_ledger_export(
        events=[event],
        export_dir=export_dir,
        public_keys=[
            public_key_record(
                key_id=ACTOR_KEY_ID,
                actor_id=ACTOR_ID,
                public_key=actor_private_key.public_key(),
                permissions=["fact.store"],
            )
        ],
        export_authority=ExportAuthority(
            key_id=EXPORT_KEY_ID,
            actor_id="export-authority-01",
            private_key=export_private_key,
        ),
        export_id="export-2026-02-03-001",
        tenant_id=TENANT_ID,
        stream_id=STREAM_ID,
        created_at=CREATED_AT,
        include_verification_report=True,
    )

    expected_files = {
        "events.jsonl",
        "key-events.jsonl",
        "manifest.json",
        "public-keys.json",
        "schema.json",
        "verification-profile.json",
        "verification-report.json",
    }
    assert expected_files <= {path.name for path in export_dir.iterdir()}
    assert not (export_dir / "facts.jsonl").exists()
    assert result.verification_report_path == export_dir / "verification-report.json"
    assert result.verification_result == "VALID_FULL_STRICT"
    assert result.manifest_hash == _sha256_file(export_dir / "manifest.json")

    report = verify_export(export_dir)
    assert report["result"] == "VALID_FULL_STRICT"
    assert report["guarantees"]["integrity_verified"] is True
    assert report["guarantees"]["origin_authenticity_verified"] is True
    assert report["guarantees"]["authority_verified"] is True
    assert report["guarantees"]["completeness_verified"] is True
    assert report["guarantees"]["truth_verified"] is False
    assert report == _load_json(export_dir / "verification-report.json")

    manifest = _load_json(export_dir / "manifest.json")
    public_keys = _load_json(export_dir / "public-keys.json")
    assert manifest["signature"]["key_id"] == EXPORT_KEY_ID
    assert manifest["hashes"]["events_file_sha256"] == _sha256_file(export_dir / "events.jsonl")
    assert manifest["hashes"]["public_keys_file_sha256"] == _sha256_file(
        export_dir / "public-keys.json"
    )
    assert {key["key_id"] for key in public_keys["keys"]} == {ACTOR_KEY_ID, EXPORT_KEY_ID}
    assert manifest["counts"]["event_count"] == 1
    assert manifest["range"]["first_sequence"] == 1
    assert manifest["range"]["last_sequence"] == 1


def test_write_public_ledger_export_rejects_inline_fact_payload(tmp_path: Path) -> None:
    actor_private_key = Ed25519PrivateKey.generate()
    export_private_key = Ed25519PrivateKey.generate()
    event = _signed_event(actor_private_key)
    event["detail"] = dict(event["detail"])
    event["detail"]["payload"] = "plaintext fact body"

    with pytest.raises(ValueError, match="inline fact payload"):
        write_public_ledger_export(
            events=[event],
            export_dir=tmp_path / "forensic-export",
            public_keys=[
                public_key_record(
                    key_id=ACTOR_KEY_ID,
                    actor_id=ACTOR_ID,
                    public_key=actor_private_key.public_key(),
                    permissions=["fact.store"],
                )
            ],
            export_authority=ExportAuthority(
                key_id=EXPORT_KEY_ID,
                actor_id="export-authority-01",
                private_key=export_private_key,
            ),
            export_id="export-2026-02-03-001",
            tenant_id=TENANT_ID,
            stream_id=STREAM_ID,
            created_at=CREATED_AT,
        )


def _signed_event(private_key: Ed25519PrivateKey) -> dict[str, Any]:
    event: dict[str, Any] = {
        "action": "fact.store",
        "actor_id": ACTOR_ID,
        "actor_key_id": ACTOR_KEY_ID,
        "detail": {
            "fact_type": "risk_signal",
            "payload_ref": "facts/tenant-acme/fact-001.enc.json",
            "subject_ref": "subject:hmac-sha256:01HX",
        },
        "event_id": "evt_01HXEXPORT0000000000000001",
        "hash_alg": "sha256",
        "issued_at": CREATED_AT,
        "nonce": "nonce_01HXEXPORT0000000000000001",
        "prev_hash": "GENESIS",
        "project": "cortex-persist",
        "recorded_at": CREATED_AT,
        "schema_version": "cortex-ledger-event-v1",
        "sequence": 1,
        "signature_alg": "ed25519",
        "stream_id": STREAM_ID,
        "target": "fact:001",
        "tenant_id": TENANT_ID,
    }
    event["hash"] = _event_hash(event)
    event["origin_signature"] = _b64url_encode(
        private_key.sign(_canonical_json(event).encode("utf-8"))
    )
    return event


def _event_hash(event: dict[str, Any]) -> str:
    scope = dict(event)
    scope.pop("hash", None)
    scope.pop("origin_signature", None)
    return hashlib.sha256(_canonical_json(scope).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value
