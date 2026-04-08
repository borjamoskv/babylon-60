"""SOVEREIGN IOT TELEMETRY ORACLE (CORTEX Sidecar)
Physical-Cognitive Entanglement — tensor-robocar-entanglement

Captures physical friction and acts as the bridging protocol between hardware
(NXP, ESP32, environmental sensors) and the CORTEX core.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger("cortex.sidecar.telemetry.iot_oracle")


class IoTOracle:
    """
    Sovereign Physical Telemetry Oracle.

    Establishes the bridge between biological/physical signals (Temperature, Movement, MQTT)
    and the CORTEX Sovereign Ledger.
    """

    def __init__(
        self,
        engine: CortexEngine | AsyncCortexEngine,
        poll_interval: float = 10.0,
        enable_simulated_sensors: bool = True,
    ) -> None:
        self.engine = engine
        self.poll_interval = poll_interval
        self._running = False
        self._stop_event = asyncio.Event()
        self.enable_simulated_sensors = enable_simulated_sensors
        # Simulates R-Value dropping in an Earthship MMX or a Robocar friction event.
        self._sim_temp = 22.0

    async def start(self) -> None:
        """Invokes the Oracle's physical sensors."""
        self._running = True
        self._stop_event.clear()
        logger.info("📡 IOT ORACLE ONLINE. Physical Entanglement Active.")

        while self._running:
            try:
                await self._process_telemetry()
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                logger.error("IOT ORACLE SENSOR FAILURE: %s", exc)

            if not self._running:
                break

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except TimeoutError:
                continue

    async def stop(self) -> None:
        """Closes the Oracle's bridge to the physical world."""
        self._running = False
        self._stop_event.set()
        logger.info("IOT ORACLE OFFLINE.")

    async def _store_physical_telemetry(self, content: str, meta: dict[str, Any]) -> bool:
        store = getattr(self.engine, "store", None)
        if store is not None and inspect.iscoroutinefunction(store):
            await store(
                project="earthship_mmx",
                content=content,
                fact_type="physical_telemetry",
                meta=meta,
            )
            return True

        store_sync = getattr(self.engine, "store_sync", None)
        if callable(store_sync):
            store_sync(
                project="earthship_mmx",
                content=content,
                fact_type="physical_telemetry",
                meta=meta,
            )
            return True

        logger.warning("IOT Oracle skipped persistence: engine lacks store/store_sync")
        return False

    async def _process_telemetry(self) -> None:
        """Fetches data from edge devices and crystallizes friction."""
        if not self.enable_simulated_sensors:
            return  # In production, this would poll over MQTT / WebSocket to NXP

        # Simulated Earthship or Robocar thermal friction
        self._sim_temp -= 0.1  # Entropy drop

        if self._sim_temp < 18.0:
            logger.warning(
                "🌡️ [IOT ORACLE] Thermodynamic Friction Detected: Temp dropped to %.2f",
                self._sim_temp,
            )
            await self._inject_physical_intent(
                friction_type="thermal_drop",
                severity="P2",
                metrics={"temperature": self._sim_temp, "r_value": 0.85},
            )
            self._sim_temp = 22.0  # Simulated physical auto-actuation (e.g. heating loop activated)

    async def _inject_physical_intent(
        self, friction_type: str, severity: str, metrics: dict[str, Any]
    ) -> None:
        """Collapses the physical friction into a CORTEX Sovereign Fact."""
        content = (
            f"Fricción Física Detectada en el Entorno (Edge Node).\n"
            f"Tipo: {friction_type}\n"
            f"Gravedad: {severity}\n"
            f"Métricas: {metrics}"
        )
        meta = {
            "oracle": "iot_oracle_v1",
            "friction_type": friction_type,
            "metrics": metrics,
            "severity": severity,
        }

        try:
            stored = await self._store_physical_telemetry(content, meta)
            if stored:
                logger.info(
                    "🧠 [IOT ORACLE] Entanglement Collapsed: %s -> %s",
                    friction_type,
                    severity,
                )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.error("IOT Oracle Injection failed: %s", exc)
