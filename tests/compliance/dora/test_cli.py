from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from cortex.cli.compliance_cmds import compliance_group
from cortex.compliance import ComplianceTracker
from cortex.compliance.dora import load_dora_config
from cortex.compliance.dora.export import export_dora_pack


EXAMPLE = "examples/compliance/dora.self-managed.yaml"


def _seed_pilot_ready_tracker(db_path: Path) -> None:
    tracker = ComplianceTracker(db_path=str(db_path), project="test-agent", tenant_id="tenant-alpha")
    try:
        decision_id = tracker.log_decision(
            content="Pilot readiness decision with human oversight.",
            agent_id="agent:risk",
            tenant_id="tenant-alpha",
        )
        tracker.log_human_oversight(
            decision_fact_id=decision_id,
            reviewer_id="human:reviewer-1",
            action="approved",
            tenant_id="tenant-alpha",
        )
    finally:
        tracker.close()


def test_cli_readiness_json_reports_pilot_and_production_gate(tmp_path: Path) -> None:
    db_path = tmp_path / "readiness.db"
    _seed_pilot_ready_tracker(db_path)

    result = CliRunner().invoke(
        compliance_group,
        [
            "readiness",
            "--db",
            str(db_path),
            "--project",
            "test-agent",
            "--tenant",
            "tenant-alpha",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["article_12_status"] == "COMPLIANT"
    assert payload["article_14_status"] == "COMPLIANT"
    assert payload["article_15_status"] == "PILOT_ONLY"
    assert payload["deployment_readiness"]["dora_article_28"]["status"] == "missing"
    assert payload["deployment_readiness"]["regulated_pilot"]["status"] == "READY_WITH_CONTROLS"
    assert payload["deployment_readiness"]["tier_1_bank_production"]["status"] == "NO_GO"


def test_cli_readiness_verifies_issued_dora_pack(tmp_path: Path) -> None:
    db_path = tmp_path / "readiness.db"
    pack_path = tmp_path / "issued-dora.zip"
    _seed_pilot_ready_tracker(db_path)
    base_config = load_dora_config("examples/compliance/dora.managed-private.yaml")
    config = base_config.model_copy(
        update={
            "service": base_config.service.model_copy(
                update={"independent_assurance_available": True}
            )
        }
    )
    export_dora_pack(config, pack_path, lifecycle_status="issued")

    result = CliRunner().invoke(
        compliance_group,
        [
            "readiness",
            "--db",
            str(db_path),
            "--project",
            "test-agent",
            "--tenant",
            "tenant-alpha",
            "--dora-pack",
            str(pack_path),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["deployment_readiness"]["dora_article_28"][
        "status"
    ] == "verified_issued"
    assert payload["deployment_readiness"]["tier_1_bank_production"]["status"] == "NO_GO"


def test_cli_readiness_require_modes(tmp_path: Path) -> None:
    db_path = tmp_path / "readiness.db"
    _seed_pilot_ready_tracker(db_path)
    runner = CliRunner()

    pilot_result = runner.invoke(
        compliance_group,
        [
            "readiness",
            "--db",
            str(db_path),
            "--project",
            "test-agent",
            "--tenant",
            "tenant-alpha",
            "--require",
            "pilot",
        ],
    )
    production_result = runner.invoke(
        compliance_group,
        [
            "readiness",
            "--db",
            str(db_path),
            "--project",
            "test-agent",
            "--tenant",
            "tenant-alpha",
            "--require",
            "production",
        ],
    )

    assert pilot_result.exit_code == 0, pilot_result.output
    assert production_result.exit_code == 1


def test_cli_claims_scan_fails_for_forbidden_claim(tmp_path: Path) -> None:
    claim_file = tmp_path / "claim.md"
    claim_file.write_text("This package is bank-production ready.\n", encoding="utf-8")

    result = CliRunner().invoke(
        compliance_group,
        ["claims", "scan", str(claim_file), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["findings"][0]["term"] == "bank-production ready"
    assert payload["findings"][0]["conditional"] is False


def test_cli_claims_scan_warns_for_conditional_claim(tmp_path: Path) -> None:
    claim_file = tmp_path / "claim.md"
    claim_file.write_text("This deployment is EU-only.\n", encoding="utf-8")

    result = CliRunner().invoke(compliance_group, ["claims", "scan", str(claim_file)])
    no_conditional_result = CliRunner().invoke(
        compliance_group,
        ["claims", "scan", str(claim_file), "--no-conditional"],
    )
    strict_result = CliRunner().invoke(
        compliance_group,
        ["claims", "scan", str(claim_file), "--strict-conditional"],
    )

    assert result.exit_code == 0
    assert "WARN EU-only" in result.output
    assert no_conditional_result.exit_code == 0
    assert "PASS CLAIM_POLICY" in no_conditional_result.output
    assert strict_result.exit_code == 1


def test_cli_export_and_verify(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "pack.zip"

    export_result = runner.invoke(
        compliance_group,
        ["dora", "export", "--config", EXAMPLE, "--output", str(output)],
    )

    assert export_result.exit_code == 0, export_result.output
    assert output.exists()

    verify_result = runner.invoke(compliance_group, ["dora", "verify", str(output)])

    assert verify_result.exit_code == 0, verify_result.output
    assert "PACK_DRAFT" in verify_result.output


def test_cli_validate_reports_warnings() -> None:
    runner = CliRunner()

    result = runner.invoke(compliance_group, ["dora", "validate", "--config", EXAMPLE])

    assert result.exit_code == 0
    assert "WARN RESTORE_TEST_MISSING" in result.output


def test_cli_validate_json_output() -> None:
    runner = CliRunner()

    result = runner.invoke(
        compliance_group,
        ["dora", "validate", "--config", EXAMPLE, "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"status": "ok"' in result.output
    assert '"code": "RESTORE_TEST_MISSING"' in result.output


def test_cli_verify_strict_fails_warnings(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "pack.zip"
    runner.invoke(compliance_group, ["dora", "export", "--config", EXAMPLE, "--output", str(output)])

    verify_result = runner.invoke(compliance_group, ["dora", "verify", str(output), "--strict"])

    assert verify_result.exit_code == 1
    assert "PACK_DRAFT" in verify_result.output


def test_cli_verify_json_output(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "pack.zip"
    runner.invoke(compliance_group, ["dora", "export", "--config", EXAMPLE, "--output", str(output)])

    verify_result = runner.invoke(
        compliance_group,
        ["dora", "verify", str(output), "--format", "json"],
    )

    assert verify_result.exit_code == 0
    assert '"status": "passed_with_warnings"' in verify_result.output
