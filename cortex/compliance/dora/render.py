"""Render DORA evidence-pack documents from validated configuration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cortex.compliance.dora.hashing import canonical_json_bytes, sha256_bytes, sha256_text
from cortex.compliance.dora.manifest import (
    DocumentManifest,
    ManifestValidation,
    PackManifest,
    finalize_pack_hash,
    summarize_claims,
    utc_now_string,
    valid_until_string,
    validation_status,
)
from cortex.compliance.dora.models import DoraConfig, EvidenceStatus, ValidationSeverity
from cortex.compliance.dora.validation import validate_dora_config

_LIFECYCLE_STATUSES = {"sample", "draft", "issued", "superseded", "expired", "revoked", "failed"}


CORE_MARKDOWN_DOCS: tuple[str, ...] = (
    "README.md",
    "CONTROL_MATRIX.md",
    "CONTRACT_ANNEX.md",
    "SHARED_RESPONSIBILITY_MODEL.md",
    "DATA_LOCATION_STATEMENT.md",
    "SUBPROCESSOR_REGISTER.md",
    "AUDIT_AND_LOGGING_STATEMENT.md",
    "INCIDENT_RESPONSE_RUNBOOK.md",
    "BUSINESS_CONTINUITY_STATEMENT.md",
    "EXIT_PLAN.md",
    "REGISTER_OF_INFORMATION_FIELDS.md",
    "SECURITY_CONTROLS_MAPPING.md",
)
GENERATED_PROFILE_DOC = "DEPLOYMENT_PROFILE.md"


@dataclass(frozen=True)
class RenderedDocument:
    """Rendered pack document."""

    path: str
    content: str
    status: EvidenceStatus = EvidenceStatus.CONFIG_DEPENDENT

    @property
    def sha256(self) -> str:
        """Return the UTF-8 content hash."""

        return sha256_text(self.content)


@dataclass(frozen=True)
class RenderedPack:
    """Rendered evidence pack before ZIP export."""

    documents: list[RenderedDocument]
    manifest: PackManifest

    def manifest_json(self) -> str:
        """Return canonical-ish pretty manifest JSON with trailing newline."""

        return self.manifest.model_dump_json(indent=2) + "\n"


def render_evidence_pack(
    config: DoraConfig,
    *,
    source_docs_dir: Path | None = None,
    generated_at_utc: str | None = None,
    lifecycle_status: str = "draft",
) -> RenderedPack:
    """Render documents and manifest for a DORA evidence pack."""

    if lifecycle_status not in _LIFECYCLE_STATUSES:
        raise ValueError(f"Unsupported DORA evidence pack lifecycle status: {lifecycle_status}")

    generated_at = generated_at_utc or utc_now_string()
    documents = _render_documents(config, source_docs_dir=source_docs_dir, generated_at_utc=generated_at)
    issues = validate_dora_config(config)
    errors = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
    warnings = [issue for issue in issues if issue.severity == ValidationSeverity.WARN]
    document_entries = [
        DocumentManifest(path=document.path, sha256=document.sha256, status=document.status)
        for document in documents
    ]
    manifest = PackManifest(
        deployment_id=config.pack.deployment_id,
        deployment_mode=config.pack.deployment_mode.value,
        customer_name=config.pack.customer_name,
        cortex_version=config.service.product_version,
        generated_at_utc=generated_at,
        valid_until_utc=valid_until_string(generated_at, config.pack.validity_days),
        lifecycle_status=lifecycle_status,  # type: ignore[arg-type]
        source_config_hash=sha256_bytes(canonical_json_bytes(config.model_dump(mode="json"))),
        validation=ManifestValidation(
            status=validation_status(errors, warnings),
            errors=errors,
            warnings=warnings,
        ),
        documents=document_entries,
        claims_summary=summarize_claims(config),
    )
    return RenderedPack(documents=documents, manifest=finalize_pack_hash(manifest))


def default_docs_dir() -> Path:
    """Return the repository documentation source directory when available."""

    return Path(__file__).resolve().parents[3] / "docs" / "compliance" / "dora"


def _render_documents(
    config: DoraConfig,
    *,
    source_docs_dir: Path | None,
    generated_at_utc: str,
) -> list[RenderedDocument]:
    docs_dir = source_docs_dir or default_docs_dir()
    documents: list[RenderedDocument] = []
    for filename in CORE_MARKDOWN_DOCS:
        path = docs_dir / filename
        if path.exists():
            body = path.read_text(encoding="utf-8")
        else:
            body = _fallback_document(filename)
        documents.append(
            RenderedDocument(
                path=filename,
                content=_with_frontmatter(config, filename, body, generated_at_utc),
                )
            )

    documents.append(
        RenderedDocument(
            path=GENERATED_PROFILE_DOC,
            content=_with_frontmatter(
                config,
                GENERATED_PROFILE_DOC,
                _deployment_profile(config),
                generated_at_utc,
            ),
        )
    )
    documents.append(RenderedDocument(path="REGISTER_OF_INFORMATION_FIELDS.csv", content=_roi_csv(config)))
    return documents


def _with_frontmatter(
    config: DoraConfig,
    filename: str,
    body: str,
    generated_at_utc: str,
) -> str:
    normalized_body = body.replace("\r\n", "\n").rstrip() + "\n"
    frontmatter = (
        "---\n"
        f"title: {filename}\n"
        "pack_type: dora_evidence_pack\n"
        f"deployment_id: {config.pack.deployment_id}\n"
        f"deployment_mode: {config.pack.deployment_mode.value}\n"
        f"cortex_version: {config.service.product_version}\n"
        f"generated_at_utc: {generated_at_utc}\n"
        "evidence_status: dora-supporting\n"
        "---\n\n"
    )
    return frontmatter + normalized_body


def _fallback_document(filename: str) -> str:
    return (
        f"# {filename}\n\n"
        "This generated document provides DORA-supporting evidence for the configured "
        "CORTEX deployment. It is not a certification, legal opinion, or substitute "
        "for the financial entity's own DORA obligations.\n"
    )


def _csv_cell(value: object) -> str:
    text = str(value).replace('"', '""')
    return f'"{text}"'


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def _list_text(values: list[str]) -> str:
    return ", ".join(values) if values else "none declared"


def _md_cell(value: object | None) -> str:
    if value is None or value == "":
        return "not declared"
    return str(value).replace("\n", " ").replace("|", "\\|")


def _md_table(headers: tuple[str, ...], rows: Sequence[Sequence[object | None]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(":---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(_md_cell(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def _deployment_profile(config: DoraConfig) -> str:
    service_rows: list[tuple[object | None, ...]] = [
        ("Provider legal name", config.service.legal_provider_name),
        ("Customer name", config.pack.customer_name),
        ("Deployment ID", config.pack.deployment_id),
        ("Deployment mode", config.pack.deployment_mode.value),
        ("Product version", config.service.product_version),
        ("Service description", config.service.service_description),
        ("Modules enabled", _list_text(config.service.modules_enabled)),
        ("Independent assurance available", _bool_text(config.service.independent_assurance_available)),
    ]

    data_rows: list[tuple[object | None, ...]] = [
        ("Telemetry enabled", _bool_text(config.data.telemetry_enabled)),
        ("External models enabled", _bool_text(config.data.external_models_enabled)),
        ("Personal data possible", _bool_text(config.data.personal_data_possible)),
        ("Confidential data possible", _bool_text(config.data.confidential_data_possible)),
        ("Key custody", config.data.key_custody),
        ("Encryption at rest", config.data.encryption_at_rest),
        ("Encryption in transit", config.data.encryption_in_transit),
    ]

    location_rows = [
        (location.category, location.country, location.owner, location.description)
        for location in config.locations
    ]
    support_rows: list[tuple[object | None, ...]] = [
        ("Enabled", _bool_text(config.support_access.enabled)),
        ("Countries", _list_text(config.support_access.countries)),
        ("Authorization required", _bool_text(config.support_access.authorization_required)),
        ("Logging enabled", _bool_text(config.support_access.logging_enabled)),
        ("Revocation supported", _bool_text(config.support_access.revocation_supported)),
    ]
    subprocessor_rows = [
        (
            subprocessor.name,
            subprocessor.service,
            _list_text(subprocessor.data_categories),
            _list_text(subprocessor.countries),
            subprocessor.materiality.value,
            subprocessor.customer_opt_out,
            _list_text([mode.value for mode in subprocessor.applies_to]),
        )
        for subprocessor in config.subprocessors
    ]
    model_provider_rows = [
        (
            provider.name,
            provider.service,
            _list_text(provider.data_sent),
            _list_text(provider.countries),
            provider.retention,
            _bool_text(provider.opt_out_available),
        )
        for provider in config.data.external_model_providers
    ]
    continuity_rows: list[tuple[object | None, ...]] = [
        ("RTO", config.continuity.rto),
        ("RPO", config.continuity.rpo),
        ("Backup responsibility", config.continuity.backup_responsibility),
        ("Restore responsibility", config.continuity.restore_responsibility),
        ("Restore test available", _bool_text(config.continuity.restore_test_available)),
        ("Exit plan available", _bool_text(config.continuity.exit_plan_available)),
        ("Key-loss procedure available", _bool_text(config.continuity.key_loss_procedure_available)),
    ]
    claim_rows = [
        (
            claim.id,
            claim.status.value,
            claim.owner,
            _list_text(claim.evidence_source),
            claim.verification_method,
            claim.limitation,
        )
        for claim in config.claims
    ]

    sections = [
        "# Deployment Profile",
        "This generated annex is derived from the validated source configuration.",
        "## Service",
        _md_table(("Field", "Value"), service_rows),
        "## Data Handling",
        _md_table(("Field", "Value"), data_rows),
        "## Locations",
        (
            _md_table(("Category", "Country", "Owner", "Description"), location_rows)
            if location_rows
            else "No locations are declared in the source configuration."
        ),
        "## Support Access",
        _md_table(("Field", "Value"), support_rows),
        "## Subprocessors",
        (
            _md_table(
                (
                    "Name",
                    "Service",
                    "Data categories",
                    "Countries",
                    "Materiality",
                    "Opt-out",
                    "Applies to",
                ),
                subprocessor_rows,
            )
            if subprocessor_rows
            else "The subprocessor register is empty for this deployment."
        ),
        "## External Model Providers",
        (
            _md_table(
                ("Name", "Service", "Data sent", "Countries", "Retention", "Opt-out"),
                model_provider_rows,
            )
            if model_provider_rows
            else "No external model providers are declared for this deployment."
        ),
        "## Continuity",
        _md_table(("Field", "Value"), continuity_rows),
        "## Evidence Claims",
        (
            _md_table(
                ("ID", "Status", "Owner", "Evidence source", "Verification", "Limitation"),
                claim_rows,
            )
            if claim_rows
            else "No evidence claims are declared for this deployment."
        ),
    ]
    return "\n\n".join(sections) + "\n"


def _roi_csv(config: DoraConfig) -> str:
    rows = [
        ("provider_legal_name", config.service.legal_provider_name),
        ("deployment_id", config.pack.deployment_id),
        ("deployment_mode", config.pack.deployment_mode.value),
        ("product_version", config.service.product_version),
        ("telemetry_enabled", config.data.telemetry_enabled),
        ("external_models_enabled", config.data.external_models_enabled),
        ("key_custody", config.data.key_custody),
        ("rto_profile", config.continuity.rto),
        ("rpo_profile", config.continuity.rpo),
        ("backup_responsibility", config.continuity.backup_responsibility),
        ("restore_responsibility", config.continuity.restore_responsibility),
        ("location_countries", ";".join(sorted({location.country for location in config.locations}))),
        ("location_categories", ";".join(sorted({location.category for location in config.locations}))),
        ("subprocessors", ";".join(sorted(subprocessor.name for subprocessor in config.subprocessors))),
        ("support_access_countries", ";".join(config.support_access.countries)),
        ("exit_plan_available", config.continuity.exit_plan_available),
    ]
    lines = ["field,value"]
    lines.extend(f"{_csv_cell(field)},{_csv_cell(value)}" for field, value in rows)
    return "\n".join(lines) + "\n"
