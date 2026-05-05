"""Manifest models and builders for DORA evidence packs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field

from cortex.compliance.dora.hashing import canonical_json_bytes, sha256_bytes
from cortex.compliance.dora.models import DoraConfig, EvidenceStatus, ValidationIssue

LifecycleStatus = Literal["sample", "draft", "issued", "superseded", "expired", "revoked", "failed"]
ValidationStatus = Literal["passed", "passed_with_warnings", "failed"]


class DocumentManifest(BaseModel):
    """Hash entry for one rendered pack document."""

    path: str
    sha256: str
    status: EvidenceStatus


class ManifestValidation(BaseModel):
    """Validation result embedded into the evidence pack manifest."""

    status: ValidationStatus
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class PackManifest(BaseModel):
    """Top-level DORA evidence-pack manifest."""

    pack_type: Literal["dora_evidence_pack"] = "dora_evidence_pack"
    manifest_version: str = "0.1"
    deployment_id: str
    deployment_mode: str
    customer_name: str | None = None
    cortex_version: str
    generated_at_utc: str
    valid_until_utc: str
    lifecycle_status: LifecycleStatus = "draft"
    source_config_hash: str
    template_version: str = "0.1"
    validation: ManifestValidation
    documents: list[DocumentManifest]
    claims_summary: dict[str, int]
    pack_sha256: str | None = None


def utc_now_string() -> str:
    """Return a second-precision UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def valid_until_string(generated_at_utc: str, validity_days: int) -> str:
    """Return the validity deadline for a generated timestamp."""

    base = datetime.fromisoformat(generated_at_utc.replace("Z", "+00:00"))
    return (base + timedelta(days=validity_days)).isoformat().replace("+00:00", "Z")


def validation_status(errors: list[ValidationIssue], warnings: list[ValidationIssue]) -> ValidationStatus:
    """Summarize validation issue severity for the manifest."""

    if errors:
        return "failed"
    if warnings:
        return "passed_with_warnings"
    return "passed"


def summarize_claims(config: DoraConfig) -> dict[str, int]:
    """Count configured claims by evidence status."""

    summary = {status.value: 0 for status in EvidenceStatus}
    for claim in config.claims:
        summary[claim.status.value] += 1
    return summary


def finalize_pack_hash(manifest: PackManifest) -> PackManifest:
    """Compute and set the manifest-level pack hash."""

    payload = manifest.model_dump(mode="json")
    payload.pop("pack_sha256", None)
    manifest.pack_sha256 = sha256_bytes(canonical_json_bytes(payload))
    return manifest
