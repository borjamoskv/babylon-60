import sqlite3
from pathlib import Path

from click.testing import CliRunner

from cortex.cli.main import cli


def test_operations_doc_uses_current_cli_contract() -> None:
    doc = Path("docs/OPERATIONS.md").read_text(encoding="utf-8")

    assert 'cortex store PROJECT "content" --type decision --source agent:gemini' in doc
    assert 'cortex search "query" -k 10' in doc
    assert "cortex ledger verify" in doc
    assert "cortex verify 42" in doc
    assert "cortex export --format snapshot" in doc
    assert "CORTEX_MASTER_KEY" in doc
    assert "CORTEX_ENCRYPTION_KEY" not in doc
    assert "cortex reindex" not in doc


def test_cli_reference_audit_trail_command_matches_entrypoint(tmp_path: Path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "cortex.db"
    doc = Path("docs/cli.md").read_text(encoding="utf-8")

    assert "### `cortex audit-trail`" in doc
    assert "cortex audit-trail [--project PROJECT] [--limit N]" in doc

    init_result = runner.invoke(cli, ["init", "--db", str(db_path)])
    assert init_result.exit_code == 0, init_result.output

    store_result = runner.invoke(
        cli,
        [
            "store",
            "fraud-ops",
            "Approved transfer after MFA verification",
            "--source",
            "agent:risk-bot",
            "--db",
            str(db_path),
        ],
    )
    assert store_result.exit_code == 0, store_result.output

    audit_trail_help = runner.invoke(cli, ["audit-trail", "--help"])
    assert audit_trail_help.exit_code == 0, audit_trail_help.output
    assert "--project" in audit_trail_help.output
    assert "--limit" in audit_trail_help.output

    audit_trail_result = runner.invoke(
        cli,
        ["audit-trail", "--project", "fraud-ops", "--db", str(db_path)],
    )
    assert audit_trail_result.exit_code == 0, audit_trail_result.output
    assert "fraud-ops" in audit_trail_result.output


def test_trust_and_vote_ledgers_have_distinct_cli_surfaces(tmp_path: Path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "cortex.db"

    ledger_help = runner.invoke(cli, ["ledger", "--help"])
    assert ledger_help.exit_code == 0, ledger_help.output
    assert "Sovereign Ledger Operations" in ledger_help.output
    assert "registro inmutable de votos" not in ledger_help.output

    vote_ledger_help = runner.invoke(cli, ["vote-ledger", "--help"])
    assert vote_ledger_help.exit_code == 0, vote_ledger_help.output
    assert "registro inmutable de votos" in vote_ledger_help.output

    init_result = runner.invoke(cli, ["init", "--db", str(db_path)])
    assert init_result.exit_code == 0, init_result.output

    store_result = runner.invoke(
        cli,
        [
            "store",
            "fraud-ops",
            "Transaction flagged: IP mismatch",
            "--source",
            "agent:risk-bot",
            "--db",
            str(db_path),
        ],
    )
    assert store_result.exit_code == 0, store_result.output

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM facts WHERE project = ? ORDER BY id DESC LIMIT 1",
            ("fraud-ops",),
        ).fetchone()
    assert row is not None
    fact_id = row[0]

    vote_result = runner.invoke(
        cli,
        ["vote", str(fact_id), "1", "--agent", "agent:claude", "--db", str(db_path)],
    )
    assert vote_result.exit_code == 0, vote_result.output
    assert "votó 1" in vote_result.output

    vote_ledger_verify = runner.invoke(cli, ["vote-ledger", "verify", "--db", str(db_path)])
    assert vote_ledger_verify.exit_code == 0, vote_ledger_verify.output
    assert "Integridad de Cadena de Hashes: OK" in vote_ledger_verify.output
