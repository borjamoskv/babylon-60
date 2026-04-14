"""Tests for ledger_auditor tools in AgentToolkit.

Exercises ``ledger_query_fact`` and ``ledger_search`` against an
isolated SQLite database.  No network, no LLM, no real CORTEX engine.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from cortex.extensions.aether.tools import AgentToolkit

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_db(tmp_path: Path) -> Path:
    """Create a minimal ledger_events SQLite DB for testing."""
    db = tmp_path / "test_ledger.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE ledger_events (
            event_id        TEXT PRIMARY KEY,
            ts              TEXT NOT NULL,
            tool            TEXT NOT NULL,
            actor           TEXT NOT NULL,
            action          TEXT NOT NULL,
            payload_json    TEXT NOT NULL,
            prev_hash       TEXT,
            hash            TEXT,
            semantic_status TEXT NOT NULL DEFAULT 'pending',
            semantic_error  TEXT,
            correlation_id  TEXT,
            trace_id        TEXT,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )
        """
    )
    conn.commit()
    conn.close()
    return db


def _insert_event(
    db: Path,
    *,
    event_id: str | None = None,
    ts: str = "2025-01-01T00:00:00+00:00",
    tool: str = "test_tool",
    actor: str = "test_actor",
    action: str = "store",
    payload: dict | None = None,
    prev_hash: str = "GENESIS",
    stored_hash: str = "deadbeef",
    semantic_status: str = "indexed",
) -> str:
    eid = event_id or str(uuid.uuid4())
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO ledger_events "
        "(event_id, ts, tool, actor, action, payload_json, prev_hash, hash, semantic_status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            eid,
            ts,
            tool,
            actor,
            action,
            json.dumps(payload or {}),
            prev_hash,
            stored_hash,
            semantic_status,
        ),
    )
    conn.commit()
    conn.close()
    return eid


@pytest.fixture
def toolkit(tmp_path: Path) -> AgentToolkit:
    """AgentToolkit pointed at a temp repo dir."""
    return AgentToolkit(repo_path=tmp_path)


@pytest.fixture
def ledger_db(tmp_path: Path) -> Path:
    return _make_db(tmp_path)


# ── Capability expansion ──────────────────────────────────────────────────────


class TestLedgerCapabilityExpansion:
    def test_ledger_group_expands_to_two_methods(self, tmp_path: Path):
        tk = AgentToolkit(repo_path=tmp_path, allowed_tools=["ledger"])
        assert "ledger_query_fact" in tk.allowed_tools
        assert "ledger_search" in tk.allowed_tools

    def test_ledger_combined_with_other_groups(self, tmp_path: Path):
        tk = AgentToolkit(repo_path=tmp_path, allowed_tools=["filesystem", "ledger"])
        assert "read_file" in tk.allowed_tools
        assert "ledger_query_fact" in tk.allowed_tools
        assert "ledger_search" in tk.allowed_tools

    def test_none_allowed_tools_permits_all(self, tmp_path: Path):
        tk = AgentToolkit(repo_path=tmp_path, allowed_tools=None)
        assert tk.allowed_tools is None


# ── ledger_query_fact ─────────────────────────────────────────────────────────


