from __future__ import annotations

import sqlite3

from cortex.profile_agent import (
    LedgerProjection,
    ProfileProjection,
    public_status_digest,
    render_public_block,
    render_status_json,
    render_status_svg,
    replace_managed_block,
    verify_transaction_chain,
    write_status_json,
    write_status_svg,
)
from cortex.utils.canonical import compute_tx_hash


def test_replace_managed_block_appends_when_missing() -> None:
    updated = replace_managed_block("# Borja\n", "managed")

    assert "<!-- CORTEX-PROFILE-AGENT:START -->" in updated
    assert "managed" in updated
    assert updated.startswith("# Borja\n")


def test_replace_managed_block_replaces_existing_block_only() -> None:
    original = "\n".join(
        [
            "# Borja",
            "",
            "<!-- CORTEX-PROFILE-AGENT:START -->",
            "old",
            "<!-- CORTEX-PROFILE-AGENT:END -->",
            "",
            "tail",
        ]
    )

    updated = replace_managed_block(original, "new")

    assert "old" not in updated
    assert "new" in updated
    assert updated.endswith("\ntail")


def test_render_public_block_does_not_include_raw_memory() -> None:
    projection = ProfileProjection(
        agent_id="cortex-profile-agent",
        generated_at="2026-05-06T10:00:00Z",
        profile_repo="borjamoskv/borjamoskv",
        source_repo="borjamoskv/Cortex-Persist",
        project="github-profile-agent",
        tenant_id="public-profile",
        fact_id=42,
        ledger=LedgerProjection(valid=True, tx_checked=7, latest_hash="a" * 64),
        profile_commit="b" * 40,
    )

    rendered = render_public_block(projection)

    assert "CORTEX Live Agent Surface" in rendered
    assert 'src="assets/cortex-profile-agent.svg"' in rendered
    assert "img.shields.io/badge/ledger-verified" in rendered
    assert "Wake -> Guard -> Store -> Hash -> Verify -> Project" in rendered
    assert "<summary>Public evidence packet</summary>" in rendered
    assert "`VALID`" in rendered
    assert "Public digest" in rendered
    assert "assets/cortex-profile-agent.status.json" in rendered
    assert "#42" in rendered
    assert "Raw memory" in rendered
    assert "secret-value" not in rendered


def test_render_status_json_is_public_contract() -> None:
    projection = ProfileProjection(
        agent_id="cortex-profile-agent",
        generated_at="2026-05-06T10:00:00Z",
        profile_repo="borjamoskv/borjamoskv",
        source_repo="borjamoskv/Cortex-Persist",
        project="github-profile-agent",
        tenant_id="public-profile",
        fact_id=42,
        ledger=LedgerProjection(valid=True, tx_checked=7, latest_hash="a" * 64),
        profile_commit="b" * 40,
    )

    rendered = render_status_json(projection)
    digest = public_status_digest(projection)

    assert '"schema_version": 1' in rendered
    assert '"memory_admission": "CortexEngine.store"' in rendered
    assert '"raw_memory_published": false' in rendered
    assert '"secrets_published": false' in rendered
    assert len(digest) == 64
    assert "secret-value" not in rendered


def test_render_status_svg_is_static_and_redacted() -> None:
    projection = ProfileProjection(
        agent_id='cortex-profile-agent"><script>alert(1)</script>',
        generated_at="2026-05-06T10:00:00Z",
        profile_repo="borjamoskv/borjamoskv",
        source_repo="borjamoskv/Cortex-Persist",
        project="github-profile-agent",
        tenant_id="public-profile",
        fact_id=42,
        ledger=LedgerProjection(valid=True, tx_checked=7, latest_hash="a" * 64),
        profile_commit="b" * 40,
    )

    rendered = render_status_svg(projection)

    assert rendered.startswith("<svg ")
    assert "<script" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "CORTEX LIVE SURFACE" in rendered
    assert "anchor aaaaaaaaaaaaaaaaaa" in rendered
    assert "digest " in rendered
    assert "raw memory, prompts, tenant payloads, and secrets are not published" in rendered
    assert "secret-value" not in rendered


def test_write_status_assets_create_profile_artifacts(tmp_path) -> None:
    projection = ProfileProjection(
        agent_id="cortex-profile-agent",
        generated_at="2026-05-06T10:00:00Z",
        profile_repo="borjamoskv/borjamoskv",
        source_repo="borjamoskv/Cortex-Persist",
        project="github-profile-agent",
        tenant_id="public-profile",
        fact_id=42,
        ledger=LedgerProjection(valid=True, tx_checked=7, latest_hash="a" * 64),
        profile_commit="b" * 40,
    )

    output_path = write_status_svg(tmp_path, projection)
    json_path = write_status_json(tmp_path, projection)

    assert output_path == tmp_path / "assets" / "cortex-profile-agent.svg"
    assert output_path.exists()
    assert "CORTEX LIVE SURFACE" in output_path.read_text(encoding="utf-8")
    assert json_path == tmp_path / "assets" / "cortex-profile-agent.status.json"
    assert json_path.exists()
    assert '"public_projection_only": true' in json_path.read_text(encoding="utf-8")


def test_verify_transaction_chain_accepts_valid_tenant_chain(tmp_path) -> None:
    db_path = tmp_path / "cortex.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE transactions ("
            "id INTEGER PRIMARY KEY, tenant_id TEXT, project TEXT, action TEXT, "
            "detail TEXT, prev_hash TEXT, hash TEXT, timestamp TEXT)"
        )
        prev = "GENESIS"
        for idx in range(2):
            timestamp = f"2026-05-06T10:00:0{idx}Z"
            detail = '{"fact_type":"bridge"}'
            tx_hash = compute_tx_hash(
                prev,
                "github-profile-agent",
                "store",
                detail,
                timestamp,
                tenant_id="public-profile",
            )
            conn.execute(
                "INSERT INTO transactions "
                "(tenant_id, project, action, detail, prev_hash, hash, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "public-profile",
                    "github-profile-agent",
                    "store",
                    detail,
                    prev,
                    tx_hash,
                    timestamp,
                ),
            )
            prev = tx_hash
        conn.commit()
    finally:
        conn.close()

    projection = verify_transaction_chain(db_path, tenant_id="public-profile")

    assert projection.valid is True
    assert projection.tx_checked == 2
    assert projection.latest_hash == prev


def test_verify_transaction_chain_reports_tamper(tmp_path) -> None:
    db_path = tmp_path / "cortex.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE transactions ("
            "id INTEGER PRIMARY KEY, tenant_id TEXT, project TEXT, action TEXT, "
            "detail TEXT, prev_hash TEXT, hash TEXT, timestamp TEXT)"
        )
        conn.execute(
            "INSERT INTO transactions "
            "(tenant_id, project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "public-profile",
                "github-profile-agent",
                "store",
                '{"fact_type":"bridge"}',
                "GENESIS",
                "bad-hash",
                "2026-05-06T10:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    projection = verify_transaction_chain(db_path, tenant_id="public-profile")

    assert projection.valid is False
    assert projection.tx_checked == 1
    assert projection.violations == ("TAMPER_DETECTED tx=1",)
