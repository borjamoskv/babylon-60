"""SQLite persistence for the continual-learning sidecar."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cortex.database.core import connect
from cortex.extensions.continual_learning.models import (
    AdapterSnapshot,
    AdapterState,
    ExperienceRecord,
)

__all__ = [
    "SQLiteContinualLearningStore",
    "SQLitePrototypeStore",
    "SQLiteRetrainQueue",
    "SQLiteSemanticMemoryStore",
]

_CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS continual_buffer (
    experience_id    TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    domain           TEXT NOT NULL,
    priority         REAL NOT NULL,
    inserted_at      REAL NOT NULL,
    last_seen_at     REAL NOT NULL,
    novelty          REAL NOT NULL,
    pinned_anchor    INTEGER NOT NULL DEFAULT 0,
    dedup_group_id   TEXT NOT NULL,
    payload          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cl_buffer_scope ON continual_buffer(tenant_id, domain, priority DESC);

CREATE TABLE IF NOT EXISTS continual_prototypes (
    experience_id    TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    domain           TEXT NOT NULL,
    payload          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cl_prototypes_scope ON continual_prototypes(tenant_id, domain);

CREATE TABLE IF NOT EXISTS continual_semantic_chunks (
    chunk_id         TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    text             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cl_chunks_tenant ON continual_semantic_chunks(tenant_id);

CREATE TABLE IF NOT EXISTS continual_adapters (
    adapter_id       TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    domain           TEXT NOT NULL,
    payload          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cl_adapters_scope ON continual_adapters(tenant_id, domain);

CREATE TABLE IF NOT EXISTS continual_active_scopes (
    tenant_id        TEXT NOT NULL,
    domain           TEXT NOT NULL,
    adapter_id       TEXT NOT NULL,
    PRIMARY KEY (tenant_id, domain)
);

CREATE TABLE IF NOT EXISTS continual_adapter_snapshots (
    snapshot_id      TEXT PRIMARY KEY,
    adapter_id       TEXT NOT NULL,
    tenant_id        TEXT NOT NULL,
    domain           TEXT NOT NULL,
    created_at       REAL NOT NULL,
    payload          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cl_snapshots_adapter ON continual_adapter_snapshots(adapter_id, created_at DESC);

CREATE TABLE IF NOT EXISTS continual_rollback_streaks (
    tenant_id        TEXT NOT NULL,
    domain           TEXT NOT NULL,
    streak           INTEGER NOT NULL DEFAULT 0,
    updated_at       REAL NOT NULL,
    PRIMARY KEY (tenant_id, domain)
);

CREATE TABLE IF NOT EXISTS continual_retrain_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id        TEXT NOT NULL,
    created_at       REAL NOT NULL,
    payload          TEXT NOT NULL
);
"""


def _experience_to_dict(experience: ExperienceRecord) -> dict[str, Any]:
    """Serialize an ``ExperienceRecord`` into JSON-safe primitives."""
    payload = asdict(experience)
    payload["embedding"] = list(experience.embedding)
    payload["pii_categories"] = list(experience.pii_categories)
    return payload


def _adapter_state_to_dict(state: AdapterState) -> dict[str, Any]:
    """Serialize an ``AdapterState`` into JSON-safe primitives."""
    return asdict(state)


def _adapter_snapshot_to_dict(snapshot: AdapterSnapshot) -> dict[str, Any]:
    """Serialize an ``AdapterSnapshot`` into JSON-safe primitives."""
    return asdict(snapshot)


