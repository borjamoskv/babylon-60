import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Knowledge Broker (Insight Gate)
from cortex.extensions.temporal.activities.knowledge_broker import (
    shannon_scan_activity,
    immune_gate_activity,
    ledger_preview_activity,
    extract_exergy_activity,
)
from cortex.extensions.temporal.workflows.knowledge_broker import KnowledgeBrokerWorkflow

# Opex Hunter (Agency Killer)
from cortex.extensions.temporal.activities.opex_hunter import (
    ingest_aws_telemetry,
    ingest_okta_telemetry,
    calculate_opex_entropy,
    generate_cfo_draft,
    execute_purge_and_invoice
)
from cortex.extensions.temporal.workflows.opex_hunter import OpexHunterWorkflow

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | CORTEX/TEMPORAL | %(levelname)s | %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Módulos CORTEX-Omega: {Knowledge Broker, Opex Hunter} cargados en la Forja.")
    
    client = await Client.connect("localhost:7233")
    
    activities = [
        shannon_scan_activity, immune_gate_activity, ledger_preview_activity, extract_exergy_activity,
        ingest_aws_telemetry, ingest_okta_telemetry, calculate_opex_entropy, generate_cfo_draft, execute_purge_and_invoice
    ]

    worker = Worker(
        client,
        task_queue="cortex-broker-queue", # Usamos la misma cola para ambos
        workflows=[KnowledgeBrokerWorkflow, OpexHunterWorkflow],
        activities=activities
    )
    
    logger.info("WORKER SOBERANO ACTIVO. Escuchando anomalías OPEX y Cargas Causales (cortex-broker-queue)...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
