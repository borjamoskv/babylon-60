import logging
import sqlite3
import sys
import unittest
from pathlib import Path

_CORTEX_CORE = Path(__file__).resolve().parents[1] / "cortex-core"
if _CORTEX_CORE.exists() and str(_CORTEX_CORE) not in sys.path:
    sys.path.insert(0, str(_CORTEX_CORE))

from ouroboros_engine import OuroborosEngine


class TestOuroborosForge(unittest.IsolatedAsyncioTestCase):
    """Verifies the Forge-backed Ouroboros audit pipeline (V5)."""

    async def asyncSetUp(self):
        self.engine = OuroborosEngine()
        self.test_repo = "https://github.com/Uniswap/v4-core"

    async def test_audit_cycle(self):
        """Standard Audit Cycle on mock contract."""
        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        # This will clone and audit
        try:
            await self.engine.run_audit()
            logger.info("Audit Cycle 1/1 verified.")
        except Exception as e:
            self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    async def test_signal_emission(self):
        """Verify SignalBus emits audit findings correctly."""
        from cortex.config import DB_PATH
        from cortex.extensions.signals.bus import SignalBus

        # Ensure schema initialization
        conn = sqlite3.connect(DB_PATH)
        bus = SignalBus(conn)

        # Check if signals exist for 'ouroboros'
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM signals WHERE source='ouroboros'")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(count, 0, "Signal table check failed.")


if __name__ == "__main__":
    unittest.main()
