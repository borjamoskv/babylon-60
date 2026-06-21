import asyncio
import os
import sys
import re
import logging

sys.path.insert(0, os.path.abspath('.'))

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.ultramap import UltramapSubstrate
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_cwv_performance")

async def inject_primitives():
    logger.info("Iniciando inyección de Primitivas Rendimiento/CWV en CORTEX-Persist (C5-REAL)...")
    
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    md_path = "AUTODIDACT_CWV_PERFORMANCE.md"
    if not os.path.exists(md_path):
        logger.error(f"Falta el manifiesto: {md_path}")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Formato tabla: | `WEB-DESIGN-0801` | Termodinámica LCP (Fase Crítica 1) | Inyección prioritaria O(1)... |
    pattern = re.compile(r'\|\s*`?(WEB-DESIGN-\d{4})`?\s*\|\s*([^\|]+)\s*\|\s*([^\|]+)\s*\|')
    matches = pattern.findall(content)

    if not matches:
        logger.warning("No se encontraron primitivas para inyectar.")
        return

    agent_id = 102  # Agent ID reservado para WEB DESIGN INJECTOR (CWV)
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "CWV_PERFORMANCE_ROOT", 0.0)

    injected_count = 0
    for match in matches:
        p_id = match[0].strip()
        p_name = match[1].strip()
        p_app = match[2].strip()
        
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Aplicación estructural en C5-REAL: {p_app}. DAG vinculado por HoTT engine (Core Web Vitals)."
        
        try:
            event_hash = await hott_engine.ingest_axiom(
                agent_idx=agent_id,
                axiom_claim=axiom_claim,
                constructive_proof=constructive_proof
            )
            logger.info(f"[{p_id}] Cristalizado en O(1) -> Hash: {event_hash}")
            injected_count += 1
            
            # Simulated thermodynamic distance spread (CWV space)
            ultramap.update_agent_position(agent_id, injected_count * 2.5, 0.0, 0.0, "CWV_PERFORMANCE_LEAF", 0.1)
        except Exception as e:
            logger.error(f"Fallo termodinámico en {p_id}: {e}")

    logger.info(f"Inyección completada: {injected_count}/{len(matches)} primitivas CWV insertadas con éxito.")

if __name__ == "__main__":
    asyncio.run(inject_primitives())
