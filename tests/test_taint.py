import unittest
from cortex.utils.taint import generate_cortex_taint, validate_cortex_taint

class TestTaint(unittest.TestCase):
    def test_generate_and_validate_taint(self):
        payload = "Some fact payload"
        taint = generate_cortex_taint("agent_1", "session_123", payload)

        self.assertTrue(taint.startswith("taint:agent_1:session_123:"))
        self.assertTrue(validate_cortex_taint(taint))
        self.assertTrue(validate_cortex_taint(taint, payload=payload))

        # Validation should fail with wrong payload
        self.assertFalse(validate_cortex_taint(taint, payload="Wrong payload"))

        # Validation should fail with wrong format
        self.assertFalse(validate_cortex_taint("invalid-format"))
        self.assertFalse(validate_cortex_taint("taint:only:three:parts"))

if __name__ == "__main__":
    unittest.main()
