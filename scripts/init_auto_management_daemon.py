#!/usr/bin/env python3
"""
Sovereign Purge & Management - Auto Management Daemon (Axiom Ω₅)
Prevents CONTEXT_LEDGER overflow by actively monitoring Memory exergy.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import aiosqlite

from cortex.memory.auto_management import LedgerAutoManagementDaemon
from cortex.memory.ledger import EventLedgerL3

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [CORTEX-AUTO-MGMT] %(message)s")
logger = logging.getLogger("init_auto_management_daemon")

DB_PATH = Path("cortex.db")


async def main():
    logger.info("INIT_AUTO_MANAGEMENT_DAEMON ACTIVE")
    logger.info("Starting CORTEX Ledger Auto Management Daemon...")

    # For safety, ensure we are in a directory that has cortex.db, or create it
    # We will use the same DB paths as the rest of the application

    # Check if we should use engine db or local db
    engine_db_path = Path("cortex/engine/cortex.db")
    if engine_db_path.exists():
        target_db = engine_db_path
    else:
        target_db = DB_PATH

    logger.info(f"Target Ledger Database: {target_db}")

    try:
        async with aiosqlite.connect(target_db) as conn:
            ledger = EventLedgerL3(conn)
            await ledger.ensure_table()

            # The user reported 1.2GB overflow. We cap it at 1000 MB (1GB).
            daemon = LedgerAutoManagementDaemon(
                ledger=ledger,
                tenant_id="default",  # Default tenant unless overridden
                max_db_size_mb=1000.0,
                retain_limit=1000,
                archive_path=str(target_db.parent / "cortex_archive.db"),
                check_interval_seconds=60,
            )

            daemon.start()

            # Handle graceful shutdown
            loop = asyncio.get_running_loop()
            stop_event = asyncio.Event()

            def _shutdown():
                logger.info("Shutdown signal received. Stopping daemon...")
                daemon.stop()
                stop_event.set()

            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _shutdown)

            logger.info("Daemon is now ACTIVE and monitoring background exergy.")

            # Wait until interrupted
            await stop_event.wait()

    except Exception as e:
        logger.error(f"Daemon failed to start or crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Auto Management Daemon shutdown complete.")
