"""CLI wrappers for compliance evidence operations."""

from __future__ import annotations

import json
from pathlib import Path

import click

from cortex.cli.common import cli, console
from cortex.config import DEFAULT_DB_PATH
from cortex.compliance import ComplianceTracker
from cortex.compliance.dora import (
    ValidationSeverity,
    export_dora_pack,
    load_dora_config,
    validate_dora_config,
    verify_dora_pack,
)
from cortex.compliance.dora.claim_policy import scan_file_for_claims


@click.group("compliance")
def compliance_group() -> None:
    """Compliance evidence operations."""


@compliance_group.command("readiness")
@click.option(
    "--db",
    "db_path",
    default=str(DEFAULT_DB_PATH),
    show_default=True,
    type=click.Path(dir_okay=False, path_type=str),
    help="CORTEX SQLite database path.",
)
@click.option("--project", default="default", show_default=True, help="Project scope.")
@click.option("--tenant", "tenant_id", default="default", show_default=True, help="Tenant scope.")
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(["text", "json"], case_sensitive=False),
)
@click.option(
    "--require",
    "require_mode",
    default="none",
    show_default=True,
    type=click.Choice(["none", "pilot", "production"], case_sensitive=False),
    help="Exit non-zero unless the selected deployment mode is ready.",
)
@click.option(
    "--dora-pack",
    "dora_pack_path",
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    help="Verified DORA evidence pack ZIP used for Article 28 production readiness.",
)
def readiness(
    db_path: str,
    project: str,
    tenant_id: str,
    output_format: str,
    require_mode: str,
    dora_pack_path: str | None,
) -> None:
    """Report regulated deployment readiness for a scoped compliance dataset."""

    dora_article_28_evidence = _verify_dora_article_28_pack(dora_pack_path)
    tracker = ComplianceTracker(db_path=db_path, project=project, tenant_id=tenant_id)
    try:
        report = tracker.export_audit(
            project=project,
            tenant_id=tenant_id,
            dora_article_28_evidence=dora_article_28_evidence,
        )
    except (OSError, TypeError, ValueError) as err:
        raise click.ClickException(str(err)) from err
    finally:
        tracker.close()

    related = report["eu_ai_act"].get("related_articles", {})
    readiness_report = report["deployment_readiness"]
    payload = {
        "project": report["project"],
        "tenant_id": report["tenant_id"],
        "article_12_status": report["eu_ai_act"]["status"],
        "article_14_status": related.get("14", {}).get("status", "UNKNOWN"),
        "article_15_status": related.get("15", {}).get("status", "UNKNOWN"),
        "deployment_readiness": readiness_report,
    }

    if output_format == "json":
        click.echo(json.dumps(payload, indent=2))
    else:
        console.print(f"Article 12: {payload['article_12_status']}")
        console.print(f"Article 14: {payload['article_14_status']}")
        console.print(f"Article 15: {payload['article_15_status']}")
        console.print(f"DORA Article 28: {readiness_report['dora_article_28']['status']}")
        console.print(
            "Regulated pilot: "
            f"{readiness_report['regulated_pilot']['status']}"
        )
        console.print(
            "Tier-1 bank production: "
            f"{readiness_report['tier_1_bank_production']['status']}"
        )
        for blocker in readiness_report["tier_1_bank_production"]["blockers"]:
            console.print(f"BLOCKER production: {blocker}")

    if require_mode == "pilot" and readiness_report["regulated_pilot"]["status"] != "READY_WITH_CONTROLS":
        raise click.exceptions.Exit(1)
    if require_mode == "production" and readiness_report["tier_1_bank_production"]["status"] != "GO":
        raise click.exceptions.Exit(1)


def _verify_dora_article_28_pack(pack_path: str | None) -> dict[str, object]:
    """Verify an optional DORA pack and return deployment-readiness evidence."""
    if not pack_path:
        return {"status": "missing"}
    result = verify_dora_pack(
        pack_path,
        strict=True,
        allow_sample=False,
        allow_draft=False,
    )
    return {
        "status": "verified_issued" if result.ok else "failed",
        "source": str(pack_path),
        "verification_status": result.status,
        "failed_checks": [
            check.code for check in result.checks if check.severity == "FAIL"
        ],
    }


@compliance_group.group("claims")
def claims_group() -> None:
    """Regulated wording claim-policy checks."""


