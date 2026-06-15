# [C5-REAL] Exergy-Maximized
"""
CORTEX - Structural Isolation Guard.

A pre-processing middleware that enforces the isolation of the structural core 
from contaminating narrative (e.g. prompt preambles).
Validates artifacts using regex to strip noise, checking for template variables,
and strictly aborting execution if the payload lacks exergic density,
logging failures into .cortex_ledger.json.
"""

import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger("cortex.guards.isolation")

class StructuralIsolationGuard:
    """Enforces the extraction and validation of pure structural prompts."""
    
    LEDGER_PATH = ".cortex_ledger.json"

    def __init__(self, workspace_dir: str = "."):
        self.ledger_file = os.path.join(workspace_dir, self.LEDGER_PATH)

    def _log_failure(self, reason: str, payload_preview: str):
        """Logs a structural failure securely into the C5-REAL ledger."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "STRUCTURAL_ISOLATION_FAILURE",
            "reason": reason,
            "payload_preview": payload_preview[:200]
        }
        
        try:
            if os.path.exists(self.ledger_file):
                with open(self.ledger_file, "r") as f:
                    try:
                        ledger = json.load(f)
                    except json.JSONDecodeError:
                        ledger = {}
            else:
                ledger = {}
                
            if isinstance(ledger, list):
                ledger = {"legacy_entries": ledger}
                
            if "isolation_failures" not in ledger:
                ledger["isolation_failures"] = []
                
            ledger["isolation_failures"].append(entry)
            
            with open(self.ledger_file, "w") as f:
                json.dump(ledger, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write to ledger: {e}")

    def isolate_and_validate(self, raw_artifact: str) -> str:
        """
        Strips contamination from the artifact and validates the core structure.
        
        Raises:
            ValueError: If structural validation fails or entropy is too high.
        """
        # 1. Regex-based isolation of core elements
        core_matches = re.findall(
            r"(<system>.*?</system>|<instructions>.*?</instructions>|<rules>.*?</rules>|\{\{.*?\}\})", 
            raw_artifact, 
            re.DOTALL
        )
        
        if not core_matches:
            # Attempt a broader extraction if tags are just loose but present
            core_matches = re.findall(r"(<[a-z_]+>.*?</[a-z_]+>)", raw_artifact, re.DOTALL)
        
        if not core_matches:
            self._log_failure("Anergía Total: No structural tags found.", raw_artifact)
            raise ValueError("[C5-REAL] Anergía Total: Artifact lacks structural tags. Execution aborted.")
            
        nucleo_puro = "\n".join(core_matches)
        
        # 2. Validation of JIT variables
        tiene_templates = bool(re.search(r'\{\{[a-z_]+\}\}', nucleo_puro))
        if not tiene_templates:
            self._log_failure("Zero JIT variables found in structural core.", raw_artifact)
            raise ValueError("[C5-REAL] Falsabilidad Estructural: Nucleo lacks JIT template variables. Execution aborted.")
            
        return nucleo_puro
