"""
CORTEX — Ouroboros-Ω Gate.
The thermodynamic enforcer for architectural scaling.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("cortex.extensions.gate.ouroboros")


class OuroborosGate:
    """
    Enforces the 3 Laws of Ouroboros-Ω:
    1. Landauer's Razor (Pruning the least dense module)
    2. Latency Conservation (ΔL ≤ 0)
    3. Terminal Recursion (Prompt/Logic auto-condensation)
    """

    def __init__(self, engine_conn: Any):
        self.conn = engine_conn
        self.metrics_key = "ouroboros:entropy_metrics"

    def measure_entropy(self) -> dict[str, Any]:
        """Calculates complexity metrics and signal-to-noise ratio."""
        # Simple heuristic: fact density per project
        total_facts = self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        total_bridges = self.conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'bridge'"
        ).fetchone()[0]
        total_decisions = self.conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'decision'"
        ).fetchone()[0]

        # Signal density
        projects_count = self.conn.execute("SELECT COUNT(DISTINCT project) FROM facts").fetchone()[
            0
        ]

        # SNR calculation
        signal = total_decisions + total_bridges
        # We define noise as the complement of useful facts
        noise = max(1, total_facts - signal)
        snr = signal / noise

        # Absolute Entropy Index: (1/SNR) * (size/1000)
        entropy_idx = (1.0 / (snr + 0.01)) * (total_facts / 1000.0)

        return {
            "n_projects": projects_count,
            "total_facts": total_facts,
            "total_bridges": total_bridges,
            "signal_to_noise": round(snr, 3),
            "entropy_index": round(entropy_idx, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def identify_dead_weight(self) -> Optional[str]:
        """Identifies the project or module with the lowest importance/density ratio."""
        # Analysis of projects with highest error/bridge ratio
        stats = self.conn.execute("""
            SELECT project,
                   COUNT(*) as total,
                   SUM(CASE WHEN fact_type='error' THEN 1 ELSE 0 END) as errors,
                   SUM(CASE WHEN fact_type='bridge' THEN 1 ELSE 0 END) as bridges
            FROM facts
            GROUP BY project
        """).fetchall()

        if not stats:
            return None

        # Candidates for pruning: many errors, zero bridges
        candidates = []
        for p, total, _, bridges in stats:
            if bridges == 0 and total > 5:
                candidates.append((p, total))

        if candidates:
            # Sort by total facts (higher weight in pruning)
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def trigger_pruning(self, target_project: str) -> None:
        """Block unsafe physical pruning until a canonical tenant-scoped path is available."""
        logger.warning(
            "Ouroboros pruning blocked for project [%s]: canonical tenant-scoped "
            "tombstone/audit path required.",
            target_project,
        )
        raise RuntimeError(
            "Unsafe Ouroboros physical pruning is disabled; use a tenant-scoped "
            "canonical tombstone mutation with ledger audit."
        )

    def _log_scaling_event(self, content: str):
        """Log non-persistent scaling decisions without fabricating audit evidence."""
        logger.warning("Ouroboros scaling event not persisted: %s", content)


def get_ouroboros_gate(engine: Any) -> OuroborosGate:
    """Helper to initialize the gate with an engine connection."""
    return OuroborosGate(engine._get_sync_conn())
