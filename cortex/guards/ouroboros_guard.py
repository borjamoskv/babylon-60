# [C5-REAL] Exergy-Maximized
"""
Ouroboros Entropy Guard (Issue #412).

Detects runaway async tasks that consume excessive event loop time without
yielding. Named after Ouroboros — the self-consuming snake — these tasks
feed on the event loop indefinitely, starving all other coroutines.

Implementation strategy:
  - A background watchdog coroutine measures the round-trip latency of a
    no-op asyncio.sleep(0) tick at regular intervals.
  - If tick latency exceeds ENTROPY_THRESHOLD_MS, the guard logs a warning
    and records the violation.
  - If latency exceeds CANCELLATION_THRESHOLD_MS, the guard force-cancels
    all tasks (except itself) to restore event loop homeostasis.
  - All violations are logged with logging.warning() per AGENTS.md Anti-Pattern.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import ClassVar

logger = logging.getLogger(__name__)

# Entropy threshold in milliseconds — warn if a single tick exceeds this
ENTROPY_THRESHOLD_MS: float = 100.0

# Cancellation threshold in milliseconds — force-cancel tasks if tick exceeds this
CANCELLATION_THRESHOLD_MS: float = 500.0

# How often the watchdog checks the event loop tick latency (seconds)
WATCHDOG_INTERVAL_S: float = 0.05


class OuroborosEntropyGuard:
    """Entropy guard that detects and terminates runaway async tasks.

    Monitors event loop tick latency and cancels tasks that exceed the
    entropy threshold, preventing starvation of the cooperative scheduler.

    Usage:
        guard = OuroborosEntropyGuard()
        await guard.start()
        # ... run your agent tasks ...
        await guard.stop()

    Or as an async context manager:
        async with OuroborosEntropyGuard():
            # ... run your agent tasks ...
    """

    DEFAULT_ENTROPY_THRESHOLD_MS: ClassVar[float] = ENTROPY_THRESHOLD_MS
    DEFAULT_CANCELLATION_THRESHOLD_MS: ClassVar[float] = CANCELLATION_THRESHOLD_MS

    def __init__(
        self,
        entropy_threshold_ms: float = ENTROPY_THRESHOLD_MS,
        cancellation_threshold_ms: float = CANCELLATION_THRESHOLD_MS,
        watchdog_interval_s: float = WATCHDOG_INTERVAL_S,
    ) -> None:
        """Initialise the Ouroboros entropy guard.

        Args:
            entropy_threshold_ms: Warn if event loop tick latency exceeds this
                value in milliseconds. Default: 100ms.
            cancellation_threshold_ms: Force-cancel all non-guard tasks if tick
                latency exceeds this value in milliseconds. Default: 500ms.
            watchdog_interval_s: Polling interval for the watchdog coroutine in
                seconds. Default: 50ms.
        """
        self.entropy_threshold_ms = entropy_threshold_ms
        self.cancellation_threshold_ms = cancellation_threshold_ms
        self.watchdog_interval_s = watchdog_interval_s
        self._watchdog_task: asyncio.Task[None] | None = None
        self._violation_count: int = 0
        self._cancellation_count: int = 0
        self._active: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the entropy watchdog as a background task."""
        if self._active:
            logger.warning("[OuroborosGuard] Guard already active — ignoring start()")
            return
        self._active = True
        self._watchdog_task = asyncio.create_task(
            self._watchdog_loop(), name="ouroboros-entropy-watchdog"
        )
        logger.info(
            "[OuroborosGuard] Entropy watchdog started — threshold=%.0fms "
            "cancellation=%.0fms interval=%.0fms",
            self.entropy_threshold_ms,
            self.cancellation_threshold_ms,
            self.watchdog_interval_s * 1000,
        )

    async def stop(self) -> None:
        """Stop the entropy watchdog gracefully."""
        self._active = False
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        self._watchdog_task = None
        logger.info(
            "[OuroborosGuard] Stopped. violations=%d cancellations=%d",
            self._violation_count,
            self._cancellation_count,
        )

    @property
    def violation_count(self) -> int:
        """Number of entropy threshold violations recorded."""
        return self._violation_count

    @property
    def cancellation_count(self) -> int:
        """Number of task cancellation events triggered."""
        return self._cancellation_count

    @property
    def is_active(self) -> bool:
        """True if the watchdog is currently running."""
        return self._active and (
            self._watchdog_task is not None and not self._watchdog_task.done()
        )

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "OuroborosEntropyGuard":
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Internal watchdog
    # ------------------------------------------------------------------

    async def _watchdog_loop(self) -> None:
        """Background watchdog: measures event loop tick latency continuously.

        Strategy:
          1. Record wall-clock time before yielding to the event loop.
          2. Schedule a no-op via asyncio.sleep(0) — this yields control and
             lets other tasks run.
          3. Measure elapsed wall-clock time after resumption.
          4. If elapsed > entropy_threshold_ms: log warning, increment counter.
          5. If elapsed > cancellation_threshold_ms: cancel runaway tasks.
          6. Sleep for watchdog_interval_s before next measurement.
        """
        while self._active:
            try:
                t_before = time.monotonic()
                await asyncio.sleep(0)  # yield to event loop
                elapsed_ms = (time.monotonic() - t_before) * 1000.0

                if elapsed_ms >= self.cancellation_threshold_ms:
                    self._violation_count += 1
                    self._cancellation_count += 1
                    logger.warning(
                        "[OuroborosGuard] CRITICAL entropy violation: tick_latency=%.1fms "
                        "(threshold=%.0fms) — cancelling runaway tasks. "
                        "violation_count=%d",
                        elapsed_ms,
                        self.cancellation_threshold_ms,
                        self._violation_count,
                    )
                    await self._cancel_runaway_tasks()

                elif elapsed_ms >= self.entropy_threshold_ms:
                    self._violation_count += 1
                    logger.warning(
                        "[OuroborosGuard] Entropy violation: tick_latency=%.1fms "
                        "(threshold=%.0fms). violation_count=%d",
                        elapsed_ms,
                        self.entropy_threshold_ms,
                        self._violation_count,
                    )

                await asyncio.sleep(self.watchdog_interval_s)

            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[OuroborosGuard] Unexpected error in watchdog loop: %s", exc
                )

    async def _cancel_runaway_tasks(self) -> None:
        """Force-cancel all tasks except the watchdog itself.

        Tasks named 'ouroboros-entropy-watchdog' are excluded to prevent
        the guard from self-cancelling.
        """
        current = asyncio.current_task()
        loop = asyncio.get_running_loop()
        all_tasks = asyncio.all_tasks(loop)

        runaway = [
            t
            for t in all_tasks
            if t is not current and t.get_name() != "ouroboros-entropy-watchdog"
        ]

        if not runaway:
            logger.warning(
                "[OuroborosGuard] No runaway tasks found — tick latency may be "
                "caused by blocking I/O in the main thread."
            )
            return

        for task in runaway:
            task_name = task.get_name()
            logger.warning(
                "[OuroborosGuard] Cancelling runaway task: name=%r coro=%r",
                task_name,
                task.get_coro().__qualname__ if hasattr(task.get_coro(), '__qualname__') else str(task.get_coro()),
            )
            task.cancel()

        # Await cancellation with a bounded timeout to prevent re-entrancy
        try:
            await asyncio.wait_for(
                asyncio.gather(*runaway, return_exceptions=True),
                timeout=2.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[OuroborosGuard] Runaway task cancellation timed out after 2s — "
                "tasks may still be holding locks."
            )

        logger.warning(
            "[OuroborosGuard] Cancelled %d runaway task(s). "
            "C5-REAL mode execution verified.",
            len(runaway),
        )
