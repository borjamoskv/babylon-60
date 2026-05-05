from __future__ import annotations

import json
import zipfile
from pathlib import Path

from cortex.compliance.dora import load_dora_config
from cortex.compliance.dora.export import export_dora_pack
from cortex.compliance.dora.render import render_evidence_pack
from cortex.compliance.dora.verify import verify_dora_pack


EXAMPLES = Path("examples/compliance")
FIXED_TIME = "2026-05-05T10:00:00Z"


def test_render_outputs_documents_and_manifest() -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")

    pack = render_evidence_pack(config, generated_at_utc=FIXED_TIME)

    paths = {document.path for document in pack.documents}
    assert "CONTROL_MATRIX.md" in paths
    assert "DEPLOYMENT_PROFILE.md" in paths
    assert "REGISTER_OF_INFORMATION_FIELDS.csv" in paths
    assert pack.manifest.deployment_id == "example-self-managed"
    assert pack.manifest.pack_sha256 is not None


def test_rendered_profile_contains_configured_locations_and_subprocessors() -> None:
    config = load_dora_config(EXAMPLES / "dora.hosted.yaml")

    pack = render_evidence_pack(config, generated_at_utc=FIXED_TIME)
    profile = next(document.content for document in pack.documents if document.path == "DEPLOYMENT_PROFILE.md")

    assert "hosted_runtime" in profile
    assert "Example Hosted Platform" in profile
    assert "Example Model Provider" in profile


def test_source_config_hash_is_stable() -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")

    first = render_evidence_pack(config, generated_at_utc=FIXED_TIME)
    second = render_evidence_pack(config, generated_at_utc=FIXED_TIME)

    assert first.manifest.source_config_hash == second.manifest.source_config_hash
    assert first.manifest.pack_sha256 == second.manifest.pack_sha256


def test_export_zip_and_verify_with_warnings(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")
    output = tmp_path / "pack.zip"

    export_dora_pack(config, output)
    result = verify_dora_pack(output)

    assert result.ok
    assert result.status == "passed_with_warnings"
    assert any(check.code == "PACK_DRAFT" for check in result.checks)
    assert any(check.code == "RESTORE_TEST_MISSING" for check in result.checks)


def test_export_issued_pack_fails_when_validation_has_warnings(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")
    output = tmp_path / "issued.zip"

    try:
        export_dora_pack(config, output, lifecycle_status="issued")
    except ValueError as exc:
        assert "cannot be issued with validation warnings" in str(exc)
        assert "RESTORE_TEST_MISSING" in str(exc)
    else:
        raise AssertionError("issued pack export should fail when warnings remain")
    assert not output.exists()


def test_export_issued_pack_succeeds_without_validation_warnings(tmp_path: Path) -> None:
    base_config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    config = base_config.model_copy(
        update={
            "service": base_config.service.model_copy(
                update={"independent_assurance_available": True}
            )
        }
    )
    output = tmp_path / "issued.zip"

    pack = export_dora_pack(config, output, lifecycle_status="issued")
    result = verify_dora_pack(output, strict=True, allow_draft=False)

    assert output.exists()
    assert pack.manifest.lifecycle_status == "issued"
    assert result.ok
    assert result.status == "passed"


def test_verify_strict_fails_warnings(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.self-managed.yaml")
    output = tmp_path / "pack.zip"

    export_dora_pack(config, output)
    result = verify_dora_pack(output, strict=True)

    assert not result.ok
    assert any(check.code == "PACK_DRAFT" for check in result.checks)


def test_verify_rejects_expired_lifecycle_even_before_valid_until(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    output = tmp_path / "pack.zip"
    expired = tmp_path / "expired.zip"
    export_dora_pack(config, output)

    with zipfile.ZipFile(output) as source, zipfile.ZipFile(expired, "w") as dest:
        for name in source.namelist():
            data = source.read(name)
            if name == "manifest.json":
                payload = json.loads(data)
                payload["lifecycle_status"] = "expired"
                data = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
            dest.writestr(name, data)

    result = verify_dora_pack(expired)

    assert not result.ok
    assert any(check.code == "PACK_NOT_USABLE" for check in result.checks)


def test_verify_detects_tampered_document(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    output = tmp_path / "pack.zip"
    tampered = tmp_path / "tampered.zip"
    export_dora_pack(config, output)

    with zipfile.ZipFile(output) as source, zipfile.ZipFile(tampered, "w") as dest:
        for name in source.namelist():
            data = source.read(name)
            if name == "CONTROL_MATRIX.md":
                data += b"\nTampered.\n"
            dest.writestr(name, data)

    result = verify_dora_pack(tampered)

    assert not result.ok
    assert any(check.code == "DOCUMENT_HASH_MISMATCH" for check in result.checks)


def test_verify_detects_manifest_pack_hash_tamper(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    output = tmp_path / "pack.zip"
    tampered = tmp_path / "tampered.zip"
    export_dora_pack(config, output)

    with zipfile.ZipFile(output) as source, zipfile.ZipFile(tampered, "w") as dest:
        for name in source.namelist():
            data = source.read(name)
            if name == "manifest.json":
                payload = json.loads(data)
                payload["documents"][0]["sha256"] = "sha256:" + "0" * 64
                data = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
            dest.writestr(name, data)

    result = verify_dora_pack(tampered)

    assert not result.ok
    assert any(check.code == "PACK_HASH_MISMATCH" for check in result.checks)


def test_verify_detects_forbidden_claim_in_document(tmp_path: Path) -> None:
    config = load_dora_config(EXAMPLES / "dora.managed-private.yaml")
    output = tmp_path / "pack.zip"
    tampered = tmp_path / "tampered.zip"
    export_dora_pack(config, output)

    with zipfile.ZipFile(output) as source, zipfile.ZipFile(tampered, "w") as dest:
        for name in source.namelist():
            data = source.read(name)
            if name == "CONTROL_MATRIX.md":
                data += b"\nCORTEX is DORA compliant.\n"
            dest.writestr(name, data)

    result = verify_dora_pack(tampered)

    assert not result.ok
    assert any(check.code == "CLAIM_POLICY_MATCH" for check in result.checks)
