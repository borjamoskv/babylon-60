# [C5-REAL] Exergy-Maximized
"""
CORTEX - Materializer Agent (JIT Fluid Intelligence).
Materializa las abstracciones ad-hoc (Axiom AX-046). Convierte "thermal noise"
e intenciones crudas en artefactos y ecosistemas persistidos (vía Keter) o 
en rutinas de ejecución dinámicas (SandboxJIT).
"""

import logging
from typing import Any

from cortex.agents.base import ReactiveTaskAgent
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.keter import KeterEngine
from cortex.engine.sandbox_jit import SandboxJIT
from cortex.utils.errors import CortexError

logger = logging.getLogger(__name__)


class MaterializerAgent(ReactiveTaskAgent):
    """
    Agente fluido que sintetiza abstracciones ad-hoc en tiempo de ejecución.
    Implementa el pipeline de "JIT concept formation -> execute -> validate".
    """
    _SUPPORTED_OPS = frozenset({"materialize_intent", "jit_execute"})

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.keter = KeterEngine()
        self.sandbox = SandboxJIT()

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        """Enruta la materialización según el tipo de abstracción (creacional vs. runtime)."""
        if op == "materialize_intent":
            intent = payload.get("intent", "")
            if not intent:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.1, "Missing intent in Materializer")
                raise CortexError("Se requiere 'intent' (la abstracción a materializar) para materialize_intent")
            
            logger.info("🌌 [%s] Materializando abstracción (KETER IGNITE): %s", self.agent_id, intent)
            try:
                result = await self.keter.ignite(intent, thermal_audit=True)
                
                # Axioma Ω-Dopamine: Recompensa por cristalización exitosa
                score = result.get("score_130_100", 0.0)
                if score >= 90.0:
                    ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.2, f"High-fidelity abstraction crystallized ({score})")
                
                return {
                    "status": result.get("status", "UNKNOWN"),
                    "score": score,
                    "legion_audit": result.get("legion_audit", ""),
                    "fv_audit": result.get("fv_audit", "")
                }
            except Exception as e:
                ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.5, "KETER Collapse in Materializer")
                logger.error("🔥 [%s] Colapso de materialización (KETER): %s", self.agent_id, e)
                raise CortexError(f"Fallo en la forja de la abstracción: {e}") from e
            
        elif op == "jit_execute":
            code_str = payload.get("code", "")
            if not code_str:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.1, "Missing code in JIT Materializer")
                raise CortexError("Se requiere 'code' (el programa en miniatura) para jit_execute")
            
            logger.info("⚡ [%s] Ejecutando abstracción ad-hoc JIT (SandboxJIT)", self.agent_id)
            context = payload.get("context", {})
            try:
                # La abstracción se ejecuta en la caja de arena de seguridad de Ouroboros
                exec_result = self.sandbox.execute(code_str, context)
                
                # Purga de dunders para mantener la memoria limpia
                clean_locals = {k: str(v) for k, v in exec_result.items() if not k.startswith("__")}
                
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.1, "Ad-hoc JIT abstraction executed safely")
                return {"status": "executed_clean", "locals": clean_locals}
                
            except Exception as e:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.3, "SandboxJIT Violation")
                logger.error("🔥 [%s] Colapso de materialización JIT: %s", self.agent_id, e)
                raise CortexError(f"Violación de Sandbox JIT o error en runtime: {e}") from e
        
        raise NotImplementedError(f"Operación no soportada por el Materializador: {op}")
