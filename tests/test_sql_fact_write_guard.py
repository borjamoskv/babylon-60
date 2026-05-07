from __future__ import annotations

import pytest

from cortex.database.sql_guard import reject_protected_fact_table_dml


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO facts (content) VALUES (?)",
        "INSERT OR REPLACE INTO main.facts (id, content) VALUES (?, ?)",
        'UPDATE "facts" SET content = ? WHERE id = ?',
        "DELETE FROM `facts` WHERE id = ?",
        "INSERT INTO facts_fts (rowid, content) VALUES (?, ?)",
        "INSERT INTO fact_tags (fact_id, tag) VALUES (?, ?)",
        "DELETE FROM causal_edges WHERE fact_id = ?",
        "WITH stale AS (SELECT 1) DELETE FROM facts WHERE id = ?",
    ],
)
def test_reject_protected_fact_table_dml_blocks_fact_owned_mutations(sql: str) -> None:
    with pytest.raises(ValueError, match="Direct mutations on fact-owned tables are forbidden"):
        reject_protected_fact_table_dml(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM facts WHERE tenant_id = ?",
        "CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY)",
        "INSERT INTO audit_queue (event_type, payload) VALUES (?, ?)",
        "UPDATE items SET value = ? WHERE id = ?",
        "DELETE FROM cache_entries WHERE expires_at < ?",
    ],
)
def test_reject_protected_fact_table_dml_allows_non_fact_mutations(sql: str) -> None:
    reject_protected_fact_table_dml(sql)


def test_reject_protected_fact_table_dml_allows_schema_trigger_bodies() -> None:
    reject_protected_fact_table_dml(
        """
        CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts
        BEGIN
          INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
        END;
        """,
        allow_trigger_bodies=True,
    )


def test_reject_protected_fact_table_dml_still_blocks_script_dml_after_trigger() -> None:
    with pytest.raises(ValueError, match="Direct mutations on fact-owned tables are forbidden"):
        reject_protected_fact_table_dml(
            """
            CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts
            BEGIN
              INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
            END;
            INSERT INTO facts (content) VALUES ('raw');
            """,
            allow_trigger_bodies=True,
        )
