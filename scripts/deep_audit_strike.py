"""
DEEP-AUDIT-STRIKE: Orquestador Maestro de Inteligencia Profunda
Especializado en el despliegue de Hound-Omega sobre 3 targets VIP.
"""

import asyncio
import logging
from pathlib import Path
from cortex.engine.swarm_10k import SwarmCommander
from cortex.extensions.bpo.engine.bounty_scout import BountyScoutAgent
from cortex.extensions.bpo.engine.report_agent import ReportAgent
from cortex.extensions.bpo.engine.submission_agent import SubmissionAgent

# Configuración de logs Industrial Noir
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DEEP-AUDIT-STRIKE")

async def run_deep_campaign():
    logger.info("🔥 [P-MODE] INICIANDO CAMPAÑA DE AUDITORÍA PROFUNDA (HOUND-OMEGA)")
    
    # 1. Preparar infraestructura (Usando SHM para interop con BPO Agents)
    commander = SwarmCommander(bus_path="/tmp/cortex_swarm", use_shm=True)
    await commander.initialize()

    # 2. Iniciar Agentes de Cristalización y Entrega (Ω: C5-REVENUE)
    report_agent = ReportAgent("report-omega-grid-01")
    report_task = asyncio.create_task(report_agent.start_listening())
    
    submit_agent = SubmissionAgent("submit-omega-grid-01")
    submit_task = asyncio.create_task(submit_agent.start_listening())
    
    logger.info("📄 [ORQUESTADOR] ReportAgent y SubmissionAgent activos.")

    # 3. Fase de Scouting & Triage (Ω₃: Ley del Ciclo)
    logger.info("🔭 Escaneando targets para Triage de 3 Flashes...")
    scout = BountyScoutAgent("hound-scout-01", commander) 
    
    try:
        programs = await scout._fetch_immunefi_programs()
        # Tomar solo una muestra para evitar saturación en test si es necesario, 
        # pero aquí seguimos el plan de 3 VIPs.
        opportunities = scout._extract_opportunities(programs)
        
        # TRIAGE: Seleccionar top 3 por exergía
        top_targets = sorted(opportunities, key=lambda x: x.exergy_potential, reverse=True)[:3]
        
        logger.info("🎯 Targets VIP Seleccionados para Strike Profundo:")
        for t in top_targets:
            logger.info("  ◈ %s (Exergía: %.2f)", t.payload["project_name"], t.exergy_potential)

        # 4. Empaquetar tareas para el Swarm
        tasks = []
        for opp in top_targets:
            tasks.append({
                "domain": "audit",
                "payload": {
                    "id": opp.id,
                    "project_name": opp.payload["project_name"],
                    "github_url": opp.payload["github_url"],
                    "exergy_potential": opp.exergy_potential,
                    "mode": "P-FLASH",
                    "reality_level": "C5-REAL"
                }
            })

        # 5. Ejecución vía AuditLegion
        if tasks:
            logger.info("📡 Despachando Strike Híbrido a la Legion-Audit...")
            await commander.execute_global_dispatch(tasks, parallel=True)
            
            # Esperar un momento a que las síntesis de reportes terminen
            logger.info("⏳ Esperando cristalización de resultados...")
            await asyncio.sleep(10) 
        else:
            logger.warning("∅ No se encontraron targets para el ciclo actual.")

    except Exception as e:
        logger.error("❌ Fallo en la campaña profunda: %s", e)
    finally:
        report = await commander.get_density_report()
        logger.info("📊 Reporte Final de Swarm: %s", report)
        
        # Cancelar agentes en background
        report_task.cancel()
        submit_task.cancel()
        
        await commander.consolidate_and_annihilate()
        logger.info("🏆 Ciclo Deep-Audit Finalizado.")

if __name__ == "__main__":
    asyncio.run(run_deep_campaign())
