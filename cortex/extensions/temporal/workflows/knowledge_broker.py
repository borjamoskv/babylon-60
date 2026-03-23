from datetime import timedelta
from typing import Dict, Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from cortex.extensions.temporal.activities.knowledge_broker import (
        shannon_scan_activity,
        immune_gate_activity,
        ledger_preview_activity,
        extract_exergy_activity,
    )

@workflow.defn
class KnowledgeBrokerWorkflow:
    def __init__(self) -> None:
        self.payment_received: bool = False
        self.aborted: bool = False

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orquestación determinista del Insight Broker CORTEX.
        Strict write-path compliance: scan -> guard -> ledger preview -> wait -> unlock.
        """
        
        # 1. SHANNON/CAUSALITY DETECT
        pattern_data = await workflow.execute_activity(
            shannon_scan_activity,
            input_data,
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # 2. IMMUNE GATE (Guards Verification)
        is_verified = await workflow.execute_activity(
            immune_gate_activity,
            pattern_data,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        if not is_verified:
            workflow.logger.warning("El insight fue rechazado por el CORTEX Immune System.")
            return {"status": "rejected_by_guards", "reason": "Failed Verification"}
            
        # 3. LEDGER DRAFT & PREVIEW
        preview = await workflow.execute_activity(
            ledger_preview_activity,
            pattern_data,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        workflow.logger.info(f"WORKFLOW SUSPENDIDO. Esperando señal del Operador/Cliente. Preview: {preview}")
        
        # 4. AWAIT SIGNAL (Bloqueo térmicamente gratuito, sin timeout impuesto para el ejemplo)
        await workflow.wait_condition(
            lambda: self.payment_received or self.aborted
        )

        if self.aborted:
            workflow.logger.info("Workflow abortado por señal de cancelación.")
            return {"status": "aborted"}

        # 5. EXTRACT KNOWLEDGE
        insight = await workflow.execute_activity(
            extract_exergy_activity,
            pattern_data,
            start_to_close_timeout=timedelta(minutes=2)
        )

        return {"status": "success", "insight": insight}

    @workflow.signal(name="confirm-payment")
    async def confirm_payment_signal(self) -> None:
        self.payment_received = True

    @workflow.signal(name="abort-insight")
    async def abort_insight_signal(self) -> None:
        self.aborted = True
