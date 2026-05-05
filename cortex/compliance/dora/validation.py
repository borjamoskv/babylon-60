"""Validation rules for DORA evidence-pack configuration."""

from __future__ import annotations

from pathlib import Path

from cortex.compliance.dora.models import (
    Claim,
    ContinuityConfig,
    DeploymentMode,
    DoraConfig,
    EvidenceStatus,
    Materiality,
    Subprocessor,
    ValidationIssue,
    ValidationSeverity,
    read_yaml_mapping,
)


_CONCRETE_RTO_RPO_DISALLOWED = {"customer-defined", "customer defined", "tbd", ""}
_HIGH_MATERIALITY = {Materiality.HIGH, Materiality.CRITICAL}


def load_dora_config(path: str | Path) -> DoraConfig:
    """Load and validate a DORA YAML config with Pydantic structure checks."""

    config_path = Path(path)
    return DoraConfig.model_validate(read_yaml_mapping(config_path))


def validate_dora_config(config: DoraConfig) -> list[ValidationIssue]:
    """Run cross-field DORA evidence validation rules."""

    issues: list[ValidationIssue] = []
    _validate_managed_rto_rpo(config, issues)
    _validate_external_models(config, issues)
    _validate_support_access(config, issues)
    _validate_locations(config, issues)
    _validate_subprocessors(config.subprocessors, issues)
    _validate_claims(config.claims, issues)
    _validate_continuity(config.continuity, config.pack.deployment_mode, issues)
    _validate_warnings(config, issues)
    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    """Return true when validation issues contain at least one error."""

    return any(issue.severity == ValidationSeverity.ERROR for issue in issues)


def _issue(
    issues: list[ValidationIssue],
    severity: ValidationSeverity,
    code: str,
    message: str,
    path: str,
    affected_document: str | None = None,
) -> None:
    issues.append(
        ValidationIssue(
            severity=severity,
            code=code,
            message=message,
            path=path,
            affected_document=affected_document,
        )
    )


def _validate_managed_rto_rpo(config: DoraConfig, issues: list[ValidationIssue]) -> None:
    if config.pack.deployment_mode not in {DeploymentMode.MANAGED_PRIVATE, DeploymentMode.HOSTED}:
        return

    for field_name, value in {
        "rto": config.continuity.rto,
        "rpo": config.continuity.rpo,
    }.items():
        if value.strip().lower() in _CONCRETE_RTO_RPO_DISALLOWED:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "MANAGED_RTO_RPO_NOT_CONCRETE",
                "Managed private and hosted deployments require concrete RTO/RPO values.",
                f"continuity.{field_name}",
                "BUSINESS_CONTINUITY_STATEMENT.md",
            )


def _validate_external_models(config: DoraConfig, issues: list[ValidationIssue]) -> None:
    if not config.data.external_models_enabled:
        return

    providers = config.data.external_model_providers
    if not providers:
        _issue(
            issues,
            ValidationSeverity.ERROR,
            "EXTERNAL_MODEL_PROVIDER_MISSING",
            "External model usage requires at least one provider declaration.",
            "data.external_model_providers",
            "AI_MODEL_DEPENDENCY_STATEMENT.md",
        )
        return

    for index, provider in enumerate(providers):
        base_path = f"data.external_model_providers[{index}]"
        if not provider.data_sent:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "EXTERNAL_MODEL_DATA_MISSING",
                "External model providers require declared data categories.",
                f"{base_path}.data_sent",
                "AI_MODEL_DEPENDENCY_STATEMENT.md",
            )
        if not provider.countries:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "EXTERNAL_MODEL_COUNTRIES_MISSING",
                "External model providers require processing countries.",
                f"{base_path}.countries",
                "DATA_LOCATION_STATEMENT.md",
            )
        if not provider.retention:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "EXTERNAL_MODEL_RETENTION_MISSING",
                "External model providers require retention details.",
                f"{base_path}.retention",
                "AI_MODEL_DEPENDENCY_STATEMENT.md",
            )


def _validate_support_access(config: DoraConfig, issues: list[ValidationIssue]) -> None:
    support = config.support_access
    if not support.enabled:
        return

    if not support.countries:
        _issue(
            issues,
            ValidationSeverity.ERROR,
            "SUPPORT_COUNTRIES_MISSING",
            "Enabled support access requires declared support countries.",
            "support_access.countries",
            "DATA_LOCATION_STATEMENT.md",
        )
    for field_name in ("authorization_required", "logging_enabled", "revocation_supported"):
        if not getattr(support, field_name):
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "SUPPORT_ACCESS_CONTROL_MISSING",
                "Enabled support access requires authorization, logging, and revocation.",
                f"support_access.{field_name}",
                "SUPPORT_ACCESS_POLICY.md",
            )


