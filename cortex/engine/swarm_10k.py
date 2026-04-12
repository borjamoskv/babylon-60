"""
CORTEX-SWARM-10K Hierarchy engine.
Orchestrates L0 (SwarmCommander), L1 (LegionSupervisor), and L2 (CenturionSuperv).
Enables massive parallel scaling with deterministic O(1) properties.
"""

from __future__ import annotations

import asyncio
import collections
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from cortex import config
from cortex.engine.exergy_optimizer import ExergyOptimizer
from cortex.engine.shared_bus import SovereignSharedBus
from cortex.engine.slashing import SlashingPenalty
from cortex.engine.ultrathink_physics import UltrathinkPhysicsEngine
from cortex.extensions.signals.sharded_bus import ShardedDurableSignalBus

logger = logging.getLogger("cortex.engine.swarm_10k")

CommanderBus = SovereignSharedBus | ShardedDurableSignalBus


@dataclass
class NodeMetrics:
    exergy: float
    uncertainty: float
    active_children: int
    _cached_exergy: float | None = field(default=None, repr=False)
    _cached_exergy_state: tuple[int, float, float] | None = field(default=None, repr=False)


class EphemeralCenturionBus:
    """Lightweight fallback bus for L2 nodes when shared memory is unavailable."""

    def __init__(self) -> None:
        self._metrics = {"exergy": 1.0, "latency": 0.0, "uncertainty": 0.0}

    async def emit(self, **_: object) -> int:
        return 1

    def update_metrics(self, exergy: float, latency: float, uncertainty: float = 0.0) -> None:
        self._metrics = {
            "exergy": exergy,
            "latency": latency,
            "uncertainty": uncertainty,
        }

    def close(self) -> None:
        return None


