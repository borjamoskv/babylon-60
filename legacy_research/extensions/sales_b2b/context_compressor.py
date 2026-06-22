# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - B2B Sales Context Compressor.

Applies Landauer's principle (thermodynamic context compression) to
automated messaging flows. To overcome context limits (Context Rot),
this module compresses long chains of emails, LinkedIn messages, or
historical context into strict structural invariants (JSON/YAML).

This prevents the LLM from processing zero-yield narrative "fluff"
and maximizes exergy by retaining only causal state transitions.
Emits [CORTEX-TAINT] to track the Epistemic Dependency Graph (EDG).
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("cortex.extensions.sales_b2b.context_compressor")


class ContextCompressor:
    """Compresses conversational text into epistemic invariants."""

    def __init__(self, entropy_threshold: int = 4000) -> None:
        """
        Args:
            entropy_threshold: The number of characters
                at which the context is considered "rotting" and
                must be collapsed.
        """
        self.entropy_threshold = entropy_threshold

    def is_degraded(self, text: str) -> bool:
        """Evaluate if the text entropy exceeds the thermodynamic threshold."""
        return len(text) > self.entropy_threshold

    def compress_history(self, history: list[dict[str, Any]], agent_id: str) -> dict[str, Any]:
        """
        Applies Landauer compression to an entire history array.
        Extracts structural facts and purges narrative fluff.
        
        Returns:
            A dictionary containing the state machine representation
            of the interaction with CORTEX-TAINT hash injection.
        """
        logger.info("Applying thermodynamic context compression to %d messages.", len(history))
        
        # Ouroboros Exergy Hash calculation for TAINT
        raw_dump = json.dumps(history, sort_keys=True).encode("utf-8")
        compression_hash = hashlib.sha256(raw_dump).hexdigest()[:16]
        
        tainted_signature = f"[CORTEX-TAINT: {agent_id}] {compression_hash}"

        invariants: dict[str, Any] = {
            "total_interactions": len(history),
            "last_contact_date": None,
            "compression_hash": compression_hash,
            "taint_signature": tainted_signature,
            "extracted_topics": [],
        }
        
        if history:
            invariants["last_contact_date"] = history[-1].get("timestamp")
            
            # Use deterministic heuristic synthesis (Simulating SynthesisEngine)
            text_dump = " ".join([str(msg.get("content", "")) for msg in history]).lower()
            
            # Deterministic topic classification mapping (no ad-hoc strings)
            classification_matrix = {
                "BUDGET_OBJECTION": ["budget", "expensive", "cost"],
                "API_INTEGRATION": ["integration", "api", "webhooks"],
                "SECURITY_REVIEW": ["security", "compliance", "iso27001", "soc2"],
            }
            
            for topic, markers in classification_matrix.items():
                if any(marker in text_dump for marker in markers):
                    invariants["extracted_topics"].append(topic)
                    
        invariants["extracted_topics"] = sorted(list(set(invariants["extracted_topics"])))
        
        return invariants
