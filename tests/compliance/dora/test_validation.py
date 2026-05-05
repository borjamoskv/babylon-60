from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cortex.compliance.dora import (
    DoraConfig,
    ValidationSeverity,
    load_dora_config,
    validate_dora_config,
)


EXAMPLES = Path("examples/compliance")


def _codes(config: DoraConfig) -> set[str]:
    return {issue.code for issue in validate_dora_config(config)}


def test_example_self_managed_loads_with_expected_warnings() -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")

    issues = validate_dora_config(config)
    assert {issue.severity for issue in issues} == {ValidationSeverity.WARN}
    assert "RESTORE_TEST_MISSING" in {issue.code for issue in issues}


def test_example_managed_private_loads_without_errors() -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")

    assert all(issue.severity != ValidationSeverity.ERROR for issue in validate_dora_config(config))


def test_example_hosted_loads_without_errors() -> None:
    config = load_dora_config(EXAMPLES / "dora.hosted.yaml")

    assert all(issue.severity != ValidationSeverity.ERROR for issue in validate_dora_config(config))


def test_missing_deployment_mode_is_structural_error() -> None:
    payload = {
        "pack": {"deployment_id": "missing-mode"},
        "service": {"legal_provider_name": "CORTEX", "product_version": "0"},
        "data": {},
        "continuity": {
            "rto": "customer-defined",
            "rpo": "customer-defined",
            "backup_responsibility": "customer",
            "restore_responsibility": "customer",
        },
    }

    with pytest.raises(ValidationError):
        DoraConfig.model_validate(payload)


def test_high_material_subprocessor_requires_country_and_data() -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    config.subprocessors[0].countries = []
    config.subprocessors[0].data_categories = []

    codes = _codes(config)

    assert "MATERIAL_SUBPROCESSOR_COUNTRIES_MISSING" in codes
    assert "MATERIAL_SUBPROCESSOR_DATA_MISSING" in codes


def test_hosted_rto_rpo_must_be_concrete() -> None:
    config = load_dora_config(EXAMPLES / "dora.hosted.yaml")
    config.continuity.rto = "customer-defined"
    config.continuity.rpo = "customer-defined"

    assert "MANAGED_RTO_RPO_NOT_CONCRETE" in _codes(config)


def test_external_model_usage_requires_provider() -> None:
    config = load_dora_config(EXAMPLES / "dora.hosted.yaml")
    config.data.external_model_providers = []

    assert "EXTERNAL_MODEL_PROVIDER_MISSING" in _codes(config)


def test_support_access_requires_controls() -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    config.support_access.countries = []
    config.support_access.authorization_required = False
    config.support_access.logging_enabled = False
    config.support_access.revocation_supported = False

    codes = _codes(config)

    assert "SUPPORT_COUNTRIES_MISSING" in codes
    assert "SUPPORT_ACCESS_CONTROL_MISSING" in codes


def test_managed_deployment_requires_location_declaration() -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    config.locations = []

    issues = validate_dora_config(config)

    assert any(
        issue.code == "LOCATION_DECLARATION_MISSING"
        and issue.severity == ValidationSeverity.ERROR
        for issue in issues
    )


def test_implemented_claim_requires_evidence_and_verification() -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")
    config.claims[0].status = "implemented"  # type: ignore[assignment]
    config.claims[0].evidence_source = []
    config.claims[0].verification_method = None

    codes = _codes(config)

    assert "IMPLEMENTED_CLAIM_EVIDENCE_MISSING" in codes
    assert "IMPLEMENTED_CLAIM_VERIFICATION_MISSING" in codes
