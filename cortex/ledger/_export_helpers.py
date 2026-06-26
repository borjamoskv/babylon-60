# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import base64
import os
import stat
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from cortex.ledger._verifier_events import STRICT_REQUIRED_EVENT_FIELDS
from cortex.ledger.public_verifier_utils import (
    _canonical_public_json,
    _event_hash,
    _merkle_root_v1,
    _sha256_file,
)

PUBLIC_EXPORT_MANIFEST_VERSION = "cortex-forensic-export-manifest-v1"
KEY_REGISTRY_VERSION = "cortex-key-registry-v1"
EVENT_SCHEMA_VERSION = "cortex-ledger-event-schema-v1"
VERIFICATION_PROFILE_VERSION = "cortex-verification-profile-v1"

FORBIDDEN_EXPORT_TOKENS = (
    "private_key",
    "seed_hex",
    "begin private key",
    "api_key",
    "secret_key",
    "password",
)
EXECUTABLE_SUFFIXES = (".bat", ".cmd", ".exe", ".js", ".mjs", ".py", ".sh")
PUBLIC_EXPORT_FILES = frozenset(
    {
        "events.jsonl",
        "key-events.jsonl",
        "manifest.json",
        "public-keys.json",
        "schema.json",
        "verification-profile.json",
        "verification-report.json",
        "checkpoints.jsonl",
    }
)

LEGACY_LIMITATIONS = (
    "legacy_v0_integrity_only",
    "origin_authenticity_not_verified",
    "manifest_completeness_not_available",
)


def public_key_record(
    *,
    key_id: str,
    actor_id: str,
    public_key: Any,
    permissions: Sequence[str],
    algorithm: str = "ed25519",
    actor_type: str = "agent",
    environment: str = "test",
    valid_from: str = "2026-01-01T00:00:00Z",
    valid_until: str = "2027-01-01T00:00:00Z",
    hardware_backed: bool = False,
) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "actor_type": actor_type,
        "algorithm": algorithm,
        "environment": environment,
        "hardware_backed": hardware_backed,
        "key_id": key_id,
        "permissions": list(permissions),
        "public_key": _public_key_b64url(public_key),
        "status": "active",
        "valid_from": valid_from,
        "valid_until": valid_until,
    }


def manifest_document(
    *,
    events: Sequence[Mapping[str, Any]],
    event_hashes: Sequence[str],
    export_id: str,
    tenant_id: str,
    stream_id: str,
    created_by: str,
    created_at: str,
    purpose: str,
    environment: str,
    root: Path,
    checkpoint_count: int = 0,
) -> dict[str, Any]:
    first = events[0]
    last = events[-1]

    hashes = {
        "events_file_sha256": _sha256_file(root / "events.jsonl"),
        "first_event_hash": event_hashes[0],
        "key_events_file_sha256": _sha256_file(root / "key-events.jsonl"),
        "last_event_hash": event_hashes[-1],
        "merkle_root": _merkle_root_v1(event_hashes),
        "public_keys_file_sha256": _sha256_file(root / "public-keys.json"),
        "schema_file_sha256": _sha256_file(root / "schema.json"),
        "verification_profile_sha256": _sha256_file(root / "verification-profile.json"),
    }
    if checkpoint_count > 0:
        hashes["checkpoints_file_sha256"] = _sha256_file(root / "checkpoints.jsonl")

    return {
        "algorithms": {
            "event_hash": "sha256",
            "manifest_hash": "sha256",
            "merkle": "merkle-profile-v1",
            "signature": "ed25519",
        },
        "counts": {
            "erasure_tombstone_count": 0,
            "event_count": len(events),
            "redacted_event_count": 0,
            "checkpoint_count": checkpoint_count,
        },
        "created_at": created_at,
        "created_by": created_by,
        "environment": environment,
        "export_id": export_id,
        "hashes": hashes,
        "limitations": [],
        "purpose": purpose,
        "range": {
            "first_recorded_at": first["recorded_at"],
            "first_sequence": first["sequence"],
            "last_recorded_at": last["recorded_at"],
            "last_sequence": last["sequence"],
        },
        "schema_version": PUBLIC_EXPORT_MANIFEST_VERSION,
        "stream_id": stream_id,
        "tenant_id": tenant_id,
    }


def key_registry_document(
    *,
    tenant_id: str,
    public_keys: Sequence[Mapping[str, Any]],
    export_authority: Any,
    generated_at: str,
) -> dict[str, Any]:
    keys = [dict(key) for key in public_keys]
    if not any(key.get("key_id") == export_authority.key_id for key in keys):
        keys.append(
            public_key_record(
                key_id=export_authority.key_id,
                actor_id=export_authority.actor_id,
                actor_type="export_authority",
                environment=export_authority.environment,
                public_key=export_authority.private_key.public_key(),
                permissions=["ledger.export"],
            )
        )
    return {
        "generated_at": generated_at,
        "keys": sorted(keys, key=lambda key: str(key["key_id"])),
        "schema_version": KEY_REGISTRY_VERSION,
        "tenant_id": tenant_id,
    }


