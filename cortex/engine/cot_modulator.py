import json
import os


class SovereignModulator:
    """
    Sovereign Intelligence Modulator.
    Replaces heuristic 'Intention' with deterministic 'State Truth'.
    """

    def __init__(self, ledger_path: str = None):
        # Default to the workspace ledger if not provided
        self.ledger_path = ledger_path or "bounty_output/sovereign_ledger.jsonl"
        self._jit_cache = None  # O(1) JIT-memory invariant

    def _hydrate_cache(self):
        """Hydrates the O(1) JIT-memory cache from the ledger file to annihilate CPU entropy."""
        if self._jit_cache is not None:
            return

        self._jit_cache = {}
        if not os.path.exists(self.ledger_path):
            return

        try:
            with open(self.ledger_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    tid = entry.get("target_id")
                    if tid:
                        self._jit_cache[tid] = entry
        except (OSError, json.JSONDecodeError):
            pass

    def should_use_cot(self, target_id: str = None) -> bool:
        """
        Triggers Reasoning Mode based on Ledger Friction.
        If target_id has failed transactions or missing evidence, CoT is FORCED.
        """
        if not target_id:
            return False

        # In a real environment (C5-REAL), we verify the physical existence of the ledger
        if not os.path.exists(self.ledger_path):
            return False  # O(1) by default if no history is available

        self._hydrate_cache()

        # Truth-check: O(1) lookup via JIT-memory cache
        entry = self._jit_cache.get(target_id)
        if entry:
            if entry.get("verified_count", 0) == 0 and entry.get("max_bounty_usd", 0) > 100000:
                return True  # Force CoT: Target is high-value but unverified

        return False

    def wrap_proposal(self, proposal: dict, use_cot: bool) -> dict:
        """Anchors the proposal in either O(1) direct execution or SAGA-reasoning."""
        mode = "SAGA_REASONING" if use_cot else "DIRECT_COMMIT"

        # Ensure proposal has a metadata structure
        if "meta" not in proposal:
            proposal["meta"] = {}

        proposal["meta"].update(
            {
                "execution_mode": mode,
                "truth_anchored": True,
                "realtime_exergy": 1.0 if use_cot else 0.1,
                "modulator_v": "Ω-Sovereign-1.0",
            }
        )
        return proposal


class CoTModulator:
    """
    Chain-of-Thought (CoT) Modulator.
    Analyzes prompts/messages for security triggers under Law Ω₁₀ and forces reasoning mode.
    """

    def should_use_cot(self, content: str) -> bool:
        """Determines if the prompt content requires deep reasoning (CoT)."""
        if not content:
            return False
        content_lower = content.lower()
        triggers = ["audit", "fuzz", "vulnerability", "exploit", "critical", "piensa", "verify"]
        return any(t in content_lower for t in triggers)

    def wrap_prompt(self, prompt: str, use_cot: bool) -> str:
        """Wraps prompt with dynamic instructions for CoT reasoning when active."""
        if use_cot:
            return (
                "[REASONING MODE ACTIVE]\n"
                "Please analyze this step-by-step using deep architectural reasoning. "
                "Output your thinking process first, then deliver the final C5-REAL result.\n\n"
                f"{prompt}"
            )
        return prompt
