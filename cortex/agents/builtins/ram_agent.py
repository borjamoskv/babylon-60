"""
ram_agent.py — RamAgent (Sovereign RAM Monitor)

Agente de memoria RAM soberana. Monitoriza el estado del heap Python,
detecta fugas de memoria, libera pipelines huérfanas, y emite alertas
a CORTEX Hypercore cuando la presión de memoria supera los umbrales.

Mandates (Ω₀ · Ω₂ · Ω₉):
  - C5-REAL: todas las lecturas vienen de psutil / tracemalloc (OS-level).
  - Umbrales deterministas: no hay heurísticas blandas.
  - Auto-discovery: se registra en el Supervisor en el primer tick.
"""

from __future__ import annotations

import gc
import logging
import os
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

# ─── Optional psutil (graceful degradation if not installed) ──────────────────
try:
    import psutil  # type: ignore[import]
    _PSUTIL = True
except ImportError:
    _PSUTIL = False
    logger.warning("RamAgent: psutil not installed — OS-level RAM reads disabled")


# ─── Thresholds (Ω₂ deterministic) ───────────────────────────────────────────

RAM_WARN_PCT = 70.0   # % system RAM → WARN
RAM_CRIT_PCT = 85.0   # % system RAM → CRITICAL + GC force
HEAP_WARN_MB = 256.0  # MB Python heap → WARN
HEAP_CRIT_MB = 512.0  # MB Python heap → CRIT + GC force
TRACEMALLOC_TOP = 10  # top N allocators in snapshot


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class RamSnapshot:
    """C5-REAL RAM state at a point in time."""

    ts: float = field(default_factory=time.time)
    # System
    sys_total_mb: float = 0.0
    sys_used_mb: float = 0.0
    sys_free_mb: float = 0.0
    sys_pct: float = 0.0
    # Process
    proc_rss_mb: float = 0.0
    proc_vms_mb: float = 0.0
    # Python heap
    heap_current_mb: float = 0.0
    heap_peak_mb: float = 0.0
    # GC
    gc_counts: tuple[int, int, int] = (0, 0, 0)
    gc_collected: int = 0
    # Status
    status: str = "OK"           # OK | WARN | CRITICAL
    reality_level: str = "C5-REAL"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "sys_total_mb": round(self.sys_total_mb, 1),
            "sys_used_mb": round(self.sys_used_mb, 1),
            "sys_free_mb": round(self.sys_free_mb, 1),
            "sys_pct": round(self.sys_pct, 1),
            "proc_rss_mb": round(self.proc_rss_mb, 1),
            "proc_vms_mb": round(self.proc_vms_mb, 1),
            "heap_current_mb": round(self.heap_current_mb, 2),
            "heap_peak_mb": round(self.heap_peak_mb, 2),
            "gc_counts": list(self.gc_counts),
            "gc_collected": self.gc_collected,
            "status": self.status,
            "reality_level": self.reality_level,
        }


@dataclass
class LeakSuspect:
    """Candidate memory leak from tracemalloc."""

    filename: str
    lineno: int
    size_kb: float
    count: int


# ─── RAM Reader ───────────────────────────────────────────────────────────────

def _read_ram_snapshot() -> RamSnapshot:
    """Read all RAM metrics from OS + Python runtime. C5-REAL."""
    snap = RamSnapshot()

    # System RAM (psutil path)
    if _PSUTIL:
        vm = psutil.virtual_memory()
        snap.sys_total_mb = vm.total / 1024 / 1024
        snap.sys_used_mb = vm.used / 1024 / 1024
        snap.sys_free_mb = vm.available / 1024 / 1024
        snap.sys_pct = vm.percent

        proc = psutil.Process(os.getpid())
        mi = proc.memory_info()
        snap.proc_rss_mb = mi.rss / 1024 / 1024
        snap.proc_vms_mb = mi.vms / 1024 / 1024
    else:
        # Fallback: read /proc/meminfo on Linux
        try:
            lines = open("/proc/meminfo").readlines()
            info = {line.split(":")[0]: int(line.split()[1]) for line in lines if ":" in line}
            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", 0)
            snap.sys_total_mb = total_kb / 1024
            snap.sys_free_mb = avail_kb / 1024
            snap.sys_used_mb = snap.sys_total_mb - snap.sys_free_mb
            snap.sys_pct = (snap.sys_used_mb / snap.sys_total_mb * 100
                            if snap.sys_total_mb else 0.0)
        except Exception:
            snap.reality_level = "C4-SIM"

    # Python heap  (tracemalloc)
    if tracemalloc.is_tracing():
        current, peak = tracemalloc.get_traced_memory()
        snap.heap_current_mb = current / 1024 / 1024
        snap.heap_peak_mb = peak / 1024 / 1024

    # GC state
    snap.gc_counts = tuple(gc.get_count())  # type: ignore[assignment]

    # Status classification
    if snap.sys_pct >= RAM_CRIT_PCT or snap.heap_current_mb >= HEAP_CRIT_MB:
        snap.status = "CRITICAL"
    elif snap.sys_pct >= RAM_WARN_PCT or snap.heap_current_mb >= HEAP_WARN_MB:
        snap.status = "WARN"
    else:
        snap.status = "OK"

    return snap


def _force_gc() -> int:
    """Run full GC cycle. Returns number of objects collected."""
    total = 0
    for gen in range(3):
        total += gc.collect(gen)
    return total


