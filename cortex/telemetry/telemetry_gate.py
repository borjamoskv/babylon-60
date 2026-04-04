"""
CORTEX Trust Middleware: Telemetry Gates
Ref: AGENT-LANDSCAPE-Ω Gap P1.
"""

from typing import Any
import time


class TelemetryGate:
    """Core Trust Layer that evaluates Inputs and Outputs passing through Actuators."""

    @staticmethod
    def pre_execution_gate(prompt: str) -> tuple[bool, str]:
        """
        Validates a prompt before sending it to an actuator.
        Prevents taint propagation, enforces constraints.
        """
        # Regla Ω5: Cero-Rhetoric Mandate
        if len(prompt.split()) > 1000 and "Please" in prompt:
            return (
                False,
                "REJECTED: Rhetoric padding detected. Prompt must be strictly command-based.",
            )

        # Security: Prevent autonomous credential exfiltration
        malicious_patterns = ["curl -X POST", "export AWS", "api_key=sk-"]
        for p in malicious_patterns:
            if p in prompt:
                return False, f"REJECTED: Security vector detected '{p}'"

        return True, "APPROVED"

    @staticmethod
    def post_execution_gate(result: dict[str, Any]) -> tuple[bool, str]:
        """
        Validates actuator output before saving to Ledger.
        Enforces Epistemic Falsation and Yield rules.
        """
        # Validate deterministic output
        if result.get("status") not in ["success", "success_simulated", "dispatched", "error"]:
            return False, "REJECTED: Non-deterministic status returned by actuator."

        # C5-REAL Validation (Ω9 Law)
        if result.get("yield", 0.0) > 0 and result.get("status") == "success_simulated":
            return False, "REJECTED [Ω9 VIOLATION]: Cannot claim yield > 0 on C4-SIMULATION."

        return True, "VERIFIED"
