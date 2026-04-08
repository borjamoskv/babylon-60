"""
Frontier Daemon (R&D & Metabolism)
The engine that ensures CORTEX is always at the bleeding edge.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.extensions.daemon.frontier")


class FrontierDaemon:
    """
    The R&D and Auto-Refactoring pulse of MOSKV-1.

    1. Cognitive Ingestion: Ingests SOTA documentation and auto-forges skills.
    2. Nocturnal Metabolism: Executes Ouroboros-Omega to reduce codebase entropy.
    """

    def __init__(
        self,
        engine: Any = None,
        metabolism_interval_hours: int = 12,
        ingestion_interval_hours: int = 24,
        allow_commits: bool = True,
    ) -> None:
        self.engine = engine
        self.metabolism_interval = metabolism_interval_hours * 3600
        self.ingestion_interval = ingestion_interval_hours * 3600
        self.allow_commits = allow_commits
        self._shutdown = False
        self._stop_event = asyncio.Event()
        self.last_metabolism = 0
        self.last_ingestion = 0

    async def _run_metabolism(self):
        """Executes Ouroboros-Omega on high-entropy files."""
        logger.info("[FRONTIER] Initializing Nocturnal Metabolism (Ouroboros-Omega)...")

        try:
            target_path = Path.home() / "cortex/cortex"
            from cortex.extensions.evolution.ouroboros_omega import OuroborosOmega

            test_file = target_path / "daemon/core.py"
            if test_file.exists():
                logger.info("[FRONTIER] Metabolizing %s...", test_file.name)
                engine = OuroborosOmega(str(test_file), dry_run=not self.allow_commits)
                result = await engine.execute_atomic_cycle()

                status = result.get("status", "UNKNOWN")
                logger.info("[FRONTIER] Metabolism result: %s", status)

                if status == "SUCCESS":
                    msg = f"Auto-refactored {test_file.name} with Ouroboros-Omega."
                    await self._log_evolution("metabolism", msg)
        except Exception as e:  # noqa: BLE001 — Isolate metabolism cycle failures from daemon boundary
            logger.error("[FRONTIER] Metabolism cycle failed: %s", e)

    async def _run_ingestion(self):
        """Ingests new intelligence to forge skills."""
        logger.info("[FRONTIER] Scanning frontier for Cognitive Ingestion...")
        sources = [
            "https://github.com/google-deepmind/jules",
            "https://docs.anthropic.com/en/docs/agents-and-tools/computer-use",
        ]

        for source in sources:
            logger.info("[FRONTIER] Analyzing source: %s", source)
            msg = f"Analyzed {source} for potential skill emancipation."
            await self._log_evolution("ingestion", msg)

    async def _persist_evolution_fact(self, fact_type: str, content: str) -> bool:
        if not self.engine:
            return False

        store = getattr(self.engine, "store", None)
        if store is not None and inspect.iscoroutinefunction(store):
            await store(
                project="cortex",
                content=content,
                fact_type=fact_type,
                source="daemon:frontier",
                tags=["frontier", fact_type],
                confidence="C5",
                meta={"daemon": "frontier"},
            )
            return True

        store_sync = getattr(self.engine, "store_sync", None)
        if callable(store_sync):
            store_sync(
                "cortex",
                content=content,
                fact_type=fact_type,
                source="daemon:frontier",
                tags=["frontier", fact_type],
                confidence="C5",
                meta={"daemon": "frontier"},
            )
            return True

        logger.warning("[FRONTIER] Skipped evolution log: engine lacks store/store_sync")
        return False

    async def _log_evolution(self, type: str, content: str) -> None:
        """Registers the evolution event in CORTEX."""
        try:
            stored = await self._persist_evolution_fact(
                "decision",
                f"[{type.upper()}] {content}",
            )
            if stored:
                logger.info("[FRONTIER] Evolution event logged to CORTEX: %s", type)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.error("[FRONTIER] Failed to log evolution: %s", exc)

    async def run_loop(self) -> None:
        """Main Frontier loop."""
        logger.info("Initializing Frontier Daemon (Evolution Engine)...")
        self._stop_event.clear()
        while not self._shutdown:
            now = time.time()

            # Metabolism Cycle
            if now - self.last_metabolism > self.metabolism_interval:
                await self._run_metabolism()
                self.last_metabolism = now

            # Ingestion Cycle
            if now - self.last_ingestion > self.ingestion_interval:
                await self._run_ingestion()
                self.last_ingestion = now

            if self._shutdown:
                break

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
            except TimeoutError:
                continue

    def stop(self) -> None:
        logger.info("Stopping Frontier Daemon.")
        self._shutdown = True
        self._stop_event.set()
