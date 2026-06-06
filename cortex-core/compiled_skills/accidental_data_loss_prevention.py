"""
CORTEX JIT Compiled Skill: accidental-data-loss-prevention
Description: |
"""
import json
import logging

class AccidentalDataLossPreventionSkill:
    def __init__(self):
        self.name = "accidental-data-loss-prevention"
        self.description = "|"
        self.instructions = "# Accidental Data Loss Prevention\n\n> [!CAUTION]\n>\n> **STOP AND VERIFY**: Before running any command or tool that results in\n> irreversible data loss, you **MUST** obtain explicit user consent.\n\n## Mandatory Procedure\n\n1.  **Halt Execution**: Do **not** execute the command.\n2.  **Request Consent**: Explain clearly to the user:\n    -   The **impact** of this deletion.\n    -   **Why** you believe this is necessary.\n    -   A request for their **explicit approval** to proceed.\n3.  **Wait**: Only proceed if the user provides clear, affirmative consent in\n    the conversation.\n"

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        """
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        """
        logging.info(f"[{self.name}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload
        }
