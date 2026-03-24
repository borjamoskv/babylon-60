import json

import aiosqlite
import pytest

from cortex.engine.ledger import SovereignLedger
from cortex.swarm.actuators.protocol import ActuatorResponse
from cortex.swarm.manager import SwarmManager


class MockActuator:
    @property
    def provider_id(self) -> str:
        return "mock-agent"

    async def execute(self, task: str, context: dict) -> ActuatorResponse:
        return ActuatorResponse(content="Hello World", metadata={})

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_swarm_ledger_integration():
    # Setup in-memory ledger using aiosqlite
    async with aiosqlite.connect(":memory:") as db:
        # Create schema for transactions if needed, though record_transaction handles it?
        # Wait, the ledger expects the table to exist or it will fail on SELECT.
        await db.execute(
            "CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, action TEXT, detail TEXT, prev_hash TEXT, hash TEXT, timestamp TEXT, tenant_id TEXT)"
        )
        await db.execute(
            "CREATE TABLE merkle_roots (id INTEGER PRIMARY KEY AUTOINCREMENT, root_hash TEXT, tx_start_id INTEGER, tx_end_id INTEGER, tx_count INTEGER)"
        )

        ledger = SovereignLedger(db)
        manager = SwarmManager(ledger=ledger)
        actuator = MockActuator()
        manager.register_actuator("agent-1", actuator)

        # Dispatch task with sensitive info
        await manager.dispatch("agent-1", "My secret is admin@cortex.com")

        # Verify Ledger transactions
        async with db.execute("SELECT action, detail FROM transactions ORDER BY id ASC") as cursor:
            txs = await cursor.fetchall()

        assert len(txs) >= 2
        assert txs[0][0] == "dispatch_attempt"
        assert txs[1][0] == "execution_success"
        # Verify that privacy was masked in the log record (hash of sanitized vs original)
        row = txs[0]
        detail = json.loads(row[1])
        assert "task_hash" in detail
        assert "sanitized_task_hash" in detail
        assert detail["task_hash"] != detail["sanitized_task_hash"]
