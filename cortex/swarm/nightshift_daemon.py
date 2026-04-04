"""
CORTEX Nightshift Daemon
Dispatcher central asíncrono para delegación masiva (Actuadores Múltiples)
"""

import sys
import os
import time

# Asumimos rutas relativas si se ejecuta desde python module (-m) o importando localmente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.manager import ActuatorFactory
from telemetry.telemetry_gate import TelemetryGate


class NightshiftDaemon:
    def __init__(self):
        self.is_running = False
        self.mission_queue = [
            {
                "intent": "code_audit",
                "prompt": "Execute autonomous_fuzzing in target repo",
                "context": {
                    "urgency": "high",
                    "target_dir": "/Users/borjafernandezangulo/30_CORTEX/.scratch/community-staking-module",
                    "match_path": "test/ValidationMitigation.t.sol",
                },
            }
        ]
        self.completed = []

    def start_pulse(self):
        """Simulates a Daemon execution tick (Pulse)"""
        self.is_running = True
        print("[NIGHTSHIFT:ONLINE] Demonio iniciado. Leyendo Misiones...")

        while self.mission_queue:
            mission = self.mission_queue.pop(0)
            intent, prompt = mission["intent"], mission["prompt"]

            print(f"\\n[NIGHTSHIFT] Dispatching Mission: {intent}")

            # 1. Pre-Gate Verification
            valid, msg = TelemetryGate.pre_execution_gate(prompt)
            if not valid:
                print(f"[GATE:BLOCKED] {msg}")
                continue

            # 2. Select Actuator via AAL
            actuator = ActuatorFactory.get_actuator(intent)

            # 3. Execute
            print(f"[AAL] Encaminando a actuador: {type(actuator).__name__}")
            result = actuator.execute_task(prompt, context={"urgency": "medium"})

            # 4. Post-Gate Verification
            valid, msg = TelemetryGate.post_execution_gate(result)
            if not valid:
                print(f"[GATE:BLOCKED] {msg}")
                continue

            # 5. Commit to Ledgers / Local State
            self.completed.append({"mission": mission, "result": result})
            print("[LEDGER:COMMITTED] Resultado verificado y guardado.")

            time.sleep(0.5)  # Async dispatcher rhythm

        print("\\n[NIGHTSHIFT:HALTED] Cola vacía. Durmiendo...")


if __name__ == "__main__":
    daemon = NightshiftDaemon()
    daemon.start_pulse()
