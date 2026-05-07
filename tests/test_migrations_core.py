from __future__ import annotations

import sqlite3

import aiosqlite
import pytest

from cortex.migrations import core


def test_fresh_db_base_schema_marks_latest_migration_version() -> None:
    conn = sqlite3.connect(":memory:")

    first_applied = core.run_migrations(conn)
    current_after_first = core.get_current_version(conn)
    second_applied = core.run_migrations(conn)

    assert first_applied == 0
    assert current_after_first == max(version for version, _, _ in core.MIGRATIONS)
    assert second_applied == 0


def test_run_migrations_aborts_on_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = sqlite3.connect(":memory:")
    core.ensure_migration_table(conn)
    conn.execute("INSERT INTO schema_version (version, description) VALUES (1, 'seed')")
    conn.commit()

    def mig_2(db: sqlite3.Connection) -> None:
        db.execute("CREATE TABLE ok_table (id INTEGER)")

    def mig_3(db: sqlite3.Connection) -> None:
        db.execute("CREATE TABLE broken (")

    def mig_4(db: sqlite3.Connection) -> None:
        db.execute("CREATE TABLE should_not_exist (id INTEGER)")

    monkeypatch.setattr(
        core,
        "MIGRATIONS",
        [
            (2, "ok", mig_2),
            (3, "boom", mig_3),
            (4, "must not run", mig_4),
        ],
    )

    with pytest.raises(RuntimeError, match="Migration 3 failed; aborting remaining migrations"):
        core.run_migrations(conn)

    assert core.get_current_version(conn) == 2
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "ok_table" in tables
    assert "should_not_exist" not in tables


def test_failed_migration_rolls_back_partial_schema_even_after_inner_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = sqlite3.connect(":memory:")
    core.ensure_migration_table(conn)
    conn.execute("INSERT INTO schema_version (version, description) VALUES (1, 'seed')")
    conn.commit()

    def mig_2(db: sqlite3.Connection) -> None:
        db.execute("CREATE TABLE ok_table (id INTEGER)")

    def mig_3(db: sqlite3.Connection) -> None:
        db.execute("CREATE TABLE partial_table (id INTEGER)")
        db.commit()
        raise ValueError("deterministic migration rejection")

    monkeypatch.setattr(core, "MIGRATIONS", [(2, "ok", mig_2), (3, "boom", mig_3)])

    with pytest.raises(RuntimeError, match="Migration 3 failed; aborting remaining migrations"):
        core.run_migrations(conn)

    assert core.get_current_version(conn) == 2
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "ok_table" in tables
    assert "partial_table" not in tables


@pytest.mark.asyncio
async def test_run_migrations_async_aborts_on_first_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT, description TEXT)"
        )
        await conn.execute("INSERT INTO schema_version (version, description) VALUES (1, 'seed')")
        await conn.commit()

        def mig_2(db: sqlite3.Connection) -> None:
            db.execute("CREATE TABLE ok_table (id INTEGER)")

        def mig_3(db: sqlite3.Connection) -> None:
            db.execute("CREATE TABLE broken (")

        def mig_4(db: sqlite3.Connection) -> None:
            db.execute("CREATE TABLE should_not_exist (id INTEGER)")

        monkeypatch.setattr(
            core,
            "MIGRATIONS",
            [
                (2, "ok", mig_2),
                (3, "boom", mig_3),
                (4, "must not run", mig_4),
            ],
        )

        with pytest.raises(RuntimeError, match="Migration 3 failed; aborting remaining migrations"):
            await core.run_migrations_async(conn)

        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cursor.fetchone()
        assert row[0] == 2

        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        tables = {row[0] for row in await cursor.fetchall()}
        assert "ok_table" in tables
        assert "should_not_exist" not in tables


@pytest.mark.asyncio
async def test_run_migrations_async_rolls_back_partial_schema_even_after_inner_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT, description TEXT)"
        )
        await conn.execute("INSERT INTO schema_version (version, description) VALUES (1, 'seed')")
        await conn.commit()

        def mig_2(db: sqlite3.Connection) -> None:
            db.execute("CREATE TABLE ok_table (id INTEGER)")

        def mig_3(db: sqlite3.Connection) -> None:
            db.execute("CREATE TABLE partial_table (id INTEGER)")
            db.commit()
            raise ValueError("deterministic migration rejection")

        monkeypatch.setattr(core, "MIGRATIONS", [(2, "ok", mig_2), (3, "boom", mig_3)])

        with pytest.raises(RuntimeError, match="Migration 3 failed; aborting remaining migrations"):
            await core.run_migrations_async(conn)

        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cursor.fetchone()
        assert row[0] == 2

        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        tables = {row[0] for row in await cursor.fetchall()}
        assert "ok_table" in tables
        assert "partial_table" not in tables