class SQLiteContinualLearningStore:
    """Dedicated SQLite store for continual-learning state."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    @property
    def db_path(self) -> Path:
        """Return the underlying SQLite file path."""
        return self._db_path

    def ensure_schema(self) -> None:
        """Create all sidecar tables idempotently."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.executescript(_CREATE_SCHEMA)
            conn.commit()

    def load_buffer_entries(self) -> list[dict[str, Any]]:
        """Return serialized replay buffer entries."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                """
                SELECT experience_id, priority, inserted_at, last_seen_at, novelty,
                       pinned_anchor, dedup_group_id, payload
                FROM continual_buffer
                ORDER BY priority DESC, last_seen_at DESC
                """
            )
            rows = cursor.fetchall()
        entries: list[dict[str, Any]] = []
        for row in rows:
            entries.append(
                {
                    "experience": json.loads(row["payload"]),
                    "priority": float(row["priority"]),
                    "inserted_at": float(row["inserted_at"]),
                    "last_seen_at": float(row["last_seen_at"]),
                    "novelty": float(row["novelty"]),
                    "pinned_anchor": bool(row["pinned_anchor"]),
                    "dedup_group_id": row["dedup_group_id"],
                }
            )
        return entries

    def save_buffer_entry(self, payload: dict[str, Any]) -> None:
        """Persist or replace a serialized replay buffer entry."""
        experience = payload["experience"]
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO continual_buffer (
                    experience_id, tenant_id, domain, priority, inserted_at, last_seen_at,
                    novelty, pinned_anchor, dedup_group_id, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experience["id"],
                    experience["tenant_id"],
                    experience["domain"],
                    float(payload["priority"]),
                    float(payload["inserted_at"]),
                    float(payload["last_seen_at"]),
                    float(payload["novelty"]),
                    1 if payload["pinned_anchor"] else 0,
                    payload["dedup_group_id"],
                    json.dumps(experience),
                ),
            )
            conn.commit()

    def delete_buffer_entries(self, experience_ids: Sequence[str]) -> None:
        """Delete serialized buffer entries."""
        if not experience_ids:
            return
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.executemany(
                "DELETE FROM continual_buffer WHERE experience_id = ?",
                [(experience_id,) for experience_id in experience_ids],
            )
            conn.commit()

    def save_prototypes(
        self,
        tenant_id: str,
        domain: str,
        examples: Sequence[ExperienceRecord],
    ) -> None:
        """Persist prototype examples."""
        if not examples:
            return
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO continual_prototypes (experience_id, tenant_id, domain, payload)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        example.id,
                        tenant_id.strip(),
                        domain.strip(),
                        json.dumps(_experience_to_dict(example)),
                    )
                    for example in examples
                ],
            )
            conn.commit()

    def load_prototypes(self) -> list[dict[str, Any]]:
        """Return serialized prototypes."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                "SELECT tenant_id, domain, payload FROM continual_prototypes ORDER BY experience_id ASC"
            )
            rows = cursor.fetchall()
        return [
            {
                "tenant_id": row["tenant_id"],
                "domain": row["domain"],
                "experience": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def purge_prototypes_by_source_ids(self, source_ids: Sequence[str]) -> int:
        """Delete persisted prototypes by source experience ID."""
        if not source_ids:
            return 0
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            deleted = 0
            for source_id in source_ids:
                cursor = conn.execute(
                    "DELETE FROM continual_prototypes WHERE experience_id = ?",
                    (source_id,),
                )
                deleted += cursor.rowcount
            conn.commit()
        return deleted

    def save_semantic_chunk(self, tenant_id: str, chunk_id: str, text: str) -> None:
        """Persist a semantic memory chunk."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO continual_semantic_chunks (chunk_id, tenant_id, text)
                VALUES (?, ?, ?)
                """,
                (chunk_id, tenant_id.strip(), text),
            )
            conn.commit()

    def delete_semantic_chunks_by_query(self, tenant_id: str, query: str) -> list[str]:
        """Delete semantic chunks whose text contains ``query``."""
        tenant_key = tenant_id.strip()
        needle = f"%{query.lower().strip()}%"
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                """
                SELECT chunk_id
                FROM continual_semantic_chunks
                WHERE tenant_id = ? AND LOWER(text) LIKE ?
                """,
                (tenant_key, needle),
            )
            chunk_ids = [row["chunk_id"] for row in cursor.fetchall()]
            if chunk_ids:
                conn.executemany(
                    "DELETE FROM continual_semantic_chunks WHERE chunk_id = ?",
                    [(chunk_id,) for chunk_id in chunk_ids],
                )
                conn.commit()
        return chunk_ids

    def load_semantic_chunks(self) -> list[dict[str, str]]:
        """Return persisted semantic chunks."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                "SELECT tenant_id, chunk_id, text FROM continual_semantic_chunks ORDER BY chunk_id ASC"
            )
            rows = cursor.fetchall()
        return [
            {"tenant_id": row["tenant_id"], "chunk_id": row["chunk_id"], "text": row["text"]}
            for row in rows
        ]

    def load_adapter_states(self) -> list[dict[str, Any]]:
        """Return serialized adapter states."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT payload FROM continual_adapters ORDER BY adapter_id ASC")
            rows = cursor.fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def load_active_scopes(self) -> dict[tuple[str, str], str]:
        """Return active adapters keyed by ``(tenant_id, domain)``."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                "SELECT tenant_id, domain, adapter_id FROM continual_active_scopes"
            )
            rows = cursor.fetchall()
        return {(row["tenant_id"], row["domain"]): row["adapter_id"] for row in rows}

    def load_adapter_snapshots(self) -> list[dict[str, Any]]:
        """Return serialized adapter snapshots."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                "SELECT payload FROM continual_adapter_snapshots ORDER BY created_at ASC"
            )
            rows = cursor.fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def load_rollback_streaks(self) -> dict[tuple[str, str], int]:
        """Return rollback streak counters."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                "SELECT tenant_id, domain, streak FROM continual_rollback_streaks"
            )
            rows = cursor.fetchall()
        return {(row["tenant_id"], row["domain"]): int(row["streak"]) for row in rows}

    def save_adapter_state(self, payload: dict[str, Any]) -> None:
        """Persist a serialized adapter state."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO continual_adapters (adapter_id, tenant_id, domain, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload["adapter_id"],
                    payload["tenant_id"],
                    payload["domain"],
                    json.dumps(payload),
                ),
            )
            conn.commit()

    def save_active_scope(self, tenant_id: str, domain: str, adapter_id: str) -> None:
        """Persist the active adapter mapping for a scope."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO continual_active_scopes (tenant_id, domain, adapter_id)
                VALUES (?, ?, ?)
                """,
                (tenant_id.strip(), domain.strip(), adapter_id),
            )
            conn.commit()

    def save_adapter_snapshot(self, payload: dict[str, Any]) -> None:
        """Persist a serialized adapter snapshot."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO continual_adapter_snapshots (
                    snapshot_id, adapter_id, tenant_id, domain, created_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["snapshot_id"],
                    payload["adapter_id"],
                    payload["tenant_id"],
                    payload["domain"],
                    float(payload["created_at"]),
                    json.dumps(payload),
                ),
            )
            conn.commit()

    def increment_rollback_streak(self, tenant_id: str, domain: str) -> int:
        """Increase and persist the rollback streak for a scope."""
        tenant_key = tenant_id.strip()
        domain_key = domain.strip()
        now = time.time()
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                """
                SELECT streak FROM continual_rollback_streaks
                WHERE tenant_id = ? AND domain = ?
                """,
                (tenant_key, domain_key),
            )
            row = cursor.fetchone()
            streak = (int(row["streak"]) if row else 0) + 1
            conn.execute(
                """
                INSERT OR REPLACE INTO continual_rollback_streaks (tenant_id, domain, streak, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (tenant_key, domain_key, streak, now),
            )
            conn.commit()
        return streak

    def reset_rollback_streak(self, tenant_id: str, domain: str) -> None:
        """Reset the persisted rollback streak for a scope."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                DELETE FROM continual_rollback_streaks
                WHERE tenant_id = ? AND domain = ?
                """,
                (tenant_id.strip(), domain.strip()),
            )
            conn.commit()

    def enqueue_retrain_job(self, job: dict[str, Any]) -> None:
        """Persist a replay job."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            conn.execute(
                """
                INSERT INTO continual_retrain_jobs (tenant_id, created_at, payload)
                VALUES (?, ?, ?)
                """,
                (job["tenant_id"], time.time(), json.dumps(job)),
            )
            conn.commit()

    def load_retrain_jobs(self) -> list[dict[str, Any]]:
        """Return persisted retrain jobs."""
        with connect(str(self._db_path), row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT payload FROM continual_retrain_jobs ORDER BY id ASC")
            rows = cursor.fetchall()
        return [json.loads(row["payload"]) for row in rows]


class SQLitePrototypeStore:
    """Prototype store backed by ``SQLiteContinualLearningStore``."""

    def __init__(self, store: SQLiteContinualLearningStore) -> None:
        self._store = store
        self._items: dict[tuple[str, str], list[ExperienceRecord]] = {}
        self._hydrate()

    def _hydrate(self) -> None:
        self._items = {}
        for row in self._store.load_prototypes():
            key = (row["tenant_id"], row["domain"])
            self._items.setdefault(key, []).append(ExperienceRecord(**row["experience"]))

    def add(self, tenant_id: str, domain: str, examples: Sequence[ExperienceRecord]) -> None:
        key = (tenant_id.strip(), domain.strip())
        self._items.setdefault(key, []).extend(examples)
        self._store.save_prototypes(tenant_id, domain, examples)

    def sample(self, tenant_id: str, domain: str, k: int) -> list[ExperienceRecord]:
        return list(self._items.get((tenant_id.strip(), domain.strip()), [])[: max(k, 0)])

    def purge_by_source_ids(self, source_ids: Sequence[str]) -> int:
        source_set = set(source_ids)
        deleted = 0
        for key, items in list(self._items.items()):
            kept = [item for item in items if item.id not in source_set]
            deleted += len(items) - len(kept)
            self._items[key] = kept
        persisted = self._store.purge_prototypes_by_source_ids(list(source_ids))
        return max(deleted, persisted)


class SQLiteSemanticMemoryStore:
    """Semantic memory store backed by ``SQLiteContinualLearningStore``."""

    def __init__(self, store: SQLiteContinualLearningStore) -> None:
        self._store = store

    def add(self, tenant_id: str, chunk_id: str, text: str) -> None:
        self._store.save_semantic_chunk(tenant_id, chunk_id, text)

    def delete_by_query(self, tenant_id: str, query: str) -> list[str]:
        return self._store.delete_semantic_chunks_by_query(tenant_id, query)


class SQLiteRetrainQueue:
    """Replay queue backed by ``SQLiteContinualLearningStore``."""

    def __init__(self, store: SQLiteContinualLearningStore) -> None:
        self._store = store

    @property
    def items(self) -> list[dict[str, Any]]:
        """Return all queued jobs in insertion order."""
        return self._store.load_retrain_jobs()

    def put(self, job: dict[str, Any]) -> None:
        self._store.enqueue_retrain_job(job)