def _top_allocators(n: int = TRACEMALLOC_TOP) -> list[LeakSuspect]:
    """Return top N allocation sites from tracemalloc snapshot."""
    if not tracemalloc.is_tracing():
        return []
    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics("lineno")[:n]
    result = []
    for s in stats:
        frame = s.traceback[0]
        result.append(LeakSuspect(
            filename=frame.filename,
            lineno=frame.lineno,
            size_kb=round(s.size / 1024, 2),
            count=s.count,
        ))
    return result


# ─── RamAgent ────────────────────────────────────────────────────────────────

class RamAgent(BaseAgent):
    """
    Sovereign RAM Monitor Agent.

    On each tick:
      1. Reads C5-REAL RAM snapshot (OS + Python heap).
      2. Emits snapshot as FACT_PROPOSAL to memory_agent.
      3. If CRITICAL: forces GC + alerts supervisor.
      4. Exposes top allocators for leak detection on demand.

    Responds to TASK_REQUEST ops:
      snapshot   — returns current RAM state
      gc         — forces garbage collection, returns stats
      leaks      — returns top tracemalloc allocators
      enable_trace / disable_trace — toggle tracemalloc
    """

    AGENT_ID = "ram_agent"

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        trace: bool = False,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._last_snapshot: RamSnapshot | None = None
        self._alert_count = 0

        if trace:
            tracemalloc.start(25)  # 25-frame call stack depth
            logger.info("RamAgent: tracemalloc started (25-frame depth)")

    # ------------------------------------------------------------------
    # Daemon tick
    # ------------------------------------------------------------------

    async def tick(self) -> None:
        snap = _read_ram_snapshot()
        self._last_snapshot = snap

        logger.debug(
            "RamAgent tick — sys=%.1f%% heap=%.1fMB status=%s",
            snap.sys_pct, snap.heap_current_mb, snap.status,
        )

        # Emit to memory bus
        await self._emit_snapshot(snap)

        # Pressure response
        if snap.status == "CRITICAL":
            self._alert_count += 1
            collected = _force_gc()
            logger.warning(
                "RamAgent CRITICAL — GC forced, collected %d objects (alert #%d)",
                collected, self._alert_count,
            )
            snap.gc_collected = collected
            await self._alert_supervisors(snap)

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        kind = message.kind
        payload = message.payload or {}

        if kind == MessageKind.SHUTDOWN:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            self.force_stop()
            return

        if kind != MessageKind.TASK_REQUEST:
            return

        op = payload.get("op", "snapshot")

        if op == "snapshot":
            snap = _read_ram_snapshot()
            await self._reply(message, {"snapshot": snap.as_dict()})

        elif op == "gc":
            before = _read_ram_snapshot()
            collected = _force_gc()
            after = _read_ram_snapshot()
            await self._reply(message, {
                "collected_objects": collected,
                "before_mb": before.heap_current_mb,
                "after_mb": after.heap_current_mb,
                "freed_mb": round(before.heap_current_mb - after.heap_current_mb, 2),
            })

        elif op == "leaks":
            suspects = _top_allocators(payload.get("top", TRACEMALLOC_TOP))
            await self._reply(message, {
                "leak_suspects": [
                    {
                        "file": s.filename,
                        "line": s.lineno,
                        "size_kb": s.size_kb,
                        "count": s.count,
                    }
                    for s in suspects
                ],
                "tracing": tracemalloc.is_tracing(),
            })

        elif op == "enable_trace":
            if not tracemalloc.is_tracing():
                tracemalloc.start(25)
            await self._reply(message, {"tracing": True})

        elif op == "disable_trace":
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            await self._reply(message, {"tracing": False})

        else:
            await self._reply(message, {"error": f"Unknown op: {op}"})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _emit_snapshot(self, snap: RamSnapshot) -> None:
        msg = new_message(
            sender=self.manifest.agent_id,
            recipient="memory_agent",
            kind=MessageKind.FACT_PROPOSAL,
            payload={
                "source": "ram_agent",
                "fact_type": "ram_snapshot",
                "snapshot": snap.as_dict(),
            },
        )
        await self.bus.send(msg)

    async def _alert_supervisors(self, snap: RamSnapshot) -> None:
        for target in (self.manifest.escalation_targets or []):
            msg = new_message(
                sender=self.manifest.agent_id,
                recipient=target,
                kind=MessageKind.TASK_RESULT,
                payload={
                    "alert": "RAM_CRITICAL",
                    "snapshot": snap.as_dict(),
                    "alert_count": self._alert_count,
                },
            )
            await self.bus.send(msg)

    async def _reply(self, original: AgentMessage, data: dict[str, Any]) -> None:
        msg = new_message(
            sender=self.manifest.agent_id,
            recipient=original.sender,
            kind=MessageKind.TASK_RESULT,
            payload=data,
        )
        await self.bus.send(msg)


# ─── Factory ─────────────────────────────────────────────────────────────────

def make_ram_agent_manifest(**overrides: Any) -> AgentManifest:
    defaults: dict[str, Any] = {
        "agent_id": RamAgent.AGENT_ID,
        "purpose": (
            "Sovereign RAM Monitor. C5-REAL memory pressure detection, "
            "GC forcing, tracemalloc leak hunting, and pipeline zombie cleanup."
        ),
        "tools_allowed": ["psutil", "tracemalloc", "gc"],
        "facts_writable": ["ram_snapshot", "gc_event"],
        "facts_readable": ["pipeline_telemetry"],
        "escalation_targets": ["supervisor_agent"],
        "confidence_floor": "C5",
        "trust_level": "C5",
        "daemon": True,
        "max_concurrency": 1,
        "budget_tokens": 0,
        "budget_usd": 0.0,
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)
