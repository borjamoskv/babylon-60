from __future__ import annotations

from click.testing import CliRunner

from cortex.cli import cli
from cortex.engine import CortexEngine


def test_compliance_report_uses_technical_alignment_language(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cortex.utils.landauer.audit_calcification", lambda *_args, **_kwargs: [])

    db_path = tmp_path / "compliance-report.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    try:
        engine.init_db_sync()
        engine.store_sync(
            "diligence",
            "Decision captured for technical diligence",
            fact_type="decision",
            source="agent:test",
            tags=["agent:test"],
        )
    finally:
        engine.close_sync()

    result = CliRunner().invoke(cli, ["compliance-report", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Assessment" in result.output
    assert "Compliance Score" in result.output
    assert "All Article 12 requirements met" not in result.output
