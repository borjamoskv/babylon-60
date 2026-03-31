from __future__ import annotations

from cortex.extensions.daemon.monitors.cloud import CloudSyncMonitor


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.closed = False
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple):
        self.calls.append((sql, params))
        return _FakeCursor(self.rows)

    def close(self) -> None:
        self.closed = True


class _FakeEngine:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def _get_sync_conn(self) -> _FakeConn:
        return self._conn


class _FakeTurso:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.executemany_calls: list[tuple[str, list[tuple]]] = []

    async def executemany(self, sql: str, params_list: list[tuple]) -> None:
        self.executemany_calls.append((sql, params_list))
        if self.should_fail:
            raise RuntimeError("edge down")


def test_cloud_sync_monitor_closes_local_connection_after_success(monkeypatch) -> None:
    rows = [
        (5, "alpha", "store", "{}", "prev-4", "hash-5", "2026-03-31T00:00:00Z"),
        (6, "alpha", "store", "{}", "prev-5", "hash-6", "2026-03-31T00:01:00Z"),
    ]
    conn = _FakeConn(rows)
    monitor = CloudSyncMonitor(interval_seconds=0, engine=_FakeEngine(conn), batch_size=10)
    turso = _FakeTurso()
    monitor._turso = turso
    monkeypatch.setattr(monitor, "_get_last_synced_id", lambda: 4)

    alerts = monitor.check()

    assert conn.closed is True
    assert conn.calls == [
        (
            "SELECT id, project, action, detail, prev_hash, hash, timestamp "
            "FROM transactions WHERE id > ? ORDER BY id ASC LIMIT ?",
            (4, 10),
        )
    ]
    assert len(turso.executemany_calls) == 1
    assert alerts[0].synced_count == 2
    assert alerts[0].last_id == 6


def test_cloud_sync_monitor_closes_local_connection_on_remote_failure(monkeypatch) -> None:
    conn = _FakeConn([(7, "alpha", "store", "{}", "prev-6", "hash-7", "2026-03-31T00:02:00Z")])
    monitor = CloudSyncMonitor(interval_seconds=0, engine=_FakeEngine(conn), batch_size=10)
    monitor._turso = _FakeTurso(should_fail=True)
    monkeypatch.setattr(monitor, "_get_last_synced_id", lambda: 6)

    alerts = monitor.check()

    assert alerts == []
    assert conn.closed is True
