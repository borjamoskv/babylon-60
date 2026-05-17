import unittest
import os
import json
import tempfile
from cortex.engine.cot_modulator import SovereignModulator


class TestSovereignModulator(unittest.TestCase):
    def setUp(self):
        # Create a temporary mock ledger for C5-REAL verification
        self.test_dir = tempfile.TemporaryDirectory()
        self.ledger_path = os.path.join(self.test_dir.name, "test_ledger.jsonl")
        self.modulator = SovereignModulator(ledger_path=self.ledger_path)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_default_o1_mode(self):
        # No history for this target -> should default to O(1)
        self.assertFalse(self.modulator.should_use_cot("new-target-001"))

    def test_forced_cot_on_friction(self):
        # Create a high-value unverified entry in the mock ledger
        with open(self.ledger_path, "w") as f:
            f.write(
                json.dumps(
                    {"target_id": "risky-target-99", "max_bounty_usd": 150000, "verified_count": 0}
                )
                + "\n"
            )

        # Modulator should detect friction and force CoT
        self.assertTrue(self.modulator.should_use_cot("risky-target-99"))

    def test_o1_on_verified_target(self):
        # Create a verified entry
        with open(self.ledger_path, "w") as f:
            f.write(
                json.dumps(
                    {"target_id": "safe-target-01", "max_bounty_usd": 50000, "verified_count": 5}
                )
                + "\n"
            )

        # Target is verified -> O(1) mode
        self.assertFalse(self.modulator.should_use_cot("safe-target-01"))

    def test_wrap_proposal(self):
        proposal = {"action": "MINT", "target": "0x123"}
        wrapped = self.modulator.wrap_proposal(proposal, use_cot=True)
        self.assertEqual(wrapped["meta"]["execution_mode"], "SAGA_REASONING")
        self.assertTrue(wrapped["meta"]["truth_anchored"])


if __name__ == "__main__":
    unittest.main()
