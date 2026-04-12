"""
AUDIT-BPO-STRIKE: Orquestador Maestro de Auditoría Soberana
Ciclo completo: Scout -> Compliance -> Auditor -> Ledger.
"""

import asyncio
import logging
from pathlib import Path
from cortex.engine.swarm_10k import SwarmCommander
from cortex.extensions.bpo.engine.bounty_scout import BountyScoutAgent

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AUDIT-STRIKE")

async def run_audit_campaign():
    logger.info("🔥 INICIANDO CAMPAÑA DE AUDITORÍA SOBERANA (AUDIT-BPO-OMEGA)")
    
    # 1. Preparar infraestructura
    bus_path = Path("/tmp/audit_test_bus")
    bus_path.mkdir(exist_ok=True)
    commander = SwarmCommander(bus_path=bus_path, use_shm=False)
    await commander.initialize()

    # 2. Fase de Scouting
    logger.info("🔭 Lanzando BountyScout para identificación de targets...")
    # Usamos un ID de agente ficticio para el test
    scout = BountyScoutAgent("alpha-scout-01", commander) 
    
    try:
        programs = await scout._fetch_immunefi_programs()
        opportunities = scout._extract_opportunities(programs)
        
        # Filtrar solo los Top-Tier (Alta Exergía) para el PoC
        targets = [o for o in opportunities if o.exergy_potential > 0.7][:5]
        logger.info("🎯 Targets de alta prioridad identificados: %d", len(targets))

        # 3. Empaquetar tareas para el Swarm
        tasks = []
        for opp in targets:
            tasks.append({
                "domain": "audit",
                "payload": {
                    "id": opp.id,
                    "project_name": opp.payload["project_name"],
                    "github_url": opp.payload["github_url"],
                    "exergy_potential": opp.exergy_potential,
                    "reality_level": "C5-REAL" # Activamos ejecución real
                }
            })

        # 4. Ejecución vía AuditLegion (Swarm dispatch)
        if tasks:
            logger.info("📡 Despachando Strike a la Legion-Audit...")
            await commander.execute_global_dispatch(tasks, parallel=True)
        else:
            logger.warning("∅ No se encontraron targets con exergía suficiente.")

    except Exception as e:
        logger.error("❌ Fallo en la campaña: %s", e)
    finally:
        # Cierre y reporte
        report = await commander.get_density_report()
        logger.info("📊 Reporte Final de Swarm: %s", report)
        await commander.consolidate_and_annihilate()
        logger.info("🏆 Campaña Finalizada.")

if __name__ == "__main__":
    asyncio.run(run_audit_campaign())
