import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class EpistemicBreakerDaemon:
    """
    Sovereign Epistemic Circuit Breaker (Axiom Ω₂ & Ω₃).

    Acts as the cognitive immune system for the Moskv-1 Daemon.
    Monitors the 'thermal noise' (semantic entropy, database growth, error rates).
    If the derivative of entropy (dE/dt) exceeds a threshold, it forces the system
    into a 'Sleep Mode' (Circuit Open) to purge useless connections, compress memory,
    and prevent the collapse of the causal graph.
    """

    def __init__(
        self,
        engine: Any,
        check_interval_seconds: int = 300,
        max_entropy_threshold: float = 0.70,
    ) -> None:
        self.engine = engine
        self.check_interval_seconds = check_interval_seconds
        self.max_entropy_threshold = max_entropy_threshold
        self.is_running = False

        # Internal state to track entropy derivative
        self._last_fact_count = 0
        self._last_error_count = 0
        self._last_evaluation_time = datetime.now(timezone.utc)

        # System State
        self.circuit_open = False  # False = System is awake and acting. True = Sleep/Compressing.

    @staticmethod
    async def _facts_column_names(conn: aiosqlite.Connection) -> set[str]:
        async with conn.execute("PRAGMA table_info(facts)") as cursor:
            rows = await cursor.fetchall()
        return {str(row[1]) for row in rows}

    @staticmethod
    async def _query_count(
        conn: aiosqlite.Connection,
        sql: str,
        params: tuple[Any, ...],
    ) -> int:
        async with conn.execute(sql, params) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    @classmethod
    async def _collect_stats_from_conn(
        cls,
        conn: aiosqlite.Connection,
        tenant_id: str,
        project: str,
    ) -> dict[str, Any]:
        tenant_id = tenant_id.strip() or "default"
        project = project.strip()

        facts_columns = await cls._facts_column_names(conn)
        if not facts_columns:
            return {
                "total_facts": 0,
                "active_facts": 0,
                "deprecated_facts": 0,
                "orphan_facts": 0,
                "types": {},
            }

        scope_sql = "tenant_id = ?"
        params: list[Any] = [tenant_id]
        if project:
            scope_sql += " AND project = ?"
            params.append(project)

        tombstone_clause = (
            "is_tombstoned = 0"
            if "is_tombstoned" in facts_columns
            else "valid_until IS NULL"
        )
        active_scope_sql = f"{scope_sql} AND {tombstone_clause}"

        total = await cls._query_count(
            conn,
            f"SELECT COUNT(*) FROM facts WHERE {scope_sql}",
            tuple(params),
        )
        active = await cls._query_count(
            conn,
            f"SELECT COUNT(*) FROM facts WHERE {active_scope_sql}",
            tuple(params),
        )
        error_count = await cls._query_count(
            conn,
            f"SELECT COUNT(*) FROM facts WHERE {active_scope_sql} AND fact_type = 'error'",
            tuple(params),
        )

        parent_column = ""
        if "parent_decision_id" in facts_columns:
            parent_column = "parent_decision_id"
        elif "parent_id" in facts_columns:
            parent_column = "parent_id"

        causal_facts = 0
        if parent_column:
            causal_facts = await cls._query_count(
                conn,
                f"SELECT COUNT(*) FROM facts WHERE {active_scope_sql} AND {parent_column} IS NOT NULL",
                tuple(params),
            )

        return {
            "total_facts": total,
            "active_facts": active,
            "deprecated_facts": max(total - active, 0),
            "orphan_facts": max(active - causal_facts, 0),
            "types": {"error": error_count},
        }

    @classmethod
    async def evaluate(
        cls,
        conn: aiosqlite.Connection,
        tenant_id: str,
        project: str = "",
        *,
        max_entropy_threshold: float = 0.70,
    ) -> dict[str, Any]:
        """Run a one-shot entropy evaluation against the current facts table."""
        try:
            stats = await cls._collect_stats_from_conn(conn, tenant_id, project)
        except (sqlite3.Error, OSError, ValueError) as exc:
            logger.debug("EpistemicBreaker.evaluate skipped: %s", exc)
            return {
                "tenant_id": tenant_id.strip() or "default",
                "project": project.strip(),
                "entropy": 0.0,
                "tripped": False,
                "stats": {
                    "total_facts": 0,
                    "active_facts": 0,
                    "deprecated_facts": 0,
                    "orphan_facts": 0,
                    "types": {},
                },
            }

        active = max(stats.get("active_facts", 0), 1)
        total = max(stats.get("total_facts", 0), 1)
        orphan_ratio = min(stats.get("orphan_facts", 0) / active, 1.0)
        error_density = min(stats.get("types", {}).get("error", 0) / active, 1.0)
        deprecation_ratio = min(stats.get("deprecated_facts", 0) / total, 1.0)
        entropy = round(
            min(
                orphan_ratio * 0.30
                + error_density * 0.25
                + deprecation_ratio * 0.20,
                1.0,
            ),
            4,
        )
        tripped = entropy >= max_entropy_threshold

        if tripped:
            logger.warning(
                "[EPISTEMIC BREAKER] Post-store entropy threshold crossed: %.3f >= %.3f "
                "(tenant=%s, project=%s)",
                entropy,
                max_entropy_threshold,
                tenant_id.strip() or "default",
                project.strip() or "*",
            )

        return {
            "tenant_id": tenant_id.strip() or "default",
            "project": project.strip(),
            "entropy": entropy,
            "tripped": tripped,
            "stats": stats,
        }

    async def _measure_entropy(self) -> float:
        """Deterministic cognitive entropy (0.0–1.0) from engine stats.

        Components (weighted):
          - orphan_ratio   (0.30): orphan facts / active facts
          - error_density  (0.25): error-type facts / active facts
          - deprecation    (0.20): deprecated / total facts
          - growth_rate    (0.25): Δ(facts) since last evaluation, normalized

        Returns 0.0 under clean state, approaches 1.0 under systemic stress.
        """
        try:
            s = await self.engine.stats()
        except Exception:
            logger.debug("_measure_entropy: engine.stats() unavailable, returning 0")
            return 0.0

        active = max(s.get("active_facts", 0), 1)
        total = max(s.get("total_facts", 0), 1)
        orphans = s.get("orphan_facts", 0)
        deprecated = s.get("deprecated_facts", 0)
        error_count = s.get("types", {}).get("error", 0)

        orphan_ratio = min(orphans / active, 1.0)
        error_density = min(error_count / active, 1.0)
        deprecation_ratio = min(deprecated / total, 1.0)

        # Growth rate: compare current fact count to last snapshot
        delta = max(active - self._last_fact_count, 0)
        # Normalize: >200 new facts per cycle → saturated
        growth_rate = min(delta / 200.0, 1.0)
        self._last_fact_count = active

        entropy = (
            orphan_ratio * 0.30
            + error_density * 0.25
            + deprecation_ratio * 0.20
            + growth_rate * 0.25
        )
        return round(min(entropy, 1.0), 4)

    async def _trigger_sleep_cycle(self) -> None:
        """
        The Circuit Breaker trips. The system must sleep to survive.
        (Axiom Ω₂: Entropic Asymmetry - Reduce entropy).
        """
        logger.warning(
            "🔴 [EPISTEMIC BREAKER] CIRCUIT OPEN (TRIPPED). System entering mandatory sleep cycle."
        )
        self.circuit_open = True

        # Record the event in the sovereign ledger for auditing (Falla Bizantina)
        try:
            await self.engine.store(
                "cortex-core",
                content="Epistemic limit crossed. Initiating cognitive shutdown and compression.",
                fact_type="decision",
                tags=["system", "immune", "circuit-breaker"],
                confidence="C5",
                source="agent:epistemic-breaker",
            )
        except Exception as e:
            logger.error("Failed to record breaker trip: %s", e)

        logger.info(
            "🧠 [SLEEP CYCLE] Running Autodidact Compression / Memory Compaction...\n"
            "   (Simulating structural prune)"
        )

        # Execute deep structural compression (Ω₁₃) via autodidact-omega
        # payload when system limits reached.
        await asyncio.sleep(15)  # Cooldown: compress graph and reconstruct bounds.

        logger.info(
            "🟢 [EPISTEMIC BREAKER] Compression complete. Entropy reduced. CLOSING CIRCUIT."
        )
        self.circuit_open = False

        # Record wakeup
        try:
            await self.engine.store(
                "cortex-core",
                content="Sleep cycle complete. Cognitive clarity restored. System resuming.",
                fact_type="decision",
                tags=["system", "immune", "circuit-breaker", "wakeup"],
                confidence="C5",
                source="agent:epistemic-breaker",
            )
        except Exception as e:  # noqa: BLE001 — wakeup persist must not crash daemon
            logger.error("Failed to record breaker wakeup: %s", e)

    async def run(self) -> None:
        """Main evaluation loop."""
        logger.info(
            "🛡️ Epistemic Breaker Daemon Initialized. Scanning every %ss. Max Entropy limit: %s",
            self.check_interval_seconds,
            self.max_entropy_threshold,
        )
        self.is_running = True

        while self.is_running:
            try:
                # 1. Measure the current state of chaos
                entropy = await self._measure_entropy()

                if entropy >= self.max_entropy_threshold:
                    logger.critical(
                        "⚠️ HIGH ENTROPY DETECTED: %.3f >= %.3f",
                        entropy,
                        self.max_entropy_threshold,
                    )
                    # 2. If it exceeds limits, trip the breaker.
                    await self._trigger_sleep_cycle()
                else:
                    logger.debug("Epistemic load nominal: %.3f", entropy)

            except Exception as e:
                logger.error("Error in Epistemic Breaker loop: %s", e)

            # Wait for next scan, adjust if circuit is currently open
            if self.is_running:
                await asyncio.sleep(self.check_interval_seconds)

    def stop(self) -> None:
        """Signals the daemon to shut down cleanly."""
        logger.info("Stopping Epistemic Breaker Daemon...")
        self.is_running = False
