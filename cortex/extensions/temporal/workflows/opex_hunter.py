from datetime import timedelta
from typing import Dict, Any
import asyncio
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from cortex.extensions.temporal.activities.opex_hunter import (
        ingest_aws_telemetry,
        ingest_okta_telemetry,
        calculate_opex_entropy,
        generate_cfo_draft,
        execute_purge_and_invoice
    )

@workflow.defn
class OpexHunterWorkflow:
    def __init__(self) -> None:
        self.cfo_approved: bool = False
        self.rejected: bool = False

    @workflow.run
    async def run(self, tenant_id: str) -> Dict[str, Any]:
        """
        Orquestación determinista del Agente 'Agency Killer'.
        Strict write-path compliance con cero daño colateral (barrera humana).
        """
        
        workflow.logger.info(f"Iniciando OPEX Hunt (Agency Killer Mode) para tenant: {tenant_id}")

        # 1. Ingestión Paralela Cero-Riesgo
        aws_task = workflow.execute_activity(ingest_aws_telemetry, tenant_id, start_to_close_timeout=timedelta(minutes=5))
        okta_task = workflow.execute_activity(ingest_okta_telemetry, tenant_id, start_to_close_timeout=timedelta(minutes=5))
        
        # Resolvemos en paralelo
        aws_data, okta_data = await asyncio.gather(aws_task, okta_task)
        
        # 2. Causality & Exergy Calc
        report = await workflow.execute_activity(
            calculate_opex_entropy,
            args=[aws_data, okta_data],
            start_to_close_timeout=timedelta(minutes=1)
        )
        
        # 3. Draft C-Level (Slack/Email mock)
        slack_msg = await workflow.execute_activity(
            generate_cfo_draft,
            report,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        workflow.logger.info(f"\n======== CFO DRAFT ENVIADO ========\n{slack_msg}\n===================================")
        workflow.logger.info("WORKFLOW SUSPENDIDO. Esperando la tecla balística del CFO...")
        
        # 4. BARRERA TERMICA (AWAIT APPROVAL) - Riesgo Destructivo aislado.
        # Puede esperar 3 semanas sin consumir CPU.
        await workflow.wait_condition(
            lambda: self.cfo_approved or self.rejected
        )

        if self.rejected:
            workflow.logger.info("CFO rechazó la purga. Workflow abortado sin daños.")
            return {"status": "aborted", "savings": 0}

        # 5. EXECUTION CORE (Stripe + Destructive APIs)
        ledger_receipt = await workflow.execute_activity(
            execute_purge_and_invoice,
            report,
            start_to_close_timeout=timedelta(minutes=10)
        )

        return {"status": "executed", "receipt": ledger_receipt, "cortex_revenue": report['cortex_fee_usd']}


    @workflow.signal(name="approve-opex-purge")
    async def approve_opex_signal(self) -> None:
        self.cfo_approved = True

    @workflow.signal(name="reject-opex-purge")
    async def reject_opex_signal(self) -> None:
        self.rejected = True