def _validate_locations(config: DoraConfig, issues: list[ValidationIssue]) -> None:
    if config.locations:
        return

    severity = ValidationSeverity.WARN
    if config.pack.deployment_mode in {DeploymentMode.MANAGED_PRIVATE, DeploymentMode.HOSTED}:
        severity = ValidationSeverity.ERROR

    _issue(
        issues,
        severity,
        "LOCATION_DECLARATION_MISSING",
        "Deployment evidence requires at least one declared processing or storage location.",
        "locations",
        "DATA_LOCATION_STATEMENT.md",
    )


def _validate_subprocessors(
    subprocessors: list[Subprocessor], issues: list[ValidationIssue]
) -> None:
    for index, subprocessor in enumerate(subprocessors):
        if subprocessor.materiality not in _HIGH_MATERIALITY:
            continue
        base_path = f"subprocessors[{index}]"
        if not subprocessor.countries:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "MATERIAL_SUBPROCESSOR_COUNTRIES_MISSING",
                "High or critical subprocessors require processing countries.",
                f"{base_path}.countries",
                "SUBPROCESSOR_REGISTER.md",
            )
        if not subprocessor.data_categories:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "MATERIAL_SUBPROCESSOR_DATA_MISSING",
                "High or critical subprocessors require data categories.",
                f"{base_path}.data_categories",
                "SUBPROCESSOR_REGISTER.md",
            )

        if "partial" in subprocessor.customer_opt_out.lower():
            _issue(
                issues,
                ValidationSeverity.WARN,
                "SUBPROCESSOR_OPT_OUT_PARTIAL",
                "Subprocessor opt-out is partial and should be reviewed.",
                f"{base_path}.customer_opt_out",
                "SUBPROCESSOR_REGISTER.md",
            )


def _validate_claims(claims: list[Claim], issues: list[ValidationIssue]) -> None:
    for index, claim in enumerate(claims):
        if claim.status != EvidenceStatus.IMPLEMENTED:
            continue
        base_path = f"claims[{index}]"
        if not claim.evidence_source:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "IMPLEMENTED_CLAIM_EVIDENCE_MISSING",
                "Implemented claims require evidence sources.",
                f"{base_path}.evidence_source",
                "CONTROL_MATRIX.md",
            )
        if not claim.verification_method:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "IMPLEMENTED_CLAIM_VERIFICATION_MISSING",
                "Implemented claims require a verification method.",
                f"{base_path}.verification_method",
                "CONTROL_MATRIX.md",
            )


def _validate_continuity(
    continuity: ContinuityConfig,
    deployment_mode: DeploymentMode,
    issues: list[ValidationIssue],
) -> None:
    if deployment_mode in {DeploymentMode.MANAGED_PRIVATE, DeploymentMode.HOSTED}:
        if not continuity.exit_plan_available:
            _issue(
                issues,
                ValidationSeverity.ERROR,
                "EXIT_PLAN_MISSING_FOR_MANAGED",
                "Managed private and hosted deployments require an exit plan.",
                "continuity.exit_plan_available",
                "EXIT_PLAN.md",
            )


def _validate_warnings(config: DoraConfig, issues: list[ValidationIssue]) -> None:
    if not config.continuity.restore_test_available:
        _issue(
            issues,
            ValidationSeverity.WARN,
            "RESTORE_TEST_MISSING",
            "No restore test evidence is declared.",
            "continuity.restore_test_available",
            "BUSINESS_CONTINUITY_STATEMENT.md",
        )

    if not config.service.independent_assurance_available:
        _issue(
            issues,
            ValidationSeverity.WARN,
            "INDEPENDENT_ASSURANCE_MISSING",
            "No independent assurance report is declared.",
            "service.independent_assurance_available",
            "ASSURANCE_ROADMAP.md",
        )

    if config.data.key_custody.strip().lower() == "customer":
        if not config.continuity.key_loss_procedure_available:
            _issue(
                issues,
                ValidationSeverity.WARN,
                "KEY_LOSS_PROCEDURE_MISSING",
                "Customer-held keys are declared but no key-loss procedure is available.",
                "continuity.key_loss_procedure_available",
                "KEY_MANAGEMENT_STATEMENT.md",
            )