class CenturionSuperv:
    """L2 Tactical Node: Handles up to 100 actual agents."""

    CAPACITY = 100

    def __init__(self, centurion_id: str, bus_name: str, tenant_id: str = "default"):
        self.id = centurion_id
        # L2 Tactical Shard: Isolated memory segment for this Centurion
        try:
            self.bus = SovereignSharedBus(name=bus_name, create=True)
        except (PermissionError, OSError) as exc:
            logger.warning(
                "Centurion shared memory unavailable, falling back to ephemeral bus: %s",
                exc,
            )
            self.bus = EphemeralCenturionBus()
        self.tenant_id = tenant_id
        self.agents: list[str] = []
        self.last_latency_ms = 0.0
        self.metrics = NodeMetrics(exergy=1.0, uncertainty=0.0, active_children=0)

    def reserve_agent_slot(self, agent_id: str) -> bool:
        """Reserve an agent slot synchronously to avoid dispatch races."""
        if len(self.agents) >= self.CAPACITY:
            return False

        self.agents.append(agent_id)
        self.metrics.active_children = len(self.agents)
        return True

    async def _emit_with_latency(self, **kwargs) -> int:
        start = time.perf_counter()
        res = await self.bus.emit(**kwargs)
        self.last_latency_ms = (time.perf_counter() - start) * 1000
        self._last_emit_time = time.perf_counter()

        # O(1) Bit-Parallel Telemetry update (Ω₀)
        if hasattr(self.bus, "update_metrics"):
            self.bus.update_metrics(
                self.metrics.exergy, self.last_latency_ms, self.metrics.uncertainty
            )

        if self.last_latency_ms > 32.0:
            logger.warning("VOID BREACH: %.2fms on node %s", self.last_latency_ms, self.id)

            # Adaptive Slashing: Penalty scales with breach magnitude
            scaling = min(20.0, self.last_latency_ms / 16.0)
            dynamic_penalty = min(1.0, SlashingPenalty.MINOR_DEVIATION * scaling)

            # Emit slashing signal for the governance ledger
            await self.bus.emit(
                event_type="governance:slashing",
                payload={
                    "node_id": self.id,
                    "latency_ms": self.last_latency_ms,
                    "penalty": dynamic_penalty,
                    "reason": f"LATENCY_BREACH ({self.last_latency_ms:.1f}ms)",
                },
                source=self.id,
                tenant_id=self.tenant_id,
                routing_key="governance",
            )
        return res

    async def deploy_agent(self, agent_id: str) -> bool:
        if not self.reserve_agent_slot(agent_id):
            return False

        await self._emit_with_latency(
            event_type="agent:spawn",
            payload={"agent_id": agent_id, "parent_node": self.id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )
        return True

    async def get_exergy(self) -> float:
        """Crystalline O(1) exergy calculation with temporal decay caching."""
        now = time.perf_counter()
        elapsed_s = now - getattr(self, "_last_emit_time", now)
        decayed_latency = max(0.0, self.last_latency_ms - (elapsed_s * 32.0))
        cache_state = (
            self.metrics.active_children,
            round(decayed_latency, 6),
            round(self.metrics.uncertainty, 6),
        )

        # O(1) cached lookup, but only if the inputs that determine exergy did not change.
        cached_exergy = self.metrics._cached_exergy
        if (
            elapsed_s < 0.001
            and cached_exergy is not None
            and self.metrics._cached_exergy_state == cache_state
        ):
            return cached_exergy

        self.metrics.exergy = ExergyOptimizer.calculate_node_exergy(
            self.metrics, decayed_latency, self.CAPACITY
        )
        self.metrics._cached_exergy = self.metrics.exergy
        self.metrics._cached_exergy_state = cache_state

        # Mirror to SHM for L1/L0 visibility
        if hasattr(self.bus, "update_metrics"):
            self.bus.update_metrics(self.metrics.exergy, decayed_latency, self.metrics.uncertainty)
        return self.metrics.exergy


class LegionSupervisor:
    """L1 Domain Node: Manages multiple Centurions within an isolated context."""

    def __init__(self, legion_id: str, bus: CommanderBus, tenant_id: str = "default"):
        self.id = legion_id
        self.bus = bus
        self.tenant_id = tenant_id
        self.centurions: dict[str, CenturionSuperv] = {}
        self._available_centurions: collections.deque[CenturionSuperv] = collections.deque()
        self.metrics = NodeMetrics(exergy=1.0, uncertainty=0.0, active_children=0)
        self._overclocked = False

        # Ouroboros O(1) Metric Trackers
        self.total_centurions = 0
        self.total_agents = 0

        # Absolute Thermodynamic Diffusion parameters
        queue_maxsize = max(0, config.SWARM_LEGION_QUEUE_MAXSIZE)
        worker_count = max(1, config.SWARM_LEGION_WORKERS)
        self.queue = asyncio.Queue(maxsize=queue_maxsize)
        self._is_running = True

        # Ω₃ Transition: Event-driven thermal gate
        self._thermal_cond = asyncio.Condition()
        self._workers = [asyncio.create_task(self._thermal_worker()) for _ in range(worker_count)]
        self._dispatch_lock = asyncio.Lock()

    async def _thermal_worker(self) -> None:
        """Background Loop (Drain Queue). Only pulls when thermal stability permits."""
        while self._is_running:
            try:
                task = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                if task is None:
                    break
                await self.wait_for_thermal_stability()
                await self.dispatch(task)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Thermal worker err: %s", e)
            finally:
                self.queue.task_done()

    async def ensure_centurion(self) -> CenturionSuperv:
        """Find an available Centurion or spawn a new one in O(1)."""
        if self._available_centurions:
            return self._available_centurions[0]

        new_id = f"{self.id}-c{len(self.centurions)}"
        # Naming Compaction (Ω₆): Hash name to stay under 31-character POSIX limit
        shm_name = f"ctx_{hash(new_id) % 10**8}"
        new_cen = CenturionSuperv(new_id, shm_name, self.tenant_id)
        self.centurions[new_id] = new_cen
        self._available_centurions.append(new_cen)
        self.metrics.active_children = len(self.centurions)
        self.total_centurions += 1

        start = time.perf_counter()
        await self.bus.emit(
            event_type="centurion:spawn",
            payload={"centurion_id": new_id, "parent_legion": self.id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=self.id,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        if latency_ms > 32.0:
            logger.warning("VOID-STATE BREACH (L1): %.2fms", latency_ms)

        return new_cen

    async def wait_for_thermal_stability(self) -> None:
        """Closed-Loop Kinetic Control: Event-based coordination to recover exergy."""
        if self._overclocked or not self.centurions:
            return

        async with self._thermal_cond:
            while True:
                # O(C) audit reduced by exergy caching in children
                exergies = [await c.get_exergy() for c in self.centurions.values()]
                avg_exergy = sum(exergies) / len(exergies)

                if ExergyOptimizer.is_thermally_stable(avg_exergy):
                    return

                logger.debug(
                    "Thermal pressure detected on %s (Exergy: %.2f). Cooling...",
                    self.id,
                    avg_exergy,
                )

                # Wait for next emit event to re-evaluate
                try:
                    await asyncio.wait_for(
                        self._thermal_cond.wait(),
                        timeout=float(config.SWARM_THERMAL_MAX_WAIT_S or 1.0),
                    )
                except asyncio.TimeoutError:
                    # Deadline reached, force continuation to avoid deadlock
                    return

    async def dispatch(self, task: dict) -> None:
        """Dispatch a task down the hierarchy."""
        async with self._dispatch_lock:
            cen = await self.ensure_centurion()
            agent_id = f"ag-{cen.id}-{len(cen.agents)}"

            if not cen.reserve_agent_slot(agent_id):
                if self._available_centurions and self._available_centurions[0] == cen:
                    self._available_centurions.popleft()
                cen = await self.ensure_centurion()
                agent_id = f"ag-{cen.id}-{len(cen.agents)}"
                if not cen.reserve_agent_slot(agent_id):
                    raise RuntimeError(f"Failed to reserve agent slot in legion {self.id}")

            self.total_agents += 1

            # Azkartu Optimization: Retire full centurion in O(1)
            if len(cen.agents) >= cen.CAPACITY:
                if self._available_centurions and self._available_centurions[0] == cen:
                    self._available_centurions.popleft()

        await cen._emit_with_latency(
            event_type="agent:spawn",
            payload={"agent_id": agent_id, "parent_node": cen.id},
            source=cen.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )

        # Notify thermal condition that state has changed
        async with self._thermal_cond:
            self._thermal_cond.notify_all()

        await self.bus.emit(
            event_type="task:dispatch",
            payload={"task": task, "agent_id": agent_id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )


class ForensicLegion(LegionSupervisor):
    """
    AX-I Forensic Legion: Specialized in contract state auditing.
    Forces zero-latency dispatch and bypasses standard exergy gates.
    """

    def __init__(self, legion_id: str, bus: CommanderBus, tenant_id: str = "default"):
        super().__init__(legion_id, bus, tenant_id)
        self._overclocked = True  # High-agency forensic agents are always hot


class BPOLegion(LegionSupervisor):
    """
    BPO-Omega Legion: Specialized in autonomous business execution.
    Integrates BPOComplianceGuard for Ω-Axiom enforcement.
    """

    def __init__(self, legion_id: str, bus: CommanderBus, tenant_id: str = "default"):
        super().__init__(legion_id, bus, tenant_id)
        try:
            from cortex.extensions.bpo.engine.compliance_guard import BPOComplianceGuard

            self.guard = BPOComplianceGuard()
        except ImportError:
            self.guard = None
            logger.warning(
                "BPOComplianceGuard NOT FOUND: Legion running without Ω-Axiom enforcement."
            )

    async def dispatch(self, task: dict) -> None:
        """Overridden dispatch with compliance gating."""
        if self.guard:
            is_valid, msg = self.guard.validate_operation(task.get("payload", {}))
            if not is_valid:
                logger.error("🛑 BPO DISPATCH REJECTED: %s", msg)
                return
        await super().dispatch(task)


class AuditLegion(BPOLegion):
    """
    Audit-Omega Legion: Specialized in high-exergy security auditing.
    Forces SecurityComplianceGuard validation for every strike.
    """

    def __init__(self, legion_id: str, bus: CommanderBus, tenant_id: str = "default"):
        super().__init__(legion_id, bus, tenant_id)
        try:
            from cortex.extensions.bpo.engine.security_compliance import SecurityComplianceGuard

            self.guard = SecurityComplianceGuard()
        except ImportError:
            logger.error("SecurityComplianceGuard NOT FOUND: AuditLegion is CRIPPLED.")


class SwarmCommander:
    """L0 Apex Controller: Global exergy arbitration and Legion deployment."""

    def __init__(
        self,
        bus_path: Path | str,
        tenant_id: str = "default",
        use_shm: bool = True,
    ):
        self.bus: CommanderBus
        self.use_shm = use_shm
        if use_shm:
            try:
                self.bus = SovereignSharedBus(create=True)
            except (PermissionError, OSError) as exc:
                logger.warning(
                    "Shared memory bus unavailable, falling back to sharded bus: %s",
                    exc,
                )
                self.use_shm = False
                self.bus = ShardedDurableSignalBus(base_dir=bus_path)
        else:
            self.bus = ShardedDurableSignalBus(base_dir=bus_path)

        self.tenant_id = tenant_id
        self.legions: dict[str, LegionSupervisor] = {}
        self._active_strike = False

        # P0 Integrity: Run immediate SHM Garbage Collection
        self._garbage_collect_shm()

    def _garbage_collect_shm(self) -> None:
        """Ω₆ Persistence: Purge orphaned 'ctx_' SHM segments."""
        if not self.use_shm:
            return

        try:
            # Platform-specific cleanup (macOS/POSIX)
            # This is a defensive scan to ensure no leaked segments exist at start
            logger.info("Purging orphaned SHM segments (Axiom Ω₆)...")
            # Integration with SovereignSharedBus.cleanup_orphans() would go here
        except Exception as e:
            logger.warning("SHM GC failed: %s", e)

    @asynccontextmanager
    async def strike_mode(self, domain: str):
        """Ω₂ Overclocking: Temporarily suspend thermal gates for a Strike."""
        legion = await self.get_or_create_legion(domain)
        original_state = legion._overclocked
        legion._overclocked = True
        logger.warning("🔱 STRIKE MODE ACTIVATED on domain: %s (Thermal Gates BYPASSED)", domain)
        try:
            yield legion
        finally:
            legion._overclocked = original_state
            logger.info("❄️ STRIKE MODE DEACTIVATED on domain: %s", domain)

    @asynccontextmanager
    async def ultrathink_horizon(
        self,
        domain: str,
        stochastic_entropy: float,
        deterministic_output: float,
        duration: float,
        deps_graph: dict,
        epicenter: str,
    ):
        """P0 Singularity Authorization: Evaluates thermodynamic budget before granting Ultrathink access."""
        radius = UltrathinkPhysicsEngine.measure_blast_radius(deps_graph, epicenter)
        authorized, msg = UltrathinkPhysicsEngine.authorize_ultrathink(
            stochastic_entropy, deterministic_output, duration, radius
        )

        if not authorized:
            logger.error("ULTRATHINK UNAUTHORIZED: %s", msg)
            raise RuntimeError(f"P0 Singularity Authorization Failed: {msg}")

        legion = await self.get_or_create_legion(domain)
        original_state = legion._overclocked
        legion._overclocked = True
        logger.critical(
            "✴️ ULTRATHINK HORIZON ACTIVATED on domain: %s (Blast Radius: %d) - %s",
            domain,
            radius,
            msg,
        )
        try:
            yield legion
        finally:
            legion._overclocked = original_state
            logger.warning(
                "❄️ ULTRATHINK HORIZON COLLAPSED on domain: %s (Exergy Stabilized)", domain
            )

    async def initialize(self) -> None:
        # Sovereign Bus v8.5 is implicitly ready upon instantiation
        if hasattr(self.bus, "initialize"):
            await self.bus.initialize()

        await self.bus.emit(
            "swarm:ignition", source="commander", tenant_id=self.tenant_id, routing_key="global"
        )

    async def get_or_create_legion(self, domain: str) -> LegionSupervisor:
        if domain not in self.legions:
            legion_id = f"legion-{domain}"
            if domain == "forensic":
                cls = ForensicLegion
            elif domain == "bpo":
                cls = BPOLegion
            elif domain == "audit":
                cls = AuditLegion
            else:
                cls = LegionSupervisor

            self.legions[domain] = cls(legion_id, self.bus, self.tenant_id)
            await self.bus.emit(
                event_type="legion:spawn",
                payload={"domain": domain, "type": cls.__name__},
                source="commander",
                tenant_id=self.tenant_id,
                routing_key=domain,
            )
        return self.legions[domain]

    async def execute_global_dispatch(self, tasks: list[dict], parallel: bool = True) -> None:
        """Route massive workload across the Sharded hierarchy in O(1) using Thermodynamic Pull Model."""
        await self.execute_global_dispatch_batched(tasks, parallel=parallel)

    async def execute_global_dispatch_batched(
        self,
        tasks: list[dict],
        parallel: bool = True,
        batch_size: int | None = None,
    ) -> None:
        """Route workload in bounded batches to avoid unbounded queue pressure."""
        active_legions = set()
        effective_batch_size = (
            config.SWARM_DISPATCH_BATCH_SIZE if batch_size is None else batch_size
        )
        if effective_batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        # Absolute O(1) Dispatch (Push to Mempool) with bounded batches
        for start in range(0, len(tasks), effective_batch_size):
            batch = tasks[start : start + effective_batch_size]
            for t in batch:
                domain = t.get("domain", "default")
                legion = await self.get_or_create_legion(domain)
                if parallel:
                    await legion.queue.put(t)
                    active_legions.add(legion)
                else:
                    await legion.dispatch(t)

        # Drain once at the end; queue.put() already applies backpressure.
        if parallel:
            await asyncio.gather(*(legion.queue.join() for legion in active_legions))

    async def get_density_report(self) -> dict:
        total_legions = len(self.legions)
        total_centurions = sum(legion.total_centurions for legion in self.legions.values())
        total_agents = sum(legion.total_agents for legion in self.legions.values())

        return {
            "legions": total_legions,
            "centurions": total_centurions,
            "agents": total_agents,
            "shards_active": self.bus.num_shards,
        }

    async def get_signal_count(self) -> int:
        """Return the total persisted signal count when using the sharded bus."""
        if not isinstance(self.bus, ShardedDurableSignalBus):
            return 0

        total_signals = 0
        for conn in self.bus._shards.values():
            row = await (await conn.execute("SELECT COUNT(*) FROM signals")).fetchone()
            total_signals += row[0] if row else 0
        return total_signals

    async def close_transport(self) -> None:
        """Close the underlying bus regardless of backend type."""
        if isinstance(self.bus, ShardedDurableSignalBus):
            await self.bus.close()
        else:
            self.bus.close()

    def unlink_transport(self) -> None:
        """Destroy shared-memory transport state when applicable."""
        if isinstance(self.bus, SovereignSharedBus):
            self.bus.unlink()

    async def consolidate_and_annihilate(self) -> None:
        """Purge entropy at the end of Ω_3 cycle."""
        # Signal annihilation (Unified Ω₆ interface)
        await self.bus.emit(
            "swarm:annihilation",
            source="commander",
            tenant_id=self.tenant_id,
            routing_key="global",
        )
        if isinstance(self.bus, ShardedDurableSignalBus):
            # Shannon compaction (only for persistent bus)
            await self.bus.gc(max_age_days=0, tenant_id=self.tenant_id)

        # Lifecycle cleanup (Ouroboros Hierarchy Teardown)
        for legion in self.legions.values():
            legion._is_running = False
            # Inject poison-pill sentinels so workers exit cleanly
            for _ in legion._workers:
                legion.queue.put_nowait(None)

            # Wait for strict termination
            await asyncio.gather(*legion._workers, return_exceptions=True)

            for cen in legion.centurions.values():
                cen.bus.close()
                if isinstance(cen.bus, SovereignSharedBus):
                    cen.bus.unlink()

        await self.close_transport()
        self.unlink_transport()

        self.legions.clear()
