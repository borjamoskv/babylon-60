from __future__ import annotations

import sqlite3

import pytest

from cortex.migrations.mig_ledger_replay import _migration_023_ledger_origin_replay
from cortex.migrations.registry import MIGRATIONS


def test_migration_registry_includes_ledger_origin_replay_version() -> None:
    assert any(
        version == 23 and func is _migration_023_ledger_origin_replay
        for version, _, func in MIGRATIONS
    )


def test_migration_023_creates_replay_table_and_constraints() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    _migration_023_ledger_origin_replay(conn)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(ledger_origin_replay)")}
    assert {
        "tenant_id",
        "actor_id",
        "key_id",
        "nonce",
        "event_id",
        "signed_at",
        "origin_signature",
        "event_hash",
    } <= columns

    conn.execute(
        """
        INSERT INTO ledger_origin_replay (
            tenant_id, actor_id, key_id, nonce, event_id, signed_at, origin_signature
        )
        VALUES ('tenant-acme', 'agent-risk-01', 'key-1', 'nonce-1', 'event-1', 'ts', 'sig')
        """
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO ledger_origin_replay (
                tenant_id, actor_id, key_id, nonce, event_id, signed_at, origin_signature
            )
            VALUES ('tenant-acme', 'agent-risk-01', 'key-1', 'nonce-1', 'event-2', 'ts', 'sig')
            """
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO ledger_origin_replay (
                tenant_id, actor_id, key_id, nonce, event_id, signed_at, origin_signature
            )
            VALUES ('tenant-acme', 'agent-risk-01', 'key-1', 'nonce-2', 'event-1', 'ts', 'sig')
            """
        )

    conn.close()