def schema_document() -> dict[str, str]:
    return {"profile": "public-v1-strict", "schema_version": EVENT_SCHEMA_VERSION}


def verification_profile_document() -> dict[str, str]:
    return {
        "canonicalization": "canonical-json-v1",
        "merkle": "merkle-profile-v1",
        "profile": "public-v1-strict",
        "schema_version": VERIFICATION_PROFILE_VERSION,
    }


def validate_public_events(
    events: Sequence[Mapping[str, Any]],
    *,
    tenant_id: str,
    stream_id: str,
) -> list[str]:
    previous_sequence: int | None = None
    previous_hash = "GENESIS"
    seen_event_ids: set[str] = set()
    seen_nonces: set[str] = set()
    event_hashes: list[str] = []
    for index, event in enumerate(events, start=1):
        missing = sorted(STRICT_REQUIRED_EVENT_FIELDS - event.keys())
        if missing:
            raise ValueError(f"event missing public-v1 fields at {index}: {','.join(missing)}")
        event_id, nonce = str(event["event_id"]), str(event["nonce"])
        if event_id in seen_event_ids:
            raise ValueError(f"duplicate event_id before export: {event_id}")
        if nonce in seen_nonces:
            raise ValueError(f"duplicate nonce before export: {nonce}")
        seen_event_ids.add(event_id)
        seen_nonces.add(nonce)
        if event.get("tenant_id") != tenant_id:
            raise ValueError(f"event tenant mismatch: {event_id}")
        if event.get("stream_id") != stream_id:
            raise ValueError(f"event stream mismatch: {event_id}")
        if event.get("prev_hash") != previous_hash:
            raise ValueError(f"event chain break before export: {event_id}")
        sequence = event.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise ValueError(f"event sequence invalid: {event_id}")
        if previous_sequence is None and sequence != 1:
            raise ValueError(f"event sequence must start at 1: {event_id}")
        if previous_sequence is not None and sequence != previous_sequence + 1:
            raise ValueError(f"event sequence gap: {event_id}")
        detail = event.get("detail")
        if isinstance(detail, Mapping) and any(
            field in detail for field in ("content", "payload", "plaintext", "fact_content")
        ):
            raise ValueError(f"event contains inline fact payload: {event_id}")
        actual_hash = _event_hash(event)
        if actual_hash != event.get("hash"):
            raise ValueError(f"event hash mismatch before export: {event_id}")
        event_hashes.append(actual_hash)
        previous_sequence, previous_hash = sequence, actual_hash
    return event_hashes


def validate_public_key_records(keys: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for key in keys:
        key_id = key.get("key_id")
        if not isinstance(key_id, str) or not key_id:
            raise ValueError("public key record missing key_id")
        if key_id in seen:
            raise ValueError(f"duplicate public key id: {key_id}")
        seen.add(key_id)
        if key.get("algorithm") not in ("ed25519", "mldsa44", "mldsa65", "mldsa87"):
            raise ValueError(f"public key algorithm unsupported: {key_id}")
        if not isinstance(key.get("public_key"), str):
            raise ValueError(f"public key missing material: {key_id}")
        if not isinstance(key.get("permissions"), list):
            raise ValueError(f"public key permissions missing: {key_id}")


def validate_public_checkpoints(checkpoints: Sequence[Mapping[str, Any]]) -> None:
    required = (
        "root_hash",
        "start_event_id",
        "end_event_id",
        "event_count",
        "mldsa_signature",
        "mldsa_public_key",
    )
    for cp in checkpoints:
        for field in required:
            if field not in cp:
                raise ValueError(f"checkpoint missing required field: {field}")


def prepare_export_dir(root: Path, *, allow_overwrite: bool) -> None:
    if root.exists() and any(root.iterdir()) and not allow_overwrite:
        raise FileExistsError(f"export directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)


def assert_no_private_material(value: Any) -> None:
    text = _canonical_public_json(value).lower()
    for token in FORBIDDEN_EXPORT_TOKENS:
        if token in text:
            raise ValueError(f"export contains forbidden token: {token}")


def scan_export_safety(root: Path, *, allowed_files: set[str] | None = None) -> None:
    allowed = allowed_files or set(PUBLIC_EXPORT_FILES)
    for path in root.iterdir():
        if not path.is_file():
            raise ValueError(f"export contains non-file entry: {path.name}")
        if path.name not in allowed:
            raise ValueError(f"export contains unexpected file: {path.name}")
        if path.suffix in EXECUTABLE_SUFFIXES:
            raise ValueError(f"export contains executable-like file: {path.name}")
        if path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            raise ValueError(f"export contains executable file: {path.name}")
        assert_no_private_material(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    write_text_atomic(path, _canonical_public_json(value))


def write_text_atomic(path: Path, value: str) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(value, encoding="utf-8")
    os.replace(tmp_path, path)


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _public_key_b64url(public_key: Any) -> str:
    raw = (
        public_key.public_bytes_raw()
        if hasattr(public_key, "public_bytes_raw")
        else public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    )
    return b64url_encode(raw)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
