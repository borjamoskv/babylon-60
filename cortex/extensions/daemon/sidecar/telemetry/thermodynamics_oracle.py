from __future__ import annotations

import asyncio
import inspect
import logging
import os
import platform
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger(__name__)


class ThermodynamicsOracle:
    """
    Agente Termodinámico (Ω₂).
    Mide la Exergía (trabajo útil) y la entropía del sistema en tiempo real.
    Garantiza que el sistema no exceda la asfixia termodinámica.
    """

    def __init__(
        self,
        engine: AsyncCortexEngine,
        poll_interval: float = 60.0,
        thermal_threshold: float = 0.85,
    ) -> None:
        self.engine = engine
        self.base_poll_interval = poll_interval
        self.poll_interval = poll_interval
        self.thermal_threshold = thermal_threshold
        self._running = False
        self._cores = os.cpu_count() or 1

        # Load psutil if available to measure true thermodynamic footprint
        self._psutil = None
        try:
            import psutil

            self._psutil = psutil
        except ImportError:
            pass

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                lag_ms = await self._measure_event_loop_lag()
                await self._sample_thermodynamics(lag_ms)
            except asyncio.CancelledError:
                self._running = False
                break
            except (AttributeError, OSError, RuntimeError, ValueError) as exc:
                logger.warning("ThermodynamicsOracle sample degraded: %s", exc)
            except Exception:  # noqa: BLE001 - daemon boundary must keep the loop alive
                logger.exception("ThermodynamicsOracle unexpected failure")
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._running = False
        await asyncio.sleep(0)

    async def _measure_event_loop_lag(self, probe_window_s: float = 0.1) -> float:
        """Measure event-loop lag in milliseconds without blocking the loop."""
        started_at = time.perf_counter()
        await asyncio.sleep(probe_window_s)
        lag_ms = (time.perf_counter() - started_at - probe_window_s) * 1000.0
        return max(0.0, lag_ms)

    async def _sample_thermodynamics(self, lag_ms: float) -> None:
        if platform.system() == "Windows":
            return

        try:
            load1, load5, _ = os.getloadavg()
        except OSError:
            logger.debug("Skipping thermodynamics sample: load average unavailable.")
            return
        utilization = load1 / self._cores

        memory_percent = 50.0  # Base assumption
        disk_busy_ms = 0.0

        if self._psutil:
            memory_percent = self._psutil.virtual_memory().percent
            try:
                disk_io = self._psutil.disk_io_counters()
                if disk_io and hasattr(disk_io, "busy_time"):
                    disk_busy_ms = disk_io.busy_time or 0.0  # type: ignore[reportAttributeAccessIssue]
            except (AttributeError, OSError, RuntimeError):
                logger.debug("Disk I/O counters unavailable for thermodynamics sample.", exc_info=True)

        # Density factor of the Coroutine Swarm
        active_tasks = len(asyncio.all_tasks())
        swarm_density = active_tasks / 50.0  # Normalized (50 tasks = 1.0)

        # Level 2 Exergy Calculation
        # r = load, d = memory factor, f = friction (lag), t = task density
        r = round(utilization, 2)
        d = round(memory_percent / 100.0, 2)
        f = round(1.0 + (lag_ms / 100.0), 2)
        t = round(swarm_density, 2)
        s = 100  # Singularity constant

        # Loss = r * (d * 1.5) * f * (1 + t^2) * S
        exergy_loss = round(r * (d * 1.5) * f * (1 + (t**2)) * s, 1)

        # Red Queen Dynamic Polling (Axiom Ω₁₃)
        if exergy_loss > 50.0:
            self.poll_interval = max(5.0, self.base_poll_interval / 4.0)
        else:
            self.poll_interval = self.base_poll_interval

        purged_tasks = 0
        is_death_spiral = exergy_loss > 180.0

        if is_death_spiral:
            purged_tasks = self._execute_annihilation_protocol()

        # Trigger on pure overload, massive exergy loss, or dangerous event loop lock
        if utilization > self.thermal_threshold or exergy_loss > 90.0 or lag_ms > 500.0:
            # Host RAM pressure can push exergy_loss up on different machines.
            # Reserve CRITICAL for explicit collapse signals, not for ordinary
            # threshold breaches on an otherwise responsive loop.
            severity = (
                "CRITICAL"
                if utilization > 1.5 or purged_tasks > 0 or lag_ms > 1000.0 or exergy_loss > 250.0
                else "HIGH"
            )

            aniquilacion_msg = (
                f"\\n  [!] FATAL PURGE (Ω₄): {purged_tasks} asfixiated tasks eradicated."
                if purged_tasks > 0
                else ""
            )

            # Ω₂ Mandatory Mechanical Justification Format
            content = (
                f"INCENDIO TERMODINÁMICO. Límite de exergía excedido.\\n\\n"
                f"Claim: THERMODYNAMIC COLLAPSE [Severity: {severity}]\\n"
                f"Proof:\\n"
                f"  Base: Loss = r * (d * 1.5) * f * (1 + t^2) * S -> {exergy_loss}\\n"
                f"  Variables: [r={r}, d={d}, f={f}, t={t}, Lag={lag_ms:.1f}ms, Tasks={active_tasks}, Purged={purged_tasks}, n={self._cores}]\\n"
                f"  Range: [0.0, 500.0]\\n"
                f"  Confidence: C5-Dynamic"
            ) + aniquilacion_msg

            meta = {
                "oracle": "thermodynamics_v3_aniquilador",
                "load1": load1,
                "utilization": utilization,
                "memory_percent": memory_percent,
                "lag_ms": lag_ms,
                "active_tasks": active_tasks,
                "purged_tasks": purged_tasks,
                "disk_busy_ms": disk_busy_ms,
                "exergy_loss": exergy_loss,
                "cores": self._cores,
                "severity": severity,
            }

            await self._store_thermal_noise(content=content, meta=meta)

    async def _store_thermal_noise(self, content: str, meta: dict[str, object]) -> None:
        """Persist a thermal event through either async or sync engine surfaces."""
        payload = {
            "project": "SYSTEM",
            "content": content,
            "fact_type": "thermal_noise",
            "meta": meta,
        }

        store = getattr(self.engine, "store", None)
        if callable(store):
            result = store(**payload)
            if inspect.isawaitable(result):
                await result
            return

        store_sync = getattr(self.engine, "store_sync", None)
        if callable(store_sync):
            store_sync(**payload)
            return

        raise AttributeError("ThermodynamicsOracle requires engine.store(...) or engine.store_sync(...)")

    @staticmethod
    def _is_critical_task(task_name: str, coro_name: str) -> bool:
        return any(kw in task_name for kw in ("p0", "engine", "core", "server")) or any(
            kw in coro_name for kw in ("start", "serve", "watch", "loop")
        )

    def _execute_annihilation_protocol(self) -> int:
        """
        Protocolo de Aniquilación Síncrona (Axioma Ω₄).
        Ejecuta la guadaña termodinámica sobre el enjambre, purificando ruido inerte.
        """
        purged = 0
        current = asyncio.current_task()
        for task in asyncio.all_tasks():
            if task is current or task.done():
                continue

            task_name = task.get_name().lower()
            coro_name = getattr(task.get_coro(), "__name__", "").lower()  # type: ignore[reportAttributeAccessIssue]

            # Safeguards to prevent system bricking
            is_critical = self._is_critical_task(task_name, coro_name)

            if not is_critical:
                task.cancel()
                purged += 1

        # Cooldown forced yield to allow tasks to process their CancelledError
        return purged
