# [C5-REAL] Exergy-Maximized
"""
CORTEX JIT Compiled Skill: skill-repair
Description: |
"""
import json
import logging

class SkillRepairSkill:
    def __init__(self):
        self.name = "skill-repair"
        self.description = "|"
        self.instructions = "# Skill Repair Assistant\n\nYou have been tasked with fixing a broken agent skill. After you have modified\nthe skill's source files to address the reported error, you MUST update the\n`manifest.json` to reflect that the skill is now repaired.\n\n## Skill Context\n\n-   **Skill ID**: The unique identifier for the skill (e.g., `my-skill`).\n-   **Source Path**: Where the skill's source files are located.\n-   **Installed Path**: Where the skill is installed/replicated.\n-   **Manifest Path**: The absolute path to the `manifest.json` file.\n\n## Repair Procedure\n\n1.  **Analyze Error**: Understand the error message provided in the prompt.\n2.  **Fix Installed Path**: Fix the issue at the installed path. Since some\n    skills have multiple files, you MUST list all files in the skill directory\n    and analyze them collectively to find the root cause (e.g., malformed\n    `SKILL.md`, missing resources, or incorrect sub-scripts).\n3.  **Update Manifest**: Once the fix is applied to ALL relevant files, you MUST\n    update the `manifest.json` at the **Manifest Path**.\n    -   Find the entry for the skill ID in the `skills` object.\n    -   Set `\"status\": \"installed\"`.\n    -   Clear the `\"error\"` field (set to `null` or remove it).\n4.  **Verification**: The UI will automatically detect this change and refresh.\n\n### Manifest Example\n\n```json\n{\n  \"skills\": {\n    \"my-skill\": {\n      \"status\": \"installed\",\n      \"disabled\": false,\n      \"error\": null\n    }\n  }\n}\n```\n"

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