@claims_group.command("scan")
@click.argument(
    "paths",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=str),
)
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(["text", "json"], case_sensitive=False),
)
@click.option(
    "--no-conditional",
    "exclude_conditional",
    is_flag=True,
    default=False,
    help="Ignore conditional claims such as EU-only or audit-ready.",
)
@click.option(
    "--strict-conditional",
    is_flag=True,
    help="Treat conditional claims as command failures.",
)
def claims_scan(
    paths: tuple[str, ...],
    output_format: str,
    exclude_conditional: bool,
    strict_conditional: bool,
) -> None:
    """Scan files for prohibited or conditional regulated claims."""

    findings = []
    include_conditional = not exclude_conditional
    for raw_path in paths:
        try:
            findings.extend(
                scan_file_for_claims(raw_path, include_conditional=include_conditional)
            )
        except (OSError, UnicodeDecodeError) as err:
            raise click.ClickException(str(err)) from err

    payload = [
        {
            "path": str(finding.path) if finding.path else None,
            "line": finding.line,
            "term": finding.term,
            "conditional": finding.conditional,
            "text": finding.text,
        }
        for finding in findings
    ]
    if output_format == "json":
        click.echo(json.dumps({"findings": payload}, indent=2))
    elif not findings:
        console.print("PASS CLAIM_POLICY: no findings")
    else:
        for finding in findings:
            severity = "WARN" if finding.conditional else "FAIL"
            console.print(
                f"{severity} {finding.term}: {finding.path}:{finding.line}: "
                f"{finding.text}"
            )

    has_forbidden = any(not finding.conditional for finding in findings)
    has_strict_conditional = strict_conditional and any(finding.conditional for finding in findings)
    if has_forbidden or has_strict_conditional:
        raise click.exceptions.Exit(1)


@compliance_group.group("dora")
def dora_group() -> None:
    """DORA evidence-pack export and verification."""


@dora_group.command("export")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    help="DORA YAML config path.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, path_type=str),
    help="Output ZIP path.",
)
@click.option(
    "--lifecycle-status",
    default="draft",
    show_default=True,
    type=click.Choice(["sample", "draft", "issued"], case_sensitive=False),
    help="Evidence pack lifecycle state.",
)
def dora_export(config_path: str, output_path: str, lifecycle_status: str) -> None:
    """Export a DORA evidence pack ZIP."""

    try:
        config = load_dora_config(config_path)
        pack = export_dora_pack(config, Path(output_path), lifecycle_status=lifecycle_status)
    except (OSError, TypeError, ValueError) as err:
        raise click.ClickException(str(err)) from err

    console.print(f"Exported DORA evidence pack: {output_path}")
    console.print(f"pack_sha256: {pack.manifest.pack_sha256}")
    console.print(f"validation: {pack.manifest.validation.status}")


@dora_group.command("validate")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    help="DORA YAML config path.",
)
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(["text", "json"], case_sensitive=False),
)
def dora_validate(config_path: str, output_format: str) -> None:
    """Validate a DORA evidence-pack YAML config."""

    try:
        config = load_dora_config(config_path)
    except (OSError, TypeError, ValueError) as err:
        raise click.ClickException(str(err)) from err

    issues = validate_dora_config(config)
    if output_format == "json":
        payload = {
            "status": "failed" if any(issue.severity == ValidationSeverity.ERROR for issue in issues) else "ok",
            "issues": [issue.model_dump(mode="json") for issue in issues],
        }
        console.print(json.dumps(payload, indent=2))
    elif not issues:
        console.print("PASS DORA_CONFIG_VALID: no validation issues")
    else:
        for issue in issues:
            suffix = f" [{issue.affected_document}]" if issue.affected_document else ""
            console.print(f"{issue.severity.value} {issue.code}: {issue.message} [{issue.path}]{suffix}")

    if any(issue.severity == ValidationSeverity.ERROR for issue in issues):
        raise click.exceptions.Exit(1)


@dora_group.command("verify")
@click.argument("pack_path", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option("--strict", is_flag=True, help="Treat warnings as failures.")
@click.option("--allow-sample", is_flag=True, help="Permit sample lifecycle packs.")
@click.option("--no-allow-draft", is_flag=True, help="Fail draft lifecycle packs.")
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(["text", "json"], case_sensitive=False),
)
def dora_verify(
    pack_path: str,
    strict: bool,
    allow_sample: bool,
    no_allow_draft: bool,
    output_format: str,
) -> None:
    """Verify a DORA evidence pack ZIP."""

    result = verify_dora_pack(
        pack_path,
        strict=strict,
        allow_sample=allow_sample,
        allow_draft=not no_allow_draft,
    )
    if output_format == "json":
        console.print(json.dumps(result.to_dict(), indent=2))
    else:
        for check in result.checks:
            suffix = f" [{check.path}]" if check.path else ""
            console.print(f"{check.severity} {check.code}: {check.message}{suffix}")

    if not result.ok:
        raise click.exceptions.Exit(1)


cli.add_command(compliance_group)
