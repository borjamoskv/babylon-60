import asyncio
import logging
import os
from typing import Any

# Usamos AsyncLedgerClient, asumiendo que existe o simulamos un fallback
try:
    from cortex.audit.ledger import AsyncLedgerClient
except ImportError:
    AsyncLedgerClient = Any

logger = logging.getLogger("cortex.guards.isolation")

class StructuralIsolationGuard:
    """
    Guardia de Aislamiento Estructural.
    Validación de entropía y estructura con I/O estrictamente asíncrono y fail-closed.
    """
    LEDGER_PATH = ".cortex_ledger.json"

    def __init__(
        self, 
        workspace_dir: str = ".",
        strict_mode: bool = True,
        ledger_client: Any = None
    ):
        self.ledger_file = os.path.join(workspace_dir, self.LEDGER_PATH)
        self.ledger = ledger_client
        self.strict_mode = strict_mode
        self._max_entropy_threshold = 25.0 

    async def validate_payload(self, agent_id: str, payload: dict[str, Any]) -> bool:
        """
        Evalúa el payload. Si viola el aislamiento, ejecuta SAGA-1 de forma no bloqueante.
        """
        try:
            is_valid = self._check_structural_integrity(payload)
            if not is_valid:
                await self._trigger_saga_1_rejection(agent_id, payload, "Structural violation detected")
                return False
            return True
        except Exception as e:
            logger.error(f"[GUARD FAILURE] Excepción no controlada: {e}")
            return False if self.strict_mode else True

    def _check_structural_integrity(self, payload: dict[str, Any]) -> bool:
        if "entropy_score" in payload and payload["entropy_score"] > self._max_entropy_threshold:
            return False
        return True

    async def _trigger_saga_1_rejection(self, agent_id: str, payload: dict[str, Any], reason: str):
        event_data = {
            "agent_id": agent_id,
            "event_type": "ISOLATION_BREACH",
            "reason": reason,
            "payload_snapshot": payload
        }
        
        if self.ledger:
            try:
                await asyncio.wait_for(self.ledger.emit_event(event_data), timeout=0.5)
            except asyncio.TimeoutError:
                logger.critical(f"SAGA-1 Timeout. Evento guardado en log: {event_data}")
        else:
            logger.warning(f"No ledger client, fallback to log: {event_data}")
