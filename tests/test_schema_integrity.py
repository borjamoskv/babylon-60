"""
Schema Integrity Tests (Ω₁: Byzantine verification).

Validates that every column the runtime expects actually exists
in the canonical schema and survives a fresh DB creation.
"""

from __future__ import annotations

import re
import sqlite3

from cortex.database.schema import (
    CREATE_FACTS,
    SCHEMA_VERSION,
)
from cortex.database.schema_extensions import (
    CREATE_AGENTS,
    CREATE_LOCK_INTENTS,
    CREATE_LOCK_STATE,
    CREATE_SIGNALS,
)

# ─── Helpers ───────────────────────────────────────────────────────────


def _extract_columns(create_sql: str) -> set[str]:
    """Extract column names from a CREATE TABLE statement."""
    # Find content between first ( and last )
    match = re.search(r"\(\s*\n?(.*)\n?\s*\)", create_sql, re.DOTALL)
    if not match:
        return set()
    body = match.group(1)
    cols = set()
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("--") or line.startswith(")"):
            continue
        # Skip constraints (CHECK, UNIQUE, FOREIGN, PRIMARY KEY as standalone)
        upper = line.upper()
        if any(upper.startswith(kw) for kw in ("CHECK", "UNIQUE", "FOREIGN", "PRIMARY KEY(")):
            continue
        # First token is the column name
        token = line.split()[0].strip(",")
        if token.upper() not in ("CREATE", "TABLE", "IF", "NOT", "EXISTS"):
            cols.add(token)
    return cols


def _create_fresh_db(schema_sqls: list[str]) -> sqlite3.Connection:
    """Create a fresh in-memory DB applying the given schema statements."""
    conn = sqlite3.connect(":memory:")
    for sql in schema_sqls:
        for stmt in sql.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
    conn.commit()
    return conn


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Get actual column names from a table via PRAGMA."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


# ─── Tests ─────────────────────────────────────────────────────────────


class TestFactsSchema:
    """Verify facts table has all columns the runtime depends on."""

    REQUIRED_COLUMNS = {
        "id",
        "tenant_id",
        "project",
        "content",
        "fact_type",
        "tags",
        "metadata",
        "hash",
        "valid_from",
        "valid_until",
        "source",
        "confidence",
        "tx_id",
        "cognitive_layer",
        "parent_decision_id",
        "consensus_score",
        "last_accessed",
        "created_at",
        "updated_at",
        "is_tombstoned",
        "is_quarantined",
        "quarantined_at",
        "quarantine_reason",
        "tombstoned_at",
    }

    def test_canonical_schema_contains_all_columns(self):
        """The CREATE_FACTS SQL must declare every runtime-required column."""
        defined = _extract_columns(CREATE_FACTS)
        missing = self.REQUIRED_COLUMNS - defined
        assert not missing, (
            f"Ghost columns detected — runtime expects {missing} "
            f"but CREATE_FACTS does not define them"
        )

    def test_fresh_db_has_all_columns(self):
        """A fresh DB must actually have the columns after CREATE TABLE."""
        conn = _create_fresh_db([CREATE_FACTS])
        actual = _get_table_columns(conn, "facts")
        conn.close()
        missing = self.REQUIRED_COLUMNS - actual
        assert not missing, (
            f"Fresh DB missing columns: {missing}. "
            f"Schema definition and PRAGMA diverge."
        )


class TestAgentsSchema:
    """Verify agents table has entropy columns."""

    REQUIRED_COLUMNS = {
        "id",
        "tenant_id",
        "name",
        "alignment_hits",
        "alignment_misses",
        "base_reputation",
    }

    def test_canonical_schema_contains_entropy_columns(self):
        defined = _extract_columns(CREATE_AGENTS)
        missing = self.REQUIRED_COLUMNS - defined
        assert not missing, f"Agents schema missing: {missing}"


class TestLockTablesSchema:
    """Verify lock tables have tenant_id for multi-tenant isolation."""

    def test_lock_intents_has_tenant_id(self):
        defined = _extract_columns(CREATE_LOCK_INTENTS)
        assert "tenant_id" in defined, "lock_intents missing tenant_id"

    def test_lock_state_has_tenant_id(self):
        defined = _extract_columns(CREATE_LOCK_STATE)
        assert "tenant_id" in defined, "lock_state missing tenant_id"

    def test_fresh_lock_tables(self):
        conn = _create_fresh_db([CREATE_LOCK_INTENTS, CREATE_LOCK_STATE])
        intents_cols = _get_table_columns(conn, "lock_intents")
        state_cols = _get_table_columns(conn, "lock_state")
        conn.close()
        assert "tenant_id" in intents_cols
        assert "tenant_id" in state_cols


class TestSignalsSchema:
    """Verify signals table has tenant_id."""

    def test_signals_has_tenant_id(self):
        defined = _extract_columns(CREATE_SIGNALS)
        assert "tenant_id" in defined, "signals missing tenant_id"


class TestSchemaVersion:
    """Verify schema version is current."""

    def test_version_is_5_4_0(self):
        assert SCHEMA_VERSION == "5.4.0", (
            f"SCHEMA_VERSION is {SCHEMA_VERSION}, expected 5.4.0"
        )
