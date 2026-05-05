"""Offline verification for DORA evidence packs."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from cortex.compliance.dora.claim_policy import scan_text_for_claims
from cortex.compliance.dora.hashing import canonical_json_bytes, sha256_bytes
from cortex.compliance.dora.manifest import PackManifest


_PLACEHOLDER_PATTERN = re.compile(r"\b(TODO|TBD)\b|<country>|<vendor>|<customer>|lorem ipsum", re.I)
_ALLOWED_CLAIM_HEADINGS = (
    "non-claims",
    "prohibited claims",
    "prohibited practices",
    "red lines",
    "conditional claims",
)


@dataclass(frozen=True)
class VerifyCheck:
    """One verification check result."""

    severity: str
    code: str
    message: str
    path: str | None = None


@dataclass
class VerifyResult:
    """Aggregate verification result for a DORA evidence pack."""

    status: str
    checks: list[VerifyCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return true when no failing check is present."""

        return not any(check.severity == "FAIL" for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable result."""

        return {
            "status": self.status,
            "checks": [check.__dict__ for check in self.checks],
        }


def verify_dora_pack(
    pack_path: str | Path,
    *,
    strict: bool = False,
    allow_sample: bool = False,
    allow_draft: bool = True,
) -> VerifyResult:
    """Verify a DORA evidence-pack ZIP."""

    checks: list[VerifyCheck] = []
    path = Path(pack_path)
    try:
        with zipfile.ZipFile(path) as archive:
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            _verify_zip_contents(
                archive,
                names,
                checks,
                strict=strict,
                allow_sample=allow_sample,
                allow_draft=allow_draft,
            )
    except zipfile.BadZipFile:
        checks.append(VerifyCheck("FAIL", "ZIP_INVALID", "Pack is not a readable ZIP.", str(path)))
    status = _status_from_checks(checks)
    return VerifyResult(status=status, checks=checks)


def _verify_zip_contents(
    archive: zipfile.ZipFile,
    names: list[str],
    checks: list[VerifyCheck],
    *,
    strict: bool,
    allow_sample: bool,
    allow_draft: bool,
) -> None:
    if "manifest.json" not in names:
        checks.append(VerifyCheck("FAIL", "MANIFEST_MISSING", "manifest.json is missing."))
        return
    checks.append(VerifyCheck("PASS", "ZIP_READABLE", "ZIP is readable."))

    try:
        manifest = PackManifest.model_validate_json(archive.read("manifest.json"))
    except (KeyError, ValidationError, json.JSONDecodeError, ValueError) as err:
        checks.append(VerifyCheck("FAIL", "MANIFEST_INVALID", f"Manifest is invalid: {err}"))
        return
    checks.append(VerifyCheck("PASS", "MANIFEST_VALID", "Manifest schema valid."))

    manifest_doc_paths = {document.path for document in manifest.documents}
    actual_doc_paths = set(names) - {"manifest.json"}
    missing = sorted(manifest_doc_paths - actual_doc_paths)
    for document_path in missing:
        checks.append(
            VerifyCheck("FAIL", "DOCUMENT_MISSING", "Document listed in manifest is missing.", document_path)
        )

    extra = sorted(actual_doc_paths - manifest_doc_paths)
    for document_path in extra:
        severity = "FAIL" if strict else "WARN"
        checks.append(VerifyCheck(severity, "DOCUMENT_EXTRA", "Unlisted document present.", document_path))

    for document in sorted(manifest.documents, key=lambda item: item.path):
        if document.path in missing:
            continue
        data = archive.read(document.path)
        digest = sha256_bytes(data)
        if digest == document.sha256:
            checks.append(VerifyCheck("PASS", "DOCUMENT_HASH_MATCH", "Document hash matches.", document.path))
        else:
            checks.append(
                VerifyCheck("FAIL", "DOCUMENT_HASH_MISMATCH", "Document hash mismatch.", document.path)
            )
        _verify_text_policy(data.decode("utf-8"), document.path, checks)

    _verify_pack_hash(manifest, checks)
    _verify_lifecycle(
        manifest,
        checks,
        strict=strict,
        allow_sample=allow_sample,
        allow_draft=allow_draft,
    )
    _verify_embedded_validation(manifest, checks, strict=strict)


def _verify_pack_hash(manifest: PackManifest, checks: list[VerifyCheck]) -> None:
    payload = manifest.model_dump(mode="json")
    expected = payload.pop("pack_sha256", None)
    actual = sha256_bytes(canonical_json_bytes(payload))
    if expected == actual:
        checks.append(VerifyCheck("PASS", "PACK_HASH_MATCH", "Pack hash matches manifest content."))
    else:
        checks.append(VerifyCheck("FAIL", "PACK_HASH_MISMATCH", "Pack hash mismatch."))


def _verify_lifecycle(
    manifest: PackManifest,
    checks: list[VerifyCheck],
    *,
    strict: bool,
    allow_sample: bool,
    allow_draft: bool,
) -> None:
    lifecycle = manifest.lifecycle_status
    if lifecycle == "sample":
        severity = "PASS" if allow_sample and not strict else "FAIL"
        checks.append(VerifyCheck(severity, "PACK_SAMPLE", "Pack is sample."))
    if lifecycle == "draft":
        if allow_draft and not strict:
            checks.append(VerifyCheck("WARN", "PACK_DRAFT", "Pack is draft."))
        else:
            checks.append(VerifyCheck("FAIL", "PACK_DRAFT", "Pack is draft."))
    if lifecycle in {"superseded", "expired", "revoked", "failed"}:
        checks.append(VerifyCheck("FAIL", "PACK_NOT_USABLE", f"Pack lifecycle is {lifecycle}."))

    try:
        valid_until = datetime.fromisoformat(manifest.valid_until_utc.replace("Z", "+00:00"))
    except ValueError:
        checks.append(VerifyCheck("FAIL", "PACK_EXPIRY_INVALID", "Pack expiry timestamp is invalid."))
        return
    if valid_until < datetime.now(timezone.utc):
        checks.append(VerifyCheck("FAIL", "PACK_EXPIRED", "Pack is expired."))


def _verify_embedded_validation(
    manifest: PackManifest,
    checks: list[VerifyCheck],
    *,
    strict: bool,
) -> None:
    for issue in manifest.validation.errors:
        checks.append(VerifyCheck("FAIL", issue.code, issue.message, issue.path))
    for issue in manifest.validation.warnings:
        checks.append(VerifyCheck("FAIL" if strict else "WARN", issue.code, issue.message, issue.path))


def _verify_text_policy(text: str, path: str, checks: list[VerifyCheck]) -> None:
    if _PLACEHOLDER_PATTERN.search(text):
        checks.append(VerifyCheck("FAIL", "PLACEHOLDER_FOUND", "Unresolved placeholder found.", path))

    allowed_lines = _allowed_claim_lines(text)
    for finding in scan_text_for_claims(text, include_conditional=True):
        if finding.line in allowed_lines:
            continue
        severity = "WARN" if finding.conditional else "FAIL"
        checks.append(
            VerifyCheck(
                severity,
                "CLAIM_POLICY_MATCH",
                f"Claim policy term found: {finding.term}",
                f"{path}:{finding.line}",
            )
        )


def _allowed_claim_lines(text: str) -> set[int]:
    allowed: set[int] = set()
    current_heading = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            current_heading = stripped.lower().strip("# ")
        if any(heading in current_heading for heading in _ALLOWED_CLAIM_HEADINGS):
            allowed.add(line_number)
    return allowed


def _status_from_checks(checks: list[VerifyCheck]) -> str:
    if any(check.severity == "FAIL" for check in checks):
        return "failed"
    if any(check.severity == "WARN" for check in checks):
        return "passed_with_warnings"
    return "passed"
