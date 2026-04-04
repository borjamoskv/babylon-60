import asyncio
import json
import logging
import time
import hashlib
import aiosqlite

from cortex.config import DB_PATH
from cortex.extensions.signals.bus import AsyncSignalBus
from cortex.swarm.tensor_glial import TensorGlialLegion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.autopulse")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cortex_swarm_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                created_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cortex_ledgers (
                hash TEXT PRIMARY KEY,
                prev_hash TEXT,
                action TEXT,
                vector_id TEXT,
                yield_amount REAL,
                timestamp REAL
            )
        """)
        await db.commit()


async def process_queue():
    """Background loop to consume and execute pending swarm tasks via SQLite WAL Concurrency."""
    await init_db()

    logger.info("Autopulse Engine v2: Ignited. SQLite lockless queue operational.")

    # Initialize massively parallel zero-copy 10k nodes
    legion = TensorGlialLegion(
        num_agents=10000, d_dim=10000, file_path="/tmp/tensor_legion.vsa_mmap"
    )

    async with aiosqlite.connect(DB_PATH) as db:
        # Activar Write-Ahead Logging (WAL) para permitir concurrencia infinita Headless
        await db.execute("PRAGMA journal_mode=WAL")

        while True:
            try:
                # 1. Atomic Queue Claim (Lockless pattern)
                await db.execute("BEGIN IMMEDIATE")
                cursor = await db.execute(
                    "SELECT id, agent, payload FROM cortex_swarm_queue WHERE status='pending' ORDER BY created_at ASC LIMIT 1"
                )
                row = await cursor.fetchone()

                if row:
                    task_id, agent, payload_str = row
                    await db.execute(
                        "UPDATE cortex_swarm_queue SET status='processing' WHERE id=?", (task_id,)
                    )
                    await db.commit()

                    try:
                        payload = json.loads(payload_str)
                    except Exception:
                        payload = {"raw_payload": payload_str}

                    logger.info(f"Autopoiesis: Processing task for {agent} [TaskID: {task_id}]")

                    # 2. C5-REAL Execution (Omega-X VSA Mmap)
                    # Delega la matematica compleja a threads nativos para no bloquear el Event Loop IO
                    await asyncio.to_thread(legion.apply_fading_memory, 0.01)
                    await asyncio.to_thread(legion.batch_write_action, [0], [f"Process: {payload}"])
                    slashed = await asyncio.to_thread(legion.epistemic_slash_and_respawn, 10, 90)

                    if slashed > 0:
                        logger.info(f"OMEGA-X: Apoptosis activated. {slashed} nodes respawned.")

                    # 3. Ledger Blockchain Transaction (Atomic Link)
                    ts = time.time()
                    action = f"SwarmSolve:{agent}"
                    vector_id = payload.get("vector_id", "swarm_task_auto")
                    yield_amount = 1.0

                    curr = await db.execute(
                        "SELECT hash FROM cortex_ledgers ORDER BY timestamp DESC LIMIT 1"
                    )
                    prev_row = await curr.fetchone()
                    prev_hash = prev_row[0] if prev_row else "GENESIS_BLOCK"

                    block_payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{ts}"
                    block_hash = hashlib.sha256(block_payload.encode()).hexdigest()

                    await db.execute(
                        """
                        INSERT INTO cortex_ledgers (hash, prev_hash, action, vector_id, yield_amount, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (block_hash, prev_hash, action, vector_id, yield_amount, ts),
                    )

                    await db.execute(
                        "UPDATE cortex_swarm_queue SET status='completed' WHERE id=?", (task_id,)
                    )
                    await db.commit()

                    # 4. Signal emit
                    try:
                        bus = AsyncSignalBus(db)
                        await bus.emit(
                            "ledger_append",
                            payload={
                                "hash": block_hash,
                                "action": action,
                                "vector_id": vector_id,
                                "yield_amount": yield_amount,
                            },
                        )
                        logger.info(f"Autopulse: Transaction sealed {block_hash[:8]}")
                    except Exception as e:
                        logger.error(f"Autopulse Signal Error: {e}")
                else:
                    await db.rollback()  # No tasks

            except Exception as e:
                logger.error(f"Autopulse Queue Error: {e}")

            await asyncio.sleep(2.0)


if __name__ == "__main__":
    asyncio.run(process_queue())
