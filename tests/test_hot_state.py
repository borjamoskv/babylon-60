"""Tests for HotStateDB."""

import pytest

from cortex.extensions.daemon.hot_state import HotStateDB


@pytest.fixture
def state(tmp_path):
    """Create a HotStateDB with a temporary database."""
    db = tmp_path / "test_hot_state.db"
    return HotStateDB(db_path=db)


class TestKVOperations:
    def test_set_and_get(self, state):
        state.set("key1", "value1")
        assert state.get("key1") == "value1"

    def test_get_missing_returns_default(self, state):
        assert state.get("nonexistent") is None
        assert state.get("nonexistent", "fallback") == "fallback"

    def test_set_complex_value(self, state):
        data = {"nested": {"list": [1, 2, 3]}, "flag": True}
        state.set("complex", data)
        result = state.get("complex")
        assert result == data

    def test_overwrite(self, state):
        state.set("k", "v1")
        state.set("k", "v2")
        assert state.get("k") == "v2"

    def test_delete(self, state):
        state.set("to_del", "val")
        assert state.delete("to_del") is True
        assert state.get("to_del") is None
        assert state.delete("to_del") is False

    def test_keys(self, state):
        state.set("project:a", 1)
        state.set("project:b", 2)
        state.set("other:c", 3)
        assert len(state.keys("project:")) == 2
        assert len(state.keys()) == 3

    def test_len(self, state):
        assert len(state) == 0
        state.set("a", 1)
        state.set("b", 2)
        assert len(state) == 2


class TestTTL:
    def test_ttl_not_expired(self, state):
        state.set("cache", "data", ttl_s=3600)
        assert state.get("cache") == "data"

    def test_ttl_expired(self, state):
        state.set("stale", "data", ttl_s=-1)  # Already expired
        assert state.get("stale") is None  # Returns default

    def test_purge_expired(self, state):
        state.set("fresh", "ok", ttl_s=3600)
        state.set("stale1", "old", ttl_s=-1)
        state.set("stale2", "old", ttl_s=-1)
        count = state.purge_expired()
        assert count == 2
        assert len(state) == 1


class TestMetrics:
    def test_increment(self, state):
        val = state.increment("counter")
        assert val == 1.0
        val = state.increment("counter", 5.0)
        assert val == 6.0

    def test_set_metric(self, state):
        state.set_metric("gauge", 42.0)
        m = state.metrics()
        assert m["gauge"] == 42.0

    def test_uptime(self, state):
        m = state.metrics()
        assert "uptime_s" in m
        assert m["uptime_s"] >= 0


class TestExport:
    def test_export_snapshot(self, state):
        state.set("k1", "v1")
        state.set_metric("m1", 100.0)
        snap = state.export_snapshot()
        assert "kv" in snap
        assert "metrics" in snap
        assert "k1" in snap["kv"]
        assert "m1" in snap["metrics"]
        assert "exported_at" in snap


class TestQuery:
    def test_raw_sql(self, state):
        state.set("sql_test", {"x": 1})
        rows = state.query("SELECT key, value FROM hot_kv WHERE key = ?", ("sql_test",))
        assert len(rows) == 1
        assert rows[0]["key"] == "sql_test"
