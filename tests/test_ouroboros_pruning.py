from __future__ import annotations

import sqlite3

import pytest

from cortex.extensions.gate.ouroboros import OuroborosGate


def test_ouroboros_pruning_blocks_physical_delete() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project TEXT NOT NULL,
                content TEXT NOT NULL,
                fact_type TEXT NOT NULL
            );
            INSERT INTO facts (id, tenant_id, project, content, fact_type)
            VALUES
                (1, 'tenant-alpha', 'shared-project', 'alpha', 'knowledge'),
                (2, 'tenant-beta', 'shared-project', 'beta', 'knowledge');
            """
        )

        with pytest.raises(RuntimeError, match="Unsafe Ouroboros physical pruning"):
            OuroborosGate(conn).trigger_pruning("shared-project")

        assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 2
    finally:
        conn.close()
