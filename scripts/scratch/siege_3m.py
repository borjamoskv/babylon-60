"""
CORTEX — 3M Agent Siege (Fase II Stress Test).
Simula la carga de 3 millones de agentes operando en paralelo sobre el ledger nativo.
"""

import asyncio
import logging
import os
import random
import sys
import time

import aiosqlite

# Entorno
os.environ["CORTEX_LOCAL_MODE"] = "1"
os.environ["CORTEX_SKIP_CREDIT_CHECK"] = "1"
sys.path.append(os.path.abspath("cortex-core"))

from compiled_skills.autodidact_omega import AutodidactOmegaSkill

from cortex.ledger.ledger_core import SovereignLedger

# Configuración Masiva
INTENSITY = 50  # Workers concurrentes
TOTAL_TARGET = 3_000_000
ITERATIONS_PER_WORKER = TOTAL_TARGET // INTENSITY

DB_PATH = "siege_3m.db"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("3M-Siege")
logger.setLevel(logging.INFO)

PAYLOADS = [
    "fact: 'Autonomy L3 is the production standard.'",
    "Ω2:Yield=1-(H_c/H_r)",
    "Thermal noise padding " * 5,
    "axiom: recursive self-improvement",
]


async def siege_worker(worker_id, skill, ledger, stats):
    for i in range(ITERATIONS_PER_WORKER):
        payload = random.choice(PAYLOADS)

        # Simulación de carga cognitiva (O1 Crystallization)
        # En este test masivo, medimos la capacidad del LEDGER,
        # por lo que usamos el fast-path del skill.
        result = await skill.execute_async({"content": payload})

        await ledger.enqueue_transaction(
            project="siege-3m",
            action="INGEST",
            detail={"w": worker_id, "i": i, "y": result["metrics"]["exergy_yield"]},
        )
        stats["count"] += 1

        if i % 5000 == 0:
            logger.info(f"Worker {worker_id} reached {i} iterations...")

        await asyncio.sleep(0)


async def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    logger.info(f"=== INICIANDO ASEDIO: {TOTAL_TARGET} AGENTES ===")

    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA synchronous = NORMAL")

        ledger = SovereignLedger(conn)
        await ledger.ensure_schema_async()

        skill = AutodidactOmegaSkill()
        stats = {"count": 0}

        # Turbo ultra-agresivo para 3M
        await ledger.start_turbo(flush_interval=0.05, batch_max=5000)

        start_time = time.time()

        workers = [siege_worker(i, skill, ledger, stats) for i in range(INTENSITY)]

        # Monitoreo de progreso
        async def monitor():
            while stats["count"] < TOTAL_TARGET:
                elapsed = time.time() - start_time
                tps = stats["count"] / max(1, elapsed)
                logger.info(f"PROGRESO: {stats['count']:,} / {TOTAL_TARGET:,} | TPS: {tps:.2f}")
                await asyncio.sleep(2)

        monitor_task = asyncio.create_task(monitor())

        await asyncio.gather(*workers)

        await ledger.stop_turbo()
        monitor_task.cancel()

        total_time = time.time() - start_time
        final_tps = TOTAL_TARGET / total_time

        logger.info("=== ASEDIO COMPLETADO ===")
        logger.info(f"Tiempo Total: {total_time:.2f}s")
        logger.info(f"Throughput Final: {final_tps:.2f} TPS")
        logger.info(f"DB Size: {os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB")

        # Auditoría rápida
        audit = await ledger.audit_integrity_async()
        logger.info(f"Ledger Integrity: {'VALID' if audit['valid'] else 'BROKEN'}")


if __name__ == "__main__":
    asyncio.run(main())
