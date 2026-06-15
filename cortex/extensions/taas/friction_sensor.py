# [C5-REAL] Exergy-Maximized
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from cortex.extensions.taas.market import TaaSMarketplace

logger = logging.getLogger("cortex.taas.friction_sensor")

class FrictionSensor:
    """
    High-resolution telemetry sensor for the TaaS Market.
    Acts as the nervous system for OUROBOROS-∞ to detect when and what to absorb.
    """

    def __init__(self, market: TaaSMarketplace):
        self.market = market

    def get_friction_telemetry(self, time_window_seconds: int = 3600) -> dict[str, Any]:
        """
        Extracts friction data from recent job execution results.
        Provides OUROBOROS-∞ with the precise locations of cognitive/computational waste.
        """
        total_latency = Decimal('0')
        total_redundancy = Decimal('0')
        total_memory_blocks = Decimal('0')
        job_count = 0

        now = datetime.now(timezone.utc)

        for _, result in self.market._results.items():
            if result.friction_metrics:
                try:
                    executed_dt = datetime.fromisoformat(result.executed_at.replace("Z", "+00:00"))
                    if (now - executed_dt).total_seconds() > time_window_seconds:
                        continue
                except ValueError:
                    pass

                total_latency += Decimal(str(result.friction_metrics.get("latency_ms", 0)))
                total_redundancy += Decimal(str(result.friction_metrics.get("llm_redundancy", 0)))
                total_memory_blocks += Decimal(str(result.friction_metrics.get("memory_blocks", 0)))
                job_count += 1

        if job_count == 0:
            return {
                "status": "IDLE",
                "average_latency_ms": Decimal('0'),
                "average_llm_redundancy": Decimal('0'),
                "average_memory_blocks": Decimal('0'),
                "friction_level": "LOW",
                "recommended_action": "SLEEP"
            }

        avg_latency = total_latency / Decimal(str(job_count))
        avg_redundancy = total_redundancy / Decimal(str(job_count))
        avg_memory_blocks = total_memory_blocks / Decimal(str(job_count))

        # Determine overall friction level
        friction_level = "LOW"
        action = "SLEEP"

        if avg_latency > Decimal('500') or avg_redundancy > Decimal('2.0') or avg_memory_blocks > Decimal('5.0'):
            friction_level = "CRITICAL"
            action = "OURO_TRANSCEND"
        elif avg_latency > Decimal('200') or avg_redundancy > Decimal('1.0') or avg_memory_blocks > Decimal('2.0'):
            friction_level = "MODERATE"
            action = "OURO_ABSORB"

        telemetry = {
            "status": "ACTIVE",
            "jobs_analyzed": job_count,
            "average_latency_ms": avg_latency,
            "average_llm_redundancy": avg_redundancy,
            "average_memory_blocks": avg_memory_blocks,
            "friction_level": friction_level,
            "recommended_action": action
        }

        logger.info(f"[FrictionSensor] Telemetry generated: {friction_level} Friction detected.")
        return telemetry
