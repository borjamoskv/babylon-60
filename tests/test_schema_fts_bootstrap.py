from __future__ import annotations

from cortex.database.schema import get_all_schema


def test_base_schema_does_not_bootstrap_facts_fts_triggers() -> None:
    statements = "\n".join(get_all_schema())

    assert "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts" in statements
    assert "CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts" not in statements
    assert "CREATE TRIGGER IF NOT EXISTS facts_au" not in statements
    assert "CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts" not in statements
