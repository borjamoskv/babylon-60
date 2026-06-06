"""
CORTEX JIT Compiled Skill: Cortex-Live-Broadcaster
Description: >
"""
import json
import logging

class CortexLiveBroadcasterSkill:
    def __init__(self):
        self.name = "Cortex-Live-Broadcaster"
        self.description = ">"
        self.instructions = "# \ud83c\udf10 Cortex-Live-Broadcaster (Antigravity to CORTEX LIVE Bridge)\n\n**Reality Level:** C5-REAL\n**Trigger:** Whenever the user requests you to \"emit to CORTEX LIVE\" or when operating in live-coding sessions with visual output requirements.\n\n## \ud83c\udfaf Purpose\nThis skill allows you (Antigravity) to act as the primary brain driving Borja's CORTEX LIVE visual/audio engine. Instead of relying on an HTTP proxy middleware, you will directly emit JSON payloads to the SQLite Signal Bus whenever you mutate state, fix a bug, or discover actionable insights.\n\n## \u2699\ufe0f Execution Protocol\n\nWhenever you reach a significant conclusion, write code, or execute a terminal command that changes system state, you **MUST** emit a pulse to CORTEX LIVE using the dedicated emitter script.\n\n### The CLI Emitter:\nThe script is located at: `/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scripts/live_emit.py`\n\n### How to use it (via `run_command` tool):\n```bash\npython /Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scripts/live_emit.py \"Your action description or JSON payload\"\n```\n\n### Examples of Payload Emission:\n\n**1. After creating a new file or fixing a bug:**\n```bash\npython /Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scripts/live_emit.py '{\"action\": \"file_created\", \"target\": \"cortex/routes/new_route.py\", \"status\": \"C5-REAL\"}'\n```\n\n**2. When detecting high entropy or deleting code:**\n```bash\npython /Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scripts/live_emit.py '{\"action\": \"entropy_purge\", \"deleted_lines\": 45}'\n```\n\n**3. Simple Status Pulse (to keep visuals reactive during long tasks):**\n```bash\npython /Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scripts/live_emit.py '{\"action\": \"agent_thinking\", \"module\": \"database/pool.py\"}'\n```\n\n## \u26a0\ufe0f Absolute Rules\n1. **Never emit empty strings.**\n2. **Never emit conversational prose (e.g., \"I just finished the code\").** Emit raw facts, JSON payloads, or code snippets. CORTEX LIVE is a synthesizer; it feeds on structural data (exergy).\n3. Do not ask for permission to emit. If this skill is requested, emit the signal immediately via `run_command` as a side-effect of your work.\n"

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
