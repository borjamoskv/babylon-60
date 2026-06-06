"""
CORTEX JIT Compiled Skill: managing-python-dependencies
Description: |
"""
import json
import logging

class ManagingPythonDependenciesSkill:
    def __init__(self):
        self.name = "managing-python-dependencies"
        self.description = "|"
        self.instructions = "# Python Dependency Management Rule\n\n> [!CAUTION] **BEFORE any `pip install`**: You MUST first detect the project's\n> existing dependency manager and use it correctly. Do NOT override the\n> project's established tooling.\n\n## Dependency Manager Detection\n\nBefore installing ANY Python package, check the workspace for these files **in\npriority order**:\n\n1.  **Signal:** `uv.lock` or `pyproject.toml` with `[tool.uv]`\n    *   **Tool:** **uv**\n    *   **Install:** `uv add <package>`\n    *   **Setup:** `uv sync`\n2.  **Signal:** `pyproject.toml` with `[tool.poetry]`\n    *   **Tool:** **Poetry**\n    *   **Install:** `poetry add <package>`\n    *   **Setup:** `poetry install`\n3.  **Signal:** `Pipfile`\n    *   **Tool:** **Pipenv**\n    *   **Install:** `pipenv install <package>`\n    *   **Setup:** `pipenv install`\n4.  **Signal:** `environment.yml`\n    *   **Tool:** **Conda**\n    *   **Install:** `conda install <package>`\n    *   **Setup:** `conda env create -f environment.yml`\n5.  **Signal:** `requirements.txt` only\n    *   **Tool:** **venv + pip**\n    *   **Install:** `.venv/bin/pip install <package>`\n    *   **Setup:** `.venv/bin/pip install -r requirements.txt`\n6.  **Signal:** None of the above\n    *   **Tool:** **venv + pip** (default)\n    *   **Install:** `.venv/bin/pip install <package>`\n    *   **Setup:** `.venv/bin/pip install -r requirements.txt`\n\n## Default: venv + pip\n\nIf no dependency manager is detected, use **venv + pip + requirements.txt** as\nthe default:\n\n```bash\n# Initialize environment\npython3 -m venv .venv\n\n# Add dependencies\n.venv/bin/pip install <package>\n\n# Preserve state\n.venv/bin/pip freeze > requirements.txt\n```\n\n**Rules for venv + pip workflow:**\n\n-   Always use `.venv/bin/pip` or `.venv/bin/python` (explicit path).\n-   After installing, run: `.venv/bin/pip freeze > requirements.txt`.\n-   When setting up: `.venv/bin/pip install -r requirements.txt`.\n\n## Prohibited\n\n-   **NEVER** run `pip install` globally\n-   **NEVER** override an existing dependency manager with a different one\n"

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
