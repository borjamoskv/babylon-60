import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.extensions.cuatrida.models import CuatridaMetrics, DecisionNode, Dimension
from cortex.extensions.mejoralo.engine import MejoraloEngine

logger = logging.getLogger("cortex.extensions.cuatrida.orchestrator")


class CuatridaOrchestrator:
    """
    The Sovereign Orchestrator for the Cuátrida Entity.
    Unifies the 4 dimensions of CORTEX.
    """

    def __init__(self, engine: AsyncCortexEngine):
        self.engine = engine
        self.mejoralo = MejoraloEngine(engine=engine)  # type: ignore[reportArgumentType]
        self.metrics = CuatridaMetrics()
        self._last_tx_id: Optional[int] = None

    async def log_decision(
        self,
        project: str,
        intent: str,
        dimension: Dimension,
        metadata: Optional[dict[str, Any]] = None,
        conn: Any = None,
        tenant_id: str = "default",
    ) -> DecisionNode:
        """
        Dimension B: Seals a decision into the immutable ledger.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = metadata or {}
        action = f"cuatrida:{dimension.value}"

        # Dimension B: Hook into CORTEX ledger.
        # Use provided connection if available to stay in the same transaction.
        if conn:
            actual_tx_id = await self.engine._log_transaction(
                conn,
                project,
                action,
                metadata,
                tenant_id=tenant_id,
            )
        else:
            async with self.engine.session() as session:
                actual_tx_id = await self.engine._log_transaction(
                    session,
                    project,
                    action,
                    metadata,
                    tenant_id=tenant_id,
                )
                await session.commit()

        self._last_tx_id = actual_tx_id

        node = DecisionNode(
            tx_id=actual_tx_id,
            project=project,
            intent=intent,
            dimension=dimension,
            metrics=self.metrics,
            timestamp=timestamp,
            causal_link=actual_tx_id,
            metadata=metadata,
        )
        self.metrics.decision_count += 1
        logger.info(
            "Sovereign Decision Sealed [%s] tx:%s: %s", dimension.value, actual_tx_id, intent
        )
        return node

    async def validate_aesthetic(self, project: str, path: str | Path) -> bool:
        """
        Dimension C: The Consul of Honor checks for 130/100 standards.
        """
        scan_result = self.mejoralo.scan(project, path)
        self.metrics.aesthetic_honor = float(scan_result.score)
        is_honorable = scan_result.score >= 90
        await self.log_decision(
            project=project,
            intent=f"Aesthetic Audit: {path}",
            dimension=Dimension.AESTHETIC_SOVEREIGNTY,
            metadata={
                "score": scan_result.score,
                "honorable": is_honorable,
                "total_loc": scan_result.total_loc,
            },
        )
        return is_honorable

    async def oracle_ritual(self, project: str, intent: str, cost_tokens: int) -> float:
        """
        Dimension D: The Oracle Ritual.
        Calculates 'Computational Respect' based on intent utility vs cost.
        """
        self.metrics.oracle_invocations += 1
        current_respect = max(0.1, 1.0 - (cost_tokens / 10000.0))
        self.metrics.computational_respect = (
            self.metrics.computational_respect + current_respect
        ) / 2
        await self.log_decision(
            project=project,
            intent=f"Oracle Invocation: {intent}",
            dimension=Dimension.ETHICAL_MANAGEMENT,
            metadata={
                "cost_tokens": cost_tokens,
                "instant_respect": current_respect,
                "cumulative_respect": self.metrics.computational_respect,
            },
        )
        logger.info("Oracle Ritual Completed. Respect: %.2f", self.metrics.computational_respect)
        return self.metrics.computational_respect

    async def zero_friction_sync(self, project: str) -> dict[str, Any]:
        """
        Dimension A: Zero-Friction Sync.
        Interfaces with ghost-control to ensure the system is in a pre-cognitive state.
        """
        from cortex.core.paths import SKILLS_DIR

        ghost_path = SKILLS_DIR / "ghost-control" / "ghost.py"
        latency = 0.0
        status = "unknown"

        if ghost_path.exists():
            start = datetime.now(timezone.utc)
            try:
                subprocess.run(
                    ["python3", str(ghost_path), "status"],
                    capture_output=True,
                    timeout=2.0,
                    check=False,
                )
                latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                status = "active"
            except (subprocess.SubprocessError, OSError):
                status = "error"

        self.metrics.latency_ms = latency
        # Finitud density increases as latency decreases below 100ms
        self.metrics.finitud_density = max(0.1, min(1.0, 1.0 - (latency / 500.0)))

        metadata = {
            "latency_ms": latency,
            "status": status,
            "density": self.metrics.finitud_density,
        }
        await self.log_decision(
            project=project,
            intent="Zero-Friction State Synchronization",
            dimension=Dimension.ZERO_FRICTION,
            metadata=metadata,
        )
        return metadata
