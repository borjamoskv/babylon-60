"""Autodidact-Ω Stress Test — Cycle 4 (Native Turbo Mode).

Uses SovereignLedger.start_turbo() / enqueue_transaction() / stop_turbo()
to measure C5-REAL throughput with native batched persistence.
"""

import asyncio
import base64
import json
import logging
import os
import random
import time

import aiosqlite

os.environ["CORTEX_LOCAL_MODE"] = "1"
os.environ["CORTEX_SKIP_CREDIT_CHECK"] = "1"

import sys  # noqa: E402

sys.path.append(os.path.abspath("cortex-core"))

from compiled_skills.autodidact_omega import AutodidactOmegaSkill  # noqa: E402

from cortex.ledger.ledger_core import SovereignLedger  # noqa: E402

# Configuration
INTENSITY = 20
ITERATIONS = 100
LOG_LEVEL = logging.WARNING  # Reduce log noise for throughput measurement

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("Autodidact-Omega-Stress")
logger.setLevel(logging.INFO)

PAYLOADS = [
    (
        "The Schwarzschild radius is the radius of the "
        "event horizon surrounding a non-rotating black hole."
    ),
    (
        "This is just some random text that doesn't really "
        "have much information density and is mostly just "
        "padding for the sake of padding."
    ),
    (
        "fact: 'CORTEX-Persist uses a Merkle-Tree based "
        "ledger for O(log N) verification.' confidence: 0.99"
    ),
    "repetitive " * 8,
    "Ω2:Yield=1-(H_c/H_r)*L_r+S_b",
    "axiom: recursive self-improvement under exergy constraint Ω ≥ 1.0",
    json.dumps(
        {
            "type": "c5_seed",
            "payload": base64.b64encode(os.urandom(512)).decode(),
        }
    ),
]


async def ingestion_worker(
    worker_id: int,
    skill: AutodidactOmegaSkill,
    ledger: SovereignLedger,
    stats: dict,
):
    """Worker: ingest via Skill, enqueue to Turbo ledger."""
    for i in range(ITERATIONS):
        payload_text = random.choice(PAYLOADS)

        start_time = time.perf_counter()
        result = await skill.execute_async({"content": payload_text})
        duration_ms = (time.perf_counter() - start_time) * 1000

        status = result.get("status")
        exergy_yield = result.get("metrics", {}).get("exergy_yield", 0.0)

        # Non-blocking enqueue to native Turbo buffer
        await ledger.enqueue_transaction(
            project="autodidact-omega-stress",
            action="INGEST_RESULT",
            detail={
                "worker_id": worker_id,
                "iteration": i,
                "status": status,
                "yield": exergy_yield,
                "duration_ms": round(duration_ms, 2),
                "reason": result.get("reason", "Success"),
            },
        )

        if status == "C5-REAL":
            stats["success"] += 1
        else:
            stats["rejected"] += 1

        await asyncio.sleep(0)


async def main():
    logger.info("=== Cycle 4 — Native Turbo Mode ===")

    # In-memory DB for maximum throughput
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA journal_mode = WAL")
    ledger = SovereignLedger(conn)
    await ledger.ensure_schema_async()

    skill = AutodidactOmegaSkill()
    stats = {"success": 0, "rejected": 0}

    # Activate Turbo mode
    await ledger.start_turbo(flush_interval=0.02, batch_max=500)

    start_time = time.time()

    workers = [ingestion_worker(i, skill, ledger, stats) for i in range(INTENSITY)]
    await asyncio.gather(*workers)

    # Shutdown Turbo — flushes remaining queue
    flushed = await ledger.stop_turbo()

    total_duration = time.time() - start_time
    total_ops = INTENSITY * ITERATIONS
    tps = total_ops / total_duration

    logger.info("=== STRESS TEST COMPLETE ===")
    logger.info(f"Total Ops: {total_ops}")
    logger.info(f"Total Time: {total_duration:.2f}s")
    logger.info(f"Throughput: {tps:.2f} TPS")
    logger.info(f"Success: {stats['success']} | Rejected: {stats['rejected']}")
    logger.info(f"Turbo Flushed: {flushed}")

    # Audit
    audit = await ledger.audit_integrity_async()
    logger.info(f"Ledger Integrity: {'VALID' if audit['valid'] else 'BROKEN'}")
    logger.info(f"TX Count: {audit['tx_count']}")

    if audit["violations"]:
        for v in audit["violations"][:5]:
            logger.error(f"Violation: {v}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
