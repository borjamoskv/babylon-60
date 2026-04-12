"""
TEST-BPO-STRIKE: Simulación de Ataque BPO Soberano
Verifica la orquestación, cumplimiento y despacho de la nueva infraestructura BPO.
"""

import asyncio
import logging
from pathlib import Path
from cortex.engine.swarm_10k import SwarmCommander

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BPO-STRIKE-TEST")

async def run_verification():
    logger.info("🚀 INICIANDO VERIFICACIÓN DE INFRAESTRUCTURA BPO")
    
    # 1. Inicializar Commander
    bus_path = Path("/tmp/bpo_test_bus")
    bus_path.mkdir(exist_ok=True)
    commander = SwarmCommander(bus_path=bus_path, use_shm=False)
    await commander.initialize()

    # 2. Definir Tareas de prueba
    tasks = [
        {
            "domain": "bpo",
            "payload": {
                "id": "STRIKE-01",
                "exergy_potential": 0.85,
                "reality_level": "C5-REAL",
                "description": "Arbitraje de alta frecuencia en DEX."
            }
        },
        {
            "domain": "bpo",
            "payload": {
                "id": "STRIKE-02",
                "exergy_potential": 0.30,  # Debería ser RECHAZADO por Compliance
                "reality_level": "C4",
                "description": "Spam de marketing (Baja exergía)."
            }
        }
    ]

    # 3. Ejecutar Despacho
    logger.info("📡 DESPACHANDO TAREAS A LEGION-BPO...")
    await commander.execute_global_dispatch(tasks, parallel=False)

    # 4. Verificar Reporte de Densidad
    report = await commander.get_density_report()
    logger.info("📊 REPORTE DE DENSIDAD: %s", report)

    # 5. Limpieza
    await commander.consolidate_and_annihilate()
    logger.info("🏆 VERIFICACIÓN COMPLETADA")

if __name__ == "__main__":
    asyncio.run(run_verification())