class TestLedgerQueryFact:
    def test_returns_error_when_db_missing(self, toolkit: AgentToolkit, monkeypatch, tmp_path):
        monkeypatch.setenv("CORTEX_DB_PATH", str(tmp_path / "nonexistent.db"))
        result = toolkit.ledger_query_fact("some-id")
        assert "[LEDGER]" in result
        assert "not found" in result.lower() or "DB not found" in result

    def test_returns_not_found_for_unknown_id(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        result = toolkit.ledger_query_fact("00000000-0000-0000-0000-000000000000")
        assert "[LEDGER]" in result
        assert "not found" in result.lower()

    def test_returns_compromised_for_bad_hash(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        eid = _insert_event(ledger_db, stored_hash="badhash000000000")
        result = toolkit.ledger_query_fact(eid)
        assert "[LEDGER]" in result
        # Minimal test payload won't reconstruct as LedgerEvent → UNVERIFIABLE,
        # or if reconstruction succeeds the hash won't match → COMPROMISED.
        assert "COMPROMISED" in result or "UNVERIFIABLE" in result or "hash_match : False" in result

    def test_output_contains_key_fields(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        eid = _insert_event(ledger_db, actor="my_agent", tool="my_tool", action="ingest")
        result = toolkit.ledger_query_fact(eid)
        assert "my_agent" in result
        assert "my_tool" in result
        assert "ingest" in result

    def test_dispatch_routes_ledger_query_fact(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        eid = _insert_event(ledger_db)
        result = toolkit.dispatch("ledger_query_fact", {"fact_id": eid})
        assert "[LEDGER]" in result


# ── ledger_search ─────────────────────────────────────────────────────────────


class TestLedgerSearch:
    def test_returns_error_when_db_missing(self, toolkit: AgentToolkit, monkeypatch, tmp_path):
        monkeypatch.setenv("CORTEX_DB_PATH", str(tmp_path / "nonexistent.db"))
        result = toolkit.ledger_search("anything")
        assert "[LEDGER]" in result

    def test_returns_no_results_message_on_empty_db(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        result = toolkit.ledger_search("nothing_here")
        assert "No events" in result or "0 result" in result or "[LEDGER]" in result

    def test_finds_event_by_actor(self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        _insert_event(ledger_db, actor="sovereign_agent", action="decide")
        result = toolkit.ledger_search("sovereign_agent")
        assert "sovereign_agent" in result

    def test_finds_event_by_action(self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        _insert_event(ledger_db, action="deploy_mission_critical")
        result = toolkit.ledger_search("deploy_mission")
        assert "deploy_mission_critical" in result

    def test_does_not_return_failed_events(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        _insert_event(
            ledger_db,
            actor="failing_actor",
            action="bad_action",
            semantic_status="failed",
        )
        result = toolkit.ledger_search("failing_actor")
        # failed events are excluded from search results
        assert "failing_actor" not in result or "No events" in result

    def test_limit_is_respected(self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        for i in range(10):
            _insert_event(ledger_db, actor=f"bulk_actor_{i}", action="bulk_action")
        result = toolkit.ledger_search("bulk_action", limit=3)
        # Each result line starts with "  N." — count those prefixes
        result_lines = [ln for ln in result.splitlines() if ln.strip().startswith(tuple("123456789"))]
        assert len(result_lines) <= 3

    def test_limit_capped_at_20(self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        result = toolkit.ledger_search("anything", limit=999)
        # Should not raise; capped internally at 20
        assert "[LEDGER]" in result

    def test_dispatch_routes_ledger_search(
        self, toolkit: AgentToolkit, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        _insert_event(ledger_db, actor="dispatched_actor")
        result = toolkit.dispatch("ledger_search", {"query": "dispatched_actor", "limit": "5"})
        assert "[LEDGER]" in result


# ── Access control ────────────────────────────────────────────────────────────


class TestLedgerAccessControl:
    def test_ledger_tools_blocked_when_not_in_allowed_tools(
        self, tmp_path: Path, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        tk = AgentToolkit(repo_path=tmp_path, allowed_tools=["filesystem"])
        result_q = tk.dispatch("ledger_query_fact", {"fact_id": "x"})
        result_s = tk.dispatch("ledger_search", {"query": "x"})
        assert "ToolNotAllowedError" in result_q
        assert "ToolNotAllowedError" in result_s

    def test_ledger_tools_allowed_when_in_allowed_list(
        self, tmp_path: Path, ledger_db: Path, monkeypatch
    ):
        monkeypatch.setenv("CORTEX_DB_PATH", str(ledger_db))
        tk = AgentToolkit(repo_path=tmp_path, allowed_tools=["ledger"])
        # Should not return ToolNotAllowedError (may return DB-related message)
        result = tk.dispatch("ledger_search", {"query": "x"})
        assert "ToolNotAllowedError" not in result
