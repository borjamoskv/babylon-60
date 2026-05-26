"""Tests for cortex-core/persistence.py — Sovereign Hybrid Persistence.

C5-REAL audit remediation: core persistence coverage + guard clause validation.
Tests L1 (ContextCache), L2 (VSAMemory), L3 (LedgerManager),
HybridPersistenceManager, and the swarm queue dispatcher.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time

import pytest

# Make cortex-core importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

# Patch DB_PATH before import to avoid touching real state
_tmpdir = tempfile.mkdtemp()
_test_db = os.path.join(_tmpdir, "test_cortex.db")
os.environ["CORTEX_DB_PATH"] = _test_db

import persistence  # noqa: E402

# Force module-level DB_PATH to our test path (handles cached imports)
persistence.DB_PATH = _test_db


# -- L1: ContextCache --


class TestContextCache:
    def setup_method(self):
        self.cache = persistence.ContextCache()

    def test_put_and_get(self):
        self.cache.put("k1", {"data": 42})
        result = self.cache.get("k1")
        assert result == {"data": 42}

    def test_get_miss_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        self.cache.put("k1", {"data": 1})
        self.cache._cache["k1"]["timestamp"] = time.time() - 400
        assert self.cache.get("k1") is None
        assert "k1" not in self.cache._cache

    def test_put_guard_empty_key(self):
        with pytest.raises(ValueError, match="non-empty"):
            self.cache.put("", {"data": 1})

    def test_put_guard_none_key(self):
        with pytest.raises((ValueError, TypeError)):
            self.cache.put(None, {"data": 1})

    def test_put_guard_non_dict_payload(self):
        with pytest.raises(TypeError, match="dict"):
            self.cache.put("k1", "not a dict")

    def test_get_guard_empty_key(self):
        with pytest.raises(ValueError, match="non-empty"):
            self.cache.get("")

    def test_inject_anthropic_headers_large_block(self):
        blocks = [{"text": "x" * 3000}]
        result = self.cache.inject_anthropic_headers(blocks)
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    def test_inject_anthropic_headers_last_block(self):
        blocks = [{"text": "short"}, {"text": "also short"}]
        result = self.cache.inject_anthropic_headers(blocks)
        assert "cache_control" not in result[0]
        assert result[1]["cache_control"] == {"type": "ephemeral"}

    def test_inject_anthropic_headers_empty(self):
        result = self.cache.inject_anthropic_headers([])
        assert result == []


# -- L3: LedgerManager --


class TestLedgerManager:
    def setup_method(self):
        """Ensure fresh DB state before each test."""
        import sqlite3

        self.ledger = persistence.LedgerManager()
        conn = sqlite3.connect(_test_db)
        conn.execute("DELETE FROM ledger_records")
        conn.commit()
        conn.close()

    def test_append_returns_sha256(self):
        h = self.ledger.append("STORE", "vec-001", 0.5)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_append_chain_integrity(self):
        h1 = self.ledger.append("STORE", "vec-001", 1.0)
        h2 = self.ledger.append("QUERY", "vec-001", 0.1)
        assert h1 != h2

    def test_genesis_block(self):
        h = self.ledger.append("INIT", "vec-genesis", 0.0)
        assert len(h) == 64

    def test_get_total_yield(self):
        self.ledger.append("STORE", "vec-001", 1.5)
        self.ledger.append("STORE", "vec-001", 2.5)
        total = self.ledger.get_total_yield("vec-001")
        assert total == pytest.approx(4.0)

    def test_get_total_yield_all(self):
        self.ledger.append("A", "v1", 1.0)
        self.ledger.append("B", "v2", 2.0)
        total = self.ledger.get_total_yield()
        assert total == pytest.approx(3.0)

    def test_get_total_yield_empty(self):
        total = self.ledger.get_total_yield("nonexistent")
        assert total == 0.0

    def test_append_guard_empty_action(self):
        with pytest.raises(ValueError, match="action"):
            self.ledger.append("", "vec-001", 1.0)

    def test_append_guard_empty_vector_id(self):
        with pytest.raises(ValueError, match="vector_id"):
            self.ledger.append("STORE", "", 1.0)

    def test_append_guard_non_numeric_yield(self):
        with pytest.raises(TypeError, match="numeric"):
            self.ledger.append("STORE", "vec-001", "not_a_number")

    def test_append_guard_whitespace_action(self):
        with pytest.raises(ValueError, match="action"):
            self.ledger.append("   ", "vec-001", 1.0)


# -- L2: VSAMemory --


class TestVSAMemory:
    def setup_method(self):
        self.vsa = persistence.VSAMemory()

    def test_record_increments_tensor(self):
        ctx = "test:value"
        idx = int(hashlib.sha256(ctx.encode("utf-8")).hexdigest(), 16) % persistence.VSA_DIMENSION
        assert self.vsa._tensor[idx] == 0.0
        self.vsa.record("test", "value")
        assert self.vsa._tensor[idx] == 1.0

    def test_record_multiple_increments(self):
        ctx = "k:v"
        idx = int(hashlib.sha256(ctx.encode("utf-8")).hexdigest(), 16) % persistence.VSA_DIMENSION
        self.vsa.record("k", "v")
        self.vsa.record("k", "v")
        assert self.vsa._tensor[idx] == 2.0

    def test_record_guard_empty_key(self):
        with pytest.raises(ValueError, match="non-empty"):
            self.vsa.record("", "value")

    def test_record_guard_non_string_value(self):
        with pytest.raises(TypeError, match="string"):
            self.vsa.record("key", 42)

    def test_start_glia_no_loop(self):
        vsa = persistence.VSAMemory()
        vsa.start_glia()
        assert vsa._daemon_task is None

    def test_start_glia_idempotent(self):
        vsa = persistence.VSAMemory()
        vsa.start_glia()
        vsa.start_glia()


# -- HybridPersistenceManager --


class TestHybridPersistenceManager:
    def test_layers_initialized(self):
        mgr = persistence.HybridPersistenceManager()
        assert isinstance(mgr.l1, persistence.ContextCache)
        assert isinstance(mgr.l2, persistence.VSAMemory)
        assert isinstance(mgr.l3, persistence.LedgerManager)

    def test_l1_accessible(self):
        mgr = persistence.HybridPersistenceManager()
        mgr.l1.put("test", {"data": 1})
        assert mgr.l1.get("test") == {"data": 1}

    def test_l3_accessible(self):
        import sqlite3

        conn = sqlite3.connect(_test_db)
        conn.execute("DELETE FROM ledger_records")
        conn.commit()
        conn.close()
        mgr = persistence.HybridPersistenceManager()
        h = mgr.l3.append("TEST", "v1", 1.0)
        assert len(h) == 64


# -- Swarm Queue Dispatcher --


class TestSwarmQueueDispatcher:
    def setup_method(self):
        self._queue_file = os.path.join(_tmpdir, "test_queue.json")
        self._orig = persistence.SWARM_QUEUE_FILE

    def teardown_method(self):
        persistence.SWARM_QUEUE_FILE = self._orig
        if os.path.exists(self._queue_file):
            os.remove(self._queue_file)

    def test_enqueue_creates_file(self):
        persistence.SWARM_QUEUE_FILE = self._queue_file
        persistence._enqueue_swarm_task_sync("TestAgent", {"task": "ping"})
        assert os.path.exists(self._queue_file)
        with open(self._queue_file) as f:
            data = json.load(f)
        assert len(data["pending_tasks"]) == 1
        assert data["pending_tasks"][0]["agent"] == "TestAgent"

    def test_enqueue_appends_to_existing(self):
        persistence.SWARM_QUEUE_FILE = self._queue_file
        persistence._enqueue_swarm_task_sync("A1", {"x": 1})
        persistence._enqueue_swarm_task_sync("A2", {"x": 2})
        with open(self._queue_file) as f:
            data = json.load(f)
        assert len(data["pending_tasks"]) == 2

    def test_enqueue_recovers_corrupted_json(self):
        persistence.SWARM_QUEUE_FILE = self._queue_file
        with open(self._queue_file, "w") as f:
            f.write("CORRUPTED{{{")
        persistence._enqueue_swarm_task_sync("A1", {"x": 1})
        with open(self._queue_file) as f:
            data = json.load(f)
        assert len(data["pending_tasks"]) == 1

    def test_enqueue_caps_map(self):
        persistence.SWARM_QUEUE_FILE = self._queue_file
        persistence._enqueue_swarm_task_sync("VulnerabilityFixer", {"target": "test"})
        with open(self._queue_file) as f:
            data = json.load(f)
        assert data["pending_tasks"][0]["agent"] == "VulnerabilityFixer"
