"""Tests for SovereignScheduler."""

import asyncio

import pytest

from cortex.extensions.daemon.scheduler import SovereignScheduler


@pytest.fixture
def scheduler(tmp_path):
    """Create a scheduler with a temporary database."""
    db = tmp_path / "test_scheduler.db"
    return SovereignScheduler(db_path=db, tick_interval=0.1)


class TestSchedulerRegistration:
    def test_add_recurring(self, scheduler):
        counter = {"n": 0}

        async def task():
            counter["n"] += 1

        entry = scheduler.add_recurring("test_task", lambda: task(), interval_s=60)
        assert entry.name == "test_task"
        assert entry.kind == "interval"
        assert entry.interval_s == 60

    def test_add_cron(self, scheduler):
        async def task():
            pass

        entry = scheduler.add_cron("cron_task", lambda: task(), "*/5 * * * *")
        assert entry.name == "cron_task"
        assert entry.kind == "cron"
        assert entry.cron_expr == "*/5 * * * *"

    def test_add_oneshot(self, scheduler):
        async def task():
            pass

        entry = scheduler.add_oneshot("oneshot_task", lambda: task())
        assert entry.kind == "oneshot"

    def test_list_schedules(self, scheduler):
        async def task():
            pass

        scheduler.add_recurring("a", lambda: task(), interval_s=10)
        scheduler.add_recurring("b", lambda: task(), interval_s=20)
        entries = scheduler.list_schedules()
        assert len(entries) == 2

    def test_cancel(self, scheduler):
        async def task():
            pass

        scheduler.add_recurring("to_cancel", lambda: task(), interval_s=10)
        result = scheduler.cancel("to_cancel")
        assert result is True
        entries = scheduler.list_schedules()
        assert not entries[0].enabled

    def test_upsert_idempotent(self, scheduler):
        async def task():
            pass

        scheduler.add_recurring("dup", lambda: task(), interval_s=10)
        scheduler.add_recurring("dup", lambda: task(), interval_s=20)
        entries = scheduler.list_schedules()
        assert len(entries) == 1
        assert entries[0].interval_s == 20


class TestSchedulerExecution:
    @pytest.mark.asyncio
    async def test_tick_fires_due_task(self, scheduler):
        counter = {"n": 0}

        async def task():
            counter["n"] += 1

        # Add a task that is immediately due (no next_run_at set)
        scheduler.add_recurring("fire_now", lambda: task(), interval_s=1)
        await scheduler._tick()
        assert counter["n"] == 1

    @pytest.mark.asyncio
    async def test_tick_updates_run_count(self, scheduler):
        async def task():
            pass

        scheduler.add_recurring("count_me", lambda: task(), interval_s=1)
        await scheduler._tick()
        entries = scheduler.list_schedules()
        entry = [e for e in entries if e.name == "count_me"][0]
        assert entry.run_count == 1

    @pytest.mark.asyncio
    async def test_oneshot_disables_after_run(self, scheduler):
        async def task():
            pass

        scheduler.add_oneshot("once", lambda: task())
        await scheduler._tick()
        entries = scheduler.list_schedules()
        entry = [e for e in entries if e.name == "once"][0]
        assert not entry.enabled

    @pytest.mark.asyncio
    async def test_failed_task_records_error(self, scheduler):
        async def bad_task():
            raise ValueError("boom")

        scheduler.add_recurring("fail_me", lambda: bad_task(), interval_s=1)
        await scheduler._tick()
        entries = scheduler.list_schedules()
        entry = [e for e in entries if e.name == "fail_me"][0]
        assert "boom" in entry.last_error

    @pytest.mark.asyncio
    async def test_run_and_stop(self, scheduler):
        """Verify run() can start and stop cleanly."""

        async def task():
            pass

        scheduler.add_recurring("stopper", lambda: task(), interval_s=60)

        async def stop_after_tick():
            await asyncio.sleep(0.3)
            await scheduler.stop()

        asyncio.create_task(stop_after_tick())
        await scheduler.run()
        # If we get here, it stopped cleanly
