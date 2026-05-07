"""Autonomous Tombstone Monitor."""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from cortex.extensions.daemon.models import TombstoneAlert

logger = logging.getLogger("moskv-daemon")


class TombstoneMonitor:
    """Reports logically tombstoned facts during the late-night maintenance window.

    Physical fact deletion requires a tenant-scoped canonical purge ledger. This
    monitor is intentionally read-only and emits an alert when legacy deletion
    would have run.
    """

    def __init__(
        self,
        db_path: Path | str,
        interval_seconds: int = 3600,  # check every hour
        start_hour: int = 3,  # 03:00 UTC
        end_hour: int = 5,  # 05:00 UTC
    ):
        self.db_path = Path(db_path)
        self.interval_seconds = interval_seconds
        self.start_hour = start_hour
        self.end_hour = end_hour
        self._last_run: float = 0

    def _in_maintenance_window(self) -> bool:
        """Check if current UTC time is within the maintenance window."""
        now = datetime.now(timezone.utc)
        return self.start_hour <= now.hour < self.end_hour

    def check(self) -> list[TombstoneAlert]:
        """Run physical sweep if in maintenance window and interval elapsed."""
        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        if not self._in_maintenance_window():
            return []

        if not self.db_path.exists():
            return []

        self._last_run = now

        try:
            from cortex.database.core import connect as db_connect

            # Fix HIGH-005 lock contention: use auto-commit mode (isolation_level=None)
            # to avoid taking a write-lock on the first SELECT. We'll manage transactions manually.
            with db_connect(
                self.db_path,  # type: ignore[type-error]
                timeout=5,
                isolation_level=None,  # Manual transaction control
            ) as conn:
                cursor = conn.cursor()

                # Get count of facts to sweep
                cursor.execute("SELECT COUNT(*) FROM facts WHERE is_tombstoned = 1")
                to_delete = cursor.fetchone()[0]

                if to_delete == 0:
                    return []

                logger.error(
                    "TombstoneMonitor: blocked physical deletion of %d tombstoned facts; "
                    "canonical tenant-scoped purge ledger required.",
                    to_delete,
                )

                return [
                    TombstoneAlert(
                        deleted_facts=0,
                        freed_mb=0.0,
                        message=(
                            "Tombstone sweep blocked: "
                            f"{to_delete} facts require canonical tenant-scoped purge."
                        ),
                    )
                ]

        except (ValueError, OSError, RuntimeError, sqlite3.Error) as e:
            logger.error("Tombstone Sweep failed: %s", e)
            return []
