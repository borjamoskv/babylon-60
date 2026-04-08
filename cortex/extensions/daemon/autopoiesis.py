"""Continuous autopoiesis engine and daemon for CORTEX.

Implements a bounded, policy-driven loop:
Observe -> Plan -> Act -> Measure -> Crystallize -> Repeat

The engine never performs opaque self-modification by default. It only executes
known actions and only records a cycle as accepted when measured state improves.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.extensions.mejoralo.engine import MejoraloEngine
    from cortex.extensions.sovereign.autopoiesis import Autopoiesis

logger = logging.getLogger("cortex.extensions.daemon.autopoiesis")


@dataclass(slots=True)
class AutopoiesisPolicy:
    """Boundaries for continuous autopoiesis cycles."""

    project: str = "cortex"
    focus: str = "entropy"
    target_score: int = 95
    cycle_interval_hours: float = 24.0
    idle_poll_seconds: float = 60.0
    enable_healing: bool = True
    enable_manifestation: bool = False
    minimum_registered_tools: int = 0


@dataclass(slots=True)
class AutopoiesisSnapshot:
    """Current measurable state used to plan an autopoiesis cycle."""

    timestamp: float
    workspace_root: str
    entropy_score: float
    scan_score: int | None = None
    registered_tools: int = 0


@dataclass(slots=True)
class AutopoiesisPlan:
    """The next bounded action proposed by the engine."""

    focus: str
    action: str
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AutopoiesisCycleResult:
    """Outcome of a full autopoiesis cycle."""

    evolved: bool
    accepted: bool
    action: str
    hypothesis: str
    improvement: dict[str, Any]
    snapshot_before: AutopoiesisSnapshot
    snapshot_after: AutopoiesisSnapshot
    action_result: dict[str, Any] = field(default_factory=dict)


class AutopoiesisEngine:
    """Policy-driven autopoiesis engine for long-running daemon execution."""

    def __init__(
        self,
        engine: CortexEngine | Any | None,
        workspace_root: str | Path,
        policy: AutopoiesisPolicy | None = None,
        mejoralo_factory: Callable[[Any], MejoraloEngine] | None = None,
        autopoiesis_factory: Callable[[], Autopoiesis] | None = None,
        manifest_generator: Callable[[], str] | None = None,
        manifest_validator: Callable[[str], bool] | None = None,
    ) -> None:
        self.engine = engine
        self.root = Path(workspace_root).resolve()
        self.policy = policy or AutopoiesisPolicy()
        self._mejoralo_factory = mejoralo_factory
        self._autopoiesis_factory = autopoiesis_factory
        self._manifest_generator = manifest_generator
        self._manifest_validator = manifest_validator

    def _build_mejoralo(self) -> Any:
        if self._mejoralo_factory is not None:
            return self._mejoralo_factory(self.engine)

        from cortex.extensions.mejoralo.engine import MejoraloEngine

        return MejoraloEngine(self.engine)

    def _build_autopoiesis(self) -> Any:
        if self._autopoiesis_factory is not None:
            return self._autopoiesis_factory()

        from cortex.extensions.sovereign.autopoiesis import Autopoiesis

        return Autopoiesis()

    async def observe(self) -> AutopoiesisSnapshot:
        """Observe bounded system state relevant to autopoiesis."""
        scan_score: int | None = None
        entropy_score = 0.0
        registered_tools = 0

        try:
            mejoralo = self._build_mejoralo()
            scan_result = await asyncio.to_thread(
                mejoralo.scan,
                self.policy.project,
                str(self.root),
            )
            scan_score = int(getattr(scan_result, "score", 100))
            entropy_score = max(0.0, 100.0 - float(scan_score))
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning("[AUTOPOIESIS] Observation scan failed: %s", exc)

        try:
            registered_tools = len(self._build_autopoiesis().list_registered())
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.debug("[AUTOPOIESIS] Tool registry observation failed: %s", exc)

        return AutopoiesisSnapshot(
            timestamp=time.time(),
            workspace_root=str(self.root),
            entropy_score=entropy_score,
            scan_score=scan_score,
            registered_tools=registered_tools,
        )

    def plan(self, snapshot: AutopoiesisSnapshot, focus: str | None = None) -> AutopoiesisPlan:
        """Plan the next bounded action using the current policy."""
        planned_focus = focus or self.policy.focus

        if (
            self.policy.enable_healing
            and snapshot.scan_score is not None
            and snapshot.scan_score < self.policy.target_score
        ):
            return AutopoiesisPlan(
                focus=planned_focus,
                action="heal",
                rationale=(
                    f"scan score {snapshot.scan_score} is below target {self.policy.target_score}"
                ),
                metadata={"score_before": snapshot.scan_score},
            )

        if (
            self.policy.enable_manifestation
            and snapshot.registered_tools < self.policy.minimum_registered_tools
        ):
            return AutopoiesisPlan(
                focus=planned_focus,
                action="manifest_tool",
                rationale=(
                    "registered tools below minimum threshold "
                    f"({snapshot.registered_tools} < {self.policy.minimum_registered_tools})"
                ),
                metadata={"registered_tools": snapshot.registered_tools},
            )

        return AutopoiesisPlan(
            focus=planned_focus,
            action="stabilize",
            rationale="no higher-priority autopoietic action required",
        )

    async def act(self, plan: AutopoiesisPlan) -> dict[str, Any]:
        """Execute one known autopoiesis action."""
        if plan.action == "heal":
            mejoralo = self._build_mejoralo()
            scan_result = await asyncio.to_thread(
                mejoralo.scan,
                self.policy.project,
                str(self.root),
            )
            success = await asyncio.to_thread(
                mejoralo.relentless_heal,
                self.policy.project,
                str(self.root),
                scan_result,
                self.policy.target_score,
            )
            return {
                "success": bool(success),
                "performed": True,
                "action": "heal",
                "score_before": getattr(scan_result, "score", None),
            }

        if plan.action == "manifest_tool":
            if self._manifest_generator is None:
                return {
                    "success": False,
                    "performed": False,
                    "action": "manifest_tool",
                    "reason": "no manifest generator configured",
                }

            tool_path = await asyncio.to_thread(
                self._build_autopoiesis().generate_and_register,
                self._manifest_generator,
                self._manifest_validator,
            )
            return {
                "success": True,
                "performed": True,
                "action": "manifest_tool",
                "tool_path": str(tool_path),
            }

        return {
            "success": True,
            "performed": False,
            "action": "stabilize",
            "reason": "state already within policy bounds",
        }

    async def measure(
        self,
        before: AutopoiesisSnapshot,
        action_result: dict[str, Any],
    ) -> tuple[AutopoiesisSnapshot, dict[str, Any]]:
        """Measure whether the action improved bounded state."""
        after = await self.observe()
        delta_entropy = before.entropy_score - after.entropy_score

        delta_score = 0
        if before.scan_score is not None and after.scan_score is not None:
            delta_score = after.scan_score - before.scan_score

        delta_tools = after.registered_tools - before.registered_tools

        net_positive = delta_score > 0 or delta_entropy > 0 or delta_tools > 0
        return after, {
            "net_positive": net_positive,
            "delta_entropy": delta_entropy,
            "delta_score": delta_score,
            "delta_tools": delta_tools,
            "performed": action_result.get("performed", False),
        }

    async def crystallize(
        self,
        plan: AutopoiesisPlan,
        action_result: dict[str, Any],
        improvement: dict[str, Any],
        before: AutopoiesisSnapshot,
        after: AutopoiesisSnapshot,
    ) -> None:
        """Persist accepted cycles through supported engine write paths."""
        if self.engine is None:
            logger.warning("[AUTOPOIESIS] Skipped crystallization: engine unavailable")
            return

        content = (
            f"Autopoiesis accepted action={plan.action} focus={plan.focus}. "
            f"Rationale: {plan.rationale}. Improvement: {improvement}"
        )
        meta = {
            "daemon": "autopoiesis",
            "plan": asdict(plan),
            "action_result": action_result,
            "improvement": improvement,
            "before": asdict(before),
            "after": asdict(after),
        }

        try:
            store = getattr(self.engine, "store", None)
            if store is not None and inspect.iscoroutinefunction(store):
                await store(
                    project=self.policy.project,
                    content=content,
                    fact_type="decision",
                    source="daemon:autopoiesis",
                    tags=["autopoiesis", plan.action],
                    confidence="C5",
                    meta=meta,
                )
                return

            store_sync = getattr(self.engine, "store_sync", None)
            if callable(store_sync):
                await asyncio.to_thread(
                    store_sync,
                    project=self.policy.project,
                    content=content,
                    fact_type="decision",
                    source="daemon:autopoiesis",
                    tags=["autopoiesis", plan.action],
                    confidence="C5",
                    meta=meta,
                )
                return

            logger.warning("[AUTOPOIESIS] Skipped crystallization: engine lacks store/store_sync")
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.error("[AUTOPOIESIS] Crystallization failed: %s", exc)

    async def run_cycle(self, focus: str | None = None) -> AutopoiesisCycleResult:
        """Execute one bounded autopoiesis cycle."""
        before = await self.observe()
        plan = self.plan(before, focus=focus)

        if plan.action == "stabilize":
            return AutopoiesisCycleResult(
                evolved=False,
                accepted=False,
                action=plan.action,
                hypothesis=plan.rationale,
                improvement={
                    "net_positive": False,
                    "performed": False,
                    "reason": "stable_state",
                },
                snapshot_before=before,
                snapshot_after=before,
                action_result={"success": True, "performed": False},
            )

        action_result = await self.act(plan)
        if not action_result.get("success", False):
            return AutopoiesisCycleResult(
                evolved=False,
                accepted=False,
                action=plan.action,
                hypothesis=plan.rationale,
                improvement={
                    "net_positive": False,
                    "performed": action_result.get("performed", False),
                    "reason": action_result.get("reason", "action_failed"),
                },
                snapshot_before=before,
                snapshot_after=before,
                action_result=action_result,
            )

        after, improvement = await self.measure(before, action_result)
        accepted = bool(improvement["net_positive"])
        if accepted:
            await self.crystallize(plan, action_result, improvement, before, after)
        else:
            logger.warning("[AUTOPOIESIS] Cycle rejected: %s", improvement)

        return AutopoiesisCycleResult(
            evolved=bool(action_result.get("performed", False)),
            accepted=accepted,
            action=plan.action,
            hypothesis=plan.rationale,
            improvement=improvement,
            snapshot_before=before,
            snapshot_after=after,
            action_result=action_result,
        )


class AutopoiesisDaemon:
    """24/7/365 scheduler for bounded autopoiesis cycles."""

    def __init__(
        self,
        engine: CortexEngine | Any | None,
        workspace_root: str | Path,
        cycle_interval_hours: float = 24.0,
        idle_poll_seconds: float = 60.0,
        target_score: int = 95,
        enable_healing: bool = True,
        enable_manifestation: bool = False,
        minimum_registered_tools: int = 0,
        project: str = "cortex",
        focus: str = "entropy",
        autopoiesis_engine: AutopoiesisEngine | None = None,
    ) -> None:
        policy = AutopoiesisPolicy(
            project=project,
            focus=focus,
            target_score=target_score,
            cycle_interval_hours=cycle_interval_hours,
            idle_poll_seconds=idle_poll_seconds,
            enable_healing=enable_healing,
            enable_manifestation=enable_manifestation,
            minimum_registered_tools=minimum_registered_tools,
        )
        self.autopoiesis_engine = autopoiesis_engine or AutopoiesisEngine(
            engine=engine,
            workspace_root=workspace_root,
            policy=policy,
        )
        self.interval = cycle_interval_hours * 3600
        self.idle_poll_seconds = idle_poll_seconds
        self._shutdown = False
        self._stop_event = asyncio.Event()
        self.last_cycle = 0.0

    async def run_cycle(self, focus: str = "entropy") -> AutopoiesisCycleResult:
        """Execute one autopoiesis cycle."""
        logger.info("[AUTOPOIESIS] Starting cycle on focus=%s", focus)
        return await self.autopoiesis_engine.run_cycle(focus=focus)

    async def run_loop(self) -> None:
        """Run continuous autopoiesis forever until stopped."""
        logger.info("♾️ Autopoiesis daemon ONLINE.")
        self._stop_event.clear()
        while not self._shutdown:
            now = time.time()
            if now - self.last_cycle > self.interval:
                await self.run_cycle(focus=self.autopoiesis_engine.policy.focus)
                self.last_cycle = now

            if self._shutdown:
                break

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.idle_poll_seconds)
            except TimeoutError:
                continue

    def stop(self) -> None:
        """Signal graceful shutdown."""
        logger.info("Stopping Autopoiesis daemon.")
        self._shutdown = True
        self._stop_event.set()
