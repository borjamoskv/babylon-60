import json
import logging
from swarm_manager import SwarmActuator
from telemetry_gate import TelemetryGate

import os
from pathlib import Path

# Force working directory to the script's parent directory to resolve dummy files correctly
os.chdir(Path(__file__).parent)

logging.basicConfig(level=logging.INFO)

db_path = "cortex_memory_vsa.db"
actuator = SwarmActuator(db_path)
gate = TelemetryGate(actuator)

# 1. A Valid Patch that doesn't break the tests
print("--- TEST 1: VALID PATCH ---")
valid_patch = json.dumps({
    "type": "AST_MUTATION",
    "target_file": "dummy_gate.py",
    "new_source": "def add(a, b):\n    # Optimized via Swarm\n    return a + b\n",
    "yield_amount": 10.0,
    "thermodynamic_justification": "Added optimization comment."
})
success = gate.process_external_patch("Claude-3.7", valid_patch)
print(f"Result 1 (Expected True): {success}")

# 2. A Failing Patch that breaks the tests
print("\n--- TEST 2: FAILING PATCH ---")
failing_patch = json.dumps({
    "type": "AST_MUTATION",
    "target_file": "dummy_gate.py",
    "new_source": "def add(a, b):\n    # Sabotaged by Hallucinating Agent\n    return a - b\n",
    "yield_amount": 100.0,
    "thermodynamic_justification": "Used subtraction."
})
success = gate.process_external_patch("GPT-4-Legacy", failing_patch)
print(f"Result 2 (Expected False): {success}")

import os
from pathlib import Path

dummy_path = Path(__file__).parent / "dummy_gate.py"

# Check original file
with open(dummy_path) as f:
    content = f.read()
    print(f"\nFinal dummy_gate.py content:\n{content}")

