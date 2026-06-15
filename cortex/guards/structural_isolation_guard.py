import asyncio
import logging
from typing import Any, Dict
from pydantic import BaseModel, ValidationError

# Dependencias abstraídas del core de CORTEX
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.observability.metrics import LocalMetricsBuffer

logger = logging.getLogger("cortex.guards.isolation")

class StructuralIsolationGuard:
    """
    Guardia de Aislamiento Estructural.
    Validación de entropía y estructura con I/O estrictamente asíncrono y fail-closed.
    """
    def __init__(
        self,
        ledger_client: EnterpriseAuditLedger, 
        metrics_buffer: LocalMetricsBuffer,
        strict_mode: bool = True
    ):
        self.ledger = ledger_client
        self.metrics = metrics_buffer
        self.strict_mode = strict_mode
        # Invariante de Aislamiento Estructural L5
        self._max_entropy_threshold = 25.0 

    async def validate_payload(self, agent_id: str, payload: Dict[str, Any]) -> bool:
        """
        Evalúa el payload. Si viola el aislamiento, ejecuta SAGA-1 de forma no bloqueante.
        """
        try:
            # 1. Validación Estructural Rápida (CPU-bound, no I/O)
            is_valid = self._check_structural_integrity(payload)
            
            if not is_valid:
                await self._trigger_saga_1_rejection(agent_id, payload, "Structural violation detected")
                return False
                
            return True

        except Exception as e:
            # RED TEAM FIREWALL: Fail-closed gracefully.
            logger.error(f"[GUARD FAILURE] Excepción no controlada: {e}")
            self.metrics.increment_counter("guard_panic_failures", tags={"agent": agent_id})
            return False if self.strict_mode else True

    def _check_structural_integrity(self, payload: Dict[str, Any]) -> bool:
        # Lógica pura de validación en memoria. Cero bloqueos.
        if "entropy_score" in payload and payload["entropy_score"] > self._max_entropy_threshold:
            return False
        return True

    async def _trigger_saga_1_rejection(self, agent_id: str, payload: Dict[str, Any], reason: str):
        """
        Emisión del rechazo. Desacoplado del I/O local.
        """
        # 1. Telemetría instantánea en memoria (Prometheus / Observability local)
        self.metrics.increment_counter(
            "isolation_rejections_total", 
            tags={"agent": agent_id, "reason": reason}
        )

        # 2. Persistencia asíncrona C5-REAL en el Ledger
        event_data = {
            "agent_id": agent_id,
            "event_type": "ISOLATION_BREACH",
            "reason": reason,
            "payload_snapshot": payload
        }
        
        try:
            # Timeout estricto para evitar que la red neuronal espere infinitamente al Ledger
            await asyncio.wait_for(self.ledger.emit_event(event_data), timeout=0.5)
        except asyncio.TimeoutError:
            logger.critical(f"SAGA-1 Timeout. El Ledger no responde. Evento guardado en buffer local: {event_data}")
            # Fallback a un buffer circular en memoria para rescate posterior
            self.metrics.push_to_dead_letter_queue(event_data)
