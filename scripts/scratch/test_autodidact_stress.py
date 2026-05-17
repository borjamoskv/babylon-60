"""Stress Test for AUTODIDACT L3+."""

import asyncio
import json
import logging
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

from cortex.engine.onchain_executor import SovereignExecutor
from cortex.engine.pdr_guard import PDRGuard
from cortex.engine.tis_schema import CortexTIS, TISOperation
from cortex.ledger.ledger_core import SovereignLedger

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("stress_test")

import os

NUM_AGENTS = int(os.environ.get("CORTEX_INTENSITY", 50))
ledger_lock = asyncio.Lock()


async def agent_task(agent_id: int, ledger: SovereignLedger, guard: PDRGuard, private_key: str):
    executor = SovereignExecutor(private_key=private_key)
    tis = CortexTIS(
        chain_id=31337,
        target_contract="0x1111111111111111111111111111111111111111",
        operations=[TISOperation(type="transfer", calldata="0x", value="1")],
        taint_hash="0x" + uuid.uuid4().hex + uuid.uuid4().hex,
    )

    try:
        # 1. Sign the TIS
        pdr = await asyncio.to_thread(guard.evaluate_and_sign, tis)

        # 2. Execute On-Chain
        tx_hashes = await asyncio.to_thread(executor.execute_intent, tis, pdr)

        if not tx_hashes:
            return False

        # 3. Record in Ledger
        detail_json = json.dumps(
            {
                "tis": tis.model_dump(mode="json"),
                "pdr": pdr.model_dump(mode="json"),
                "tx_hashes": tx_hashes,
            }
        )

        # We must use a lock for SQLite :memory: DB concurrent writes
        async with ledger_lock:
            await asyncio.to_thread(
                ledger.record_transaction, f"agent_{agent_id}", "EXECUTE_INTENT", detail_json
            )
        return True
    except Exception as e:
        logger.error("Agent %d failed: %s", agent_id, e)
        return False


async def main_async():
    logger.info("Starting local Anvil node with %d accounts...", NUM_AGENTS)
    anvil_proc = subprocess.Popen(
        ["anvil", "--port", "8545", "--block-time", "1", "--accounts", str(NUM_AGENTS)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    try:
        # Derive unique keys for each agent
        from eth_account import Account

        Account.enable_unaudited_hdwallet_features()
        mnemonic = "test test test test test test test test test test test junk"
        agent_keys = [
            "0x" + Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}").key.hex()
            for i in range(NUM_AGENTS)
        ]

        db = sqlite3.connect(":memory:", check_same_thread=False)
        ledger = SovereignLedger(db)

        key_path = Path("/tmp/test_guard.key")
        if key_path.exists():
            key_path.unlink()
        guard = PDRGuard(key_path)

        logger.info("Injecting %d concurrent transactions (Sovereign Swarm)...", NUM_AGENTS)
        start_time = time.time()

        tasks = [agent_task(i, ledger, guard, agent_keys[i]) for i in range(NUM_AGENTS)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time
        successes = sum(1 for r in results if r)
        tps = successes / duration if duration > 0 else 0

        logger.info("=== STRESS TEST RESULTS ===")
        logger.info("Total Time: %.2f seconds", duration)
        logger.info("Successes: %d / %d", successes, NUM_AGENTS)
        logger.info("Throughput (TPS): %.2f", tps)

    finally:
        logger.info("Shutting down local Anvil node...")
        anvil_proc.terminate()
        anvil_proc.wait()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
